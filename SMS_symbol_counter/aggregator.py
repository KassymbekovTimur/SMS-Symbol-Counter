import csv
import re
import logging
from collections import defaultdict

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

INPUT_FILE = "path/to/data.csv"

INPUT  = "patterns_report_full.csv"
OUTPUT = "patterns_report_aggregated.csv"
SEP = '\t'
MSG_COL = "message"
TIME_COL = "submission_date"
PHONE_COL = "phone"

raw = defaultdict(list)
with open(INPUT_FILE, encoding="utf-8") as f:
    rdr = csv.DictReader(f, delimiter=SEP, quoting=csv.QUOTE_NONE)
    for row in rdr:
        t = row.get(TIME_COL, "").strip()
        p = row.get(PHONE_COL, "").strip()
        m = row.get(MSG_COL, "").strip()
        if not t or not p or len(m) < 1:
            continue
        raw[(t, p)].append((row, m))

# 2) склеиваем по ключу
merged_records = []
for (t, p), lst in raw.items():
    if len(lst) > 1:
        # сортируем по порядку, если нужно – по индексу
        combined = "".join(m for (_, m) in lst)
        # возьмём остальные поля из первой записи, но с объединённым текстом
        first_row = lst[0][0].copy()
        first_row[MSG_COL] = combined
        merged_records.append(first_row)
    else:
        merged_records.append(lst[0][0])

SPECIALS = {
    # kh: {NUM} {NUM},{NUM} KZT… → {MONEY}
    r"kh: \{NUM\} \{NUM\},\{NUM\} KZT\.Karta:\{NUM\}\*\*\{NUM\}\.Qaldyq/ostatok:\{NUM\},\{NUM\} KZT":
        "kh: {MONEY} KZT. Karta: {NUM}**{NUM}. Qaldyq/ostatok: {MONEY} KZT",

    # k: {NUM} {NUM}.{NUM} KZT → k: {MONEY} KZT
    r"k: \{NUM\} \{NUM\}\.\{NUM\} KZT":
        "k: {MONEY} KZT",

    # KODTY…(KZT)…Kod:{NUM} → ({MONEY}).Kod:{NUM}
    r"KODTY ESHKIMGE AITPANYZ/NIKOMU NE GOVORITE KOD\.Audarym/Perevod: \(\{NUM\} \{NUM\}\.\{NUM\} KZT\)\.Kod:\{NUM\}":
        "KODTY ESHKIMGE AITPANYZ/NIKOMU NE GOVORITE KOD.Audarym/Perevod: ({MONEY}).Kod:{NUM}",

    # Sizge…Salemdeme kody {CODE}…Vam postupila posylka {CODE}
    r"Sizge \{CODE\} salemdemesi keldi\.Salemdeme kody \{CODE\} Saqtau merzimi \{NUM\} kun\..*?Vam postupila posylka \{CODE\}":
        "Sizge {CODE} salemdemesi keldi. Salemdeme kody {CODE} Saqtau merzimi {NUM} kun. Vam postupila posylka {CODE}",

    # {CODE}.Kod posylki X-{NUM}-{NUM}… → {CODE}.Kod posylki {CODE}…
    r"\{CODE\}\.Kod posylki [A-Za-z0-9]+-\{NUM\}-\{NUM\}\. Srok hranenia \{NUM\} dney\. Uznat dopolnitelnuyu informaciu mozhete na post\.kz\.":
        "{CODE}.Kod posylki {CODE}. Srok hranenia {NUM} dney. Uznat dopolnitelnuyu informaciu mozhete na post.kz.",

    # обрезанные хвосты «…Vam postupila posylka»
    r"Sizge \{CODE\} salemdemesi keldi\.Salemdeme kody \{CODE\} Saqtau merzimi \{NUM\} kun\. Qosymsha aqparatty post\.kz - ten bile alasyz\.Vam postupila posylka(?: [A-Za-z0-9]*)?":
        "Sizge {CODE} salemdemesi keldi. Salemdeme kody {CODE} Saqtau merzimi {NUM} kun. Qosymsha aqparatty post.kz - ten bile alasyz. Vam postupila posylka {CODE}",

    # sourcet URL → {TRACK_URL}
    r"Sizge salemdeme keldi\. Saqtau merzimi \{NUM\} kun\. / Vam prishla posylka\. Srok hranenia \{NUM\} dney\. Tolygyraq/Detali:? ?\{TRACK_URL\}":
        "Sizge salemdeme keldi. Saqtau merzimi {NUM} kun. / Vam prishla posylka. Srok hranenia {NUM} dney. Tolygyraq/Detali: {TRACK_URL}",

    # транзакционные «qolma-qol … snyatie»
    r"\{TIME\} qolma-qol aqshany sheship aly(?:ndy| oryndalmady)/ otmena snyatiya nalichnykh: \{(?:NUM|MONEY)\}(?: \{NUM\})*(?:\.\{NUM\})? (?:KZT|UZS|USD)\. Karta:\{NUM\}\*\*\{NUM\}\. Qaldyq/ostatok: \{(?:NUM|MONEY)\}(?: \{NUM\})*(?:\.\{NUM\})? (?:KZT|UZS|USD)":
        "{TIME} qolma-qol aqsha sheship alyndy/otmena snyatiya nalichnykh: {MONEY} {CURR}. Karta:{NUM}**{NUM}. Qaldyq/ostatok: {MONEY} {CURR}",

    # *{NUM} shotqa … Ostatok {NUM} KZT
    r"\*\{NUM\} shott?a \{NUM\} KZT soma alyndy\.(.*?)Ostatok \{NUM\} KZT":
        "*{NUM} shotqa {NUM} KZT soma alyndy. Qaldygy {NUM} KZT/ Postuplenie na schet *{NUM} Summa {NUM} KZT. Ostatok {NUM} KZT",

    # telefon nomiri…USD/EUR/KZT
    r"\{TIME\} telefon nomiri arqyly audarym kelip tusti/ postupil perevod po nomeru telefona: \{(?:NUM|MONEY)\}(?:\.\{NUM\})? (?:KZT|USD|EUR|UZS)\. K\*\*\{NUM\}\. Qaldyq/ostatok: \{(?:NUM|MONEY)\}(?:\.\{NUM\})? (?:KZT|USD|EUR|UZS)":
        "{TIME} telefon nomiri arqyly audarym kelip tusti/ postupil perevod po nomeru telefona: {MONEY} {CURR}. K**{NUM}. Qaldyq/ostatok: {MONEY} {CURR}",

    # хвостовые «12345KZ.Kod posylki -{NUM}…»
    r"\d+[A-Z]{2}\.Kod posylki -\{NUM\}\. Srok hranenia \{NUM\} dney\. Uznat dopolnitelnuyu informaciu mozhete na post\.kz\.":
        "{CODE}.Kod posylki -{NUM}. Srok hranenia {NUM} dney. Uznat dopolnitelnuyu informaciu mozhete na post.kz.",
}

# Регулярка для удаления подряд {NUM} {MONEY}
NUM_MONEY_RX = re.compile(r"\{NUM\}[\u00A0\s]+\{MONEY\}")


def super_generalize(pattern: str) -> str:
    """Обобщаем паттерн: сначала SPECIALS, затем общие правила, включая свёртку {NUM} {MONEY}."""
    # 1) специальные случаи
    for rx, repl in SPECIALS.items():
        if re.fullmatch(rx, pattern):
            logging.debug(f"SPECIALS matched: {pattern} -> {repl}")
            return repl

    p = pattern
    # 2) пример общего обобщения (как в temp3)
    # убираем всё перед ".Kod posylki"
    p = re.sub(r"^.*?\\.Kod posylki", "{CODE}.Kod posylki", p)
    # даты-время
    p = re.sub(r"\{NUM\}-\{NUM\}-\{NUM\} \{TIME\}", "{DATETIME}", p)
    # суммы с валютой
    p = re.sub(
        r"\{NUM\}(?:[ ,]\{NUM\})*(?:[.,]\{NUM\})? [A-Z]{3}\b",
        "{MONEY} {CURR}",
        p
    )
    # ссылки и треки
    p = re.sub(r"/t/\{\d+_TRACK\}", "{TRACK_URL}", p)
    p = re.sub(r"\{URL\}", "{TRACK_URL}", p)
    # любые коды вида {N_CODE} → {CODE}
    p = re.sub(r"\{\d+_CODE\}", "{CODE}", p)
    # сглаживаем подряд несколько {NUM}
    p = re.sub(r"(?:\{NUM\}){2,}", "{NUM}", p)

    # 3) СВЁРТКА {NUM} {MONEY} → {MONEY} (учитывая NBSP)
    before = p
    p = NUM_MONEY_RX.sub("{MONEY}", p)
    if p != before:
        logging.debug(f"Num-money collapse: {before} -> {p}")

    return p


def aggregate_patterns(report_file: str) -> dict:
    """Читаем patterns_report_full.csv и собираем агрегированные данные."""
    agg = defaultdict(lambda: {
        "sum_count": 0,
        "example_msg": None,
        "example_count": 0,
        "example_len": 0,
        "example_segs": 0
    })

    with open(report_file, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_pat    = row["Pattern"]
            traffic    = row["Traffic Type"]
            count      = int(row["Total Count"])
            length     = int(row["Length"])
            segs       = int(row["SMS Segments"])
            # используем исходный пример сообщения из колонки Example
            example_msg = row.get("Example", "")

            gen_pat = super_generalize(raw_pat)
            key = (gen_pat, traffic)
            rec = agg[key]

            # суммируем
            rec["sum_count"] += count
            # обновляем пример сообщения — берем длиннейшее
            if rec["example_msg"] is None or len(example_msg) > rec["example_len"]:
                rec.update({
                    "example_msg": example_msg,
                    "example_count": count,
                    "example_len": len(example_msg),
                    "example_segs": segs
                })
    return agg


def write_output(agg: dict, output_file: str):
    """Записываем агрегированные результаты в CSV."""
    with open(output_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Generalized Pattern",
            "Traffic Type",
            "Sum Total Count",
            "Example Message",
            "Example Total Count",
            "Example Length",
            "Example SMS Segments",
        ])
        for (gen, traffic), rec in sorted(agg.items(), key=lambda x: x[1]["sum_count"], reverse=True):
            writer.writerow([
                gen,
                traffic,
                rec["sum_count"],
                rec["example_msg"],
                rec["example_count"],
                rec["example_len"],
                rec["example_segs"],
            ])
    logging.info(f"Готово — {len(agg)} обобщённых паттернов записано в {output_file}")


if __name__ == "__main__":
    logging.info("Начинаем агрегацию паттернов...")
    aggregated = aggregate_patterns(INPUT)
    write_output(aggregated, OUTPUT)
