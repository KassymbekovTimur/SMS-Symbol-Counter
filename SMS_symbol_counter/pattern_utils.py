import re
import math

# --- Константы для обработки сообщений ---
# GSM-7 для подсчёта сегментов
GSM7 = (
    "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞ\u00A0ÆæßÉ !\"#¤%&'()*+,-./"
    "0123456789:;<=>?¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿"
    "abcdefghijklmnopqrstuvwxyzäöñüà"
)

# --- Функции для подсчёта сегментов SMS ---
def compute_segments(text: str):
    """
    Вычисляет длину сообщения и количество SMS-сегментов.
    Использует GSM-7 кодировку для оптимизации подсчета.
    """
    length = len(text)
    is_gsm7 = all(ch in GSM7 for ch in text)
    limit, block = (160, 153) if is_gsm7 else (70, 67)
    segs = 1 if length <= limit else math.ceil(length / block)
    return length, segs

# --- Словарь «особых» обобщений ---
# Эти паттерны будут обрабатываться в первую очередь
SPECIALS = {
    # kh: {NUM} {NUM},{NUM} KZT… → сводим оба в {MONEY}
    r"kh: \{NUM\} \{NUM\},\{NUM\} KZT\.Karta:\{NUM\}\*\*\{NUM\}\.Qaldyq/ostatok:\{NUM\},\{NUM\} KZT":
        "kh: {MONEY} KZT. Karta: {NUM}**{NUM}. Qaldyq/ostatok: {MONEY} KZT",

    # k: {NUM} {NUM}.{NUM} KZT → k: {MONEY} KZT
    r"k: \{NUM\} \{NUM\}\.\{NUM\} KZT":
        "k: {MONEY} KZT",

    # KODTY ESHKIMGE… (KZT) → ({MONEY}).Kod:{NUM}
    r"KODTY ESHKIMGE AITPANYZ/NIKOMU NE GOVORITE KOD\.Audarym/Perevod: \(\{NUM\} \{NUM\}\.\{NUM\} KZT\)\.Kod:\{NUM\}":
        "KODTY ESHKIMGE AITPANYZ/NIKOMU NE GOVORITE KOD.Audarym/Perevod: ({MONEY}).Kod:{NUM}",

    # «Sizge {CODE}… Salemdeme kody {CODE} Saqtau merzimi {NUM}… Vam postupila posylka {CODE}»
    r"Sizge \{CODE\} salemdemesi keldi\.Salemdeme kody \{CODE\} Saqtau merzimi \{NUM\} kun\..*?Vam postupila posylka \{CODE\}":
        "Sizge {CODE} salemdemesi keldi. Salemdeme kody {CODE} Saqtau merzimi {NUM} kun. Vam postupila posylka {CODE}",

    # {CODE}.Kod posylki X-{NUM}-{NUM}… → {CODE}.Kod posylki {CODE}…
    r"\{CODE\}\.Kod posylki [A-Za-z0-9]+-\{NUM\}-\{NUM\}\. Srok hranenia \{NUM\} dney\. Uznat dopolnitelnuyu informaciu mozhete na post\.kz\.":
        "{CODE}.Kod posylki {CODE}. Srok hranenia {NUM} dney. Uznat dopolnitelnuyu informaciu mozhete na post.kz.",

    # «Sizge {CODE}…posylka» (частично обрезанные варианты без или с коротким хвостом)
    r"Sizge \{CODE\} salemdemesi keldi\.Salemdeme kody \{CODE\} Saqtau merzimi \{NUM\} kun\. Qosymsha aqparatty post\.kz - ten bile alasyz\.Vam postupila posylka(?: [A-Za-z0-9]*)?":
        "Sizge {CODE} salemdemesi keldi. Salemdeme kody {NUM} kun. Qosymsha aqparatty post.kz - ten bile alasyz. Vam postupila posylka {CODE}",

    # «Sizge salemdeme keldi. Saqtau merzimi {NUM}… Tolygyraq/Detali: {TRACK_URL}»
    r"Sizge salemdeme keldi\. Saqtau merzimi \{NUM\} kun\. / Vam prishla posylka\. Srok hranenia \{NUM\} dney\. Tolygyraq/Detali:? ?\{TRACK_URL\}":
        "Sizge salemdeme keldi. Saqtau merzimi {NUM} kun. / Vam prishla posylka. Srok hranenia {NUM} dney. Tolygyraq/Detali: {TRACK_URL}",

    # «qolma-qol … snyatie nalichnykh» (KZT/UZS/USD) → один шаблон
    r"\{TIME\} qolma-qol aqshany sheship aly(?:ndy| oryndalmady)/ otmena snyatiya nalichnykh: \{(?:NUM|MONEY)\}(?: \{NUM\})*(?:\.\{NUM\})? (?:KZT|UZS|USD)\. Karta:\{NUM\}\*\*\{NUM\}\. Qaldyq/ostatok: \{(?:NUM|MONEY)\}(?: \{NUM\})*(?:\.\{NUM\})? (?:KZT|UZS|USD)":
        "{TIME} qolma-qol aqsha sheship alyndy/otmena snyatiya nalichnykh: {MONEY} {CURR}. Karta:{NUM}**{NUM}. Qaldyq/ostatok: {MONEY} {CURR}",

    # «*{NUM} shotqa {NUM} KZT soma alyndy…Ostatok {NUM} KZT»
    r"\*\{NUM\} shott?a \{NUM\} KZT soma alyndy\.(.*?)Ostatok \{NUM\} KZT":
        "*{NUM} shotqa {NUM} KZT soma alyndy. Qaldygy {NUM} KZT/ Postuplenie na schet *{NUM} Summa {NUM} KZT. Ostatok {NUM} KZT",

    # «telefon nomiri … perevod … KZT»
    r"\{TIME\} telefon nomiri arqyly audarym kelip tusti/ postupil perevod po nomeru telefona: \{(?:NUM|MONEY)\}(?:\.\{NUM\})? KZT\. K\*\*\{NUM\}\. Qaldyq/ostatok: \{(?:NUM|MONEY)\}(?:\.\{NUM\})? KZT":
        "{TIME} telefon nomiri arqyly audarym kelip tusti/ postupil perevod po nomeru telefona: {MONEY} KZT. K**{NUM}. Qaldyq/ostatok: {MONEY} KZT",

    r"\{CODE\}\.Kod posylki [-A-Za-z0-9]*\{NUM\}\. Srok hranenia \{NUM\} dney\. Uznat dopolnitelnuyu informaciu mozhete na post\.kz\.":
    "{CODE}.Kod posylki {CODE}. Srok hranenia {NUM} dney. Uznat dopolnitelnuyu informaciu mozhete na post.kz.",

    # Правила из aggregator.py, которых не было в generaliser.py (или были, но отличались)
    # telefon nomiri…USD/EUR/KZT - расширенная валюта
    r"\{TIME\} telefon nomiri arqyly audarym kelip tusti/ postupil perevod po nomeru telefona: \{(?:NUM|MONEY)\}(?:\.\{NUM\})? (?:KZT|USD|EUR|UZS)\. K\*\*\{NUM\}\. Qaldyq/ostatok: \{(?:NUM|MONEY)\}(?:\.\{NUM\})? (?:KZT|USD|EUR|UZS)":
        "{TIME} telefon nomiri arqyly audarym kelip tusti/ postupil perevod po nomeru telefona: {MONEY} {CURR}. K**{NUM}. Qaldyq/ostatok: {MONEY} {CURR}",

    # хвостовые «12345KZ.Kod posylki -{NUM}…»
    r"\d+[A-Z]{2}\.Kod posylki -\{NUM\}\. Srok hranenia \{NUM\} dney\. Uznat dopolnitelnuyu informaciu mozhete na post\.kz\.":
        "{CODE}.Kod posylki -{NUM}. Srok hranenia {NUM} dney. Uznat dopolnitelnuyu informaciu mozhete na post.kz.",
}

# --- Функция для базовой маскировки сообщений ---
def dynamic_mask(msg: str) -> str:
    """
    Выполняет первичную маскировку сырого сообщения, заменяя
    даты, время, ссылки, коды и числа на общие токены.
    """
    # 0) убрать дату в начале
    msg = re.sub(r'^(?:\d{2}[.-]\d{2}[.-]\d{2,4}|\d{4}-\d{2}-\d{2})\s*', '', msg)

    # 1) ссылки → {URL}
    msg = re.sub(r'https?://\S+', '{URL}', msg)

    # 2) время HH:MM:SS → {TIME}
    msg = re.sub(r'\b\d{2}:\d{2}:\d{2}\b', '{TIME}', msg)

    # 3) треки /t/XXXXXXXXXXXXX → /t/{TRACK}
    msg = re.sub(r'/t/[A-Za-z0-9]{1,13}', '/t/{TRACK}', msg)

    # 4) обобщить «Salemdeme kody … Saqtau merzimi»
    msg = re.sub(
        r'(Salemdeme kody)(.*?)(Saqtau merzimi)',
        r'\1 {CODE} \3',
        msg,
        flags=re.IGNORECASE
    )

    # 5) длинные alnum-коды (>10) → {CODE}
    def _code(m):
        w = m.group(0)
        if re.search(r'[A-Za-z]', w) and re.search(r'\d', w):
            return '{CODE}'
        return w
    msg = re.sub(r'\b[A-Za-z0-9]{10,}\b', _code, msg)

    # 6) все остальные числа → {NUM}
    msg = re.sub(r'\b\d+\b', '{NUM}', msg)

    return msg

# --- Функция для "супер-обобщения" паттернов ---
def super_generalize(pat: str) -> str:
    """
    Применяет правила "супер-обобщения" к уже маскированному паттерну.
    Сначала проверяет на "особые" случаи, затем применяет общие правила.
    """
    # сначала проверяем «специальные» случаи
    for rx, replacement in SPECIALS.items():
        if re.fullmatch(rx, pat):
            return replacement

    p = pat

    # 0) Убираем всё перед ".Kod posylki" (правило из aggregator.py, применяем его здесь)
    p = re.sub(r"^.*?\.Kod posylki", "{CODE}.Kod posylki", p)

    # 1) datetime — дата и время вместе ({NUM}-{NUM}-{NUM} {TIME} → {DATETIME})
    p = re.sub(r"\{NUM\}-\{NUM\}-\{NUM\} \{TIME\}", "{DATETIME}", p)

    # 2) суммы с валютами → {MONEY} {CURR}
    # пример: {NUM} {NUM},{NUM} USD → {MONEY} {CURR}
    p = re.sub(
        r"-?\{NUM\}(?:[ ,]\{NUM\})*(?:[.,]\{NUM\})? [A-Z]{3}\b",
        lambda m: f"{'-' if m.group(0).startswith('-') else ''}{{MONEY}} {{CURR}}",
        p
    )

    # 3) ссылки и треки
    p = re.sub(r"/t/\{\d+_TRACK\}", "{TRACK_URL}", p)
    p = re.sub(r"\{URL\}", "{TRACK_URL}", p)

    # 4) любые коды вида {N_CODE} → {CODE}
    p = re.sub(r"\{\d+_CODE\}", "{CODE}", p)

    # 5) сжимаем подряд несколько {NUM}{NUM}… → один {NUM} (из aggregator.py)
    # или (?:{NUM}\s*){2,} → {NUM} (из generaliser.py)
    # Объединим их в одно: если несколько {NUM} подряд, даже с пробелами, сжимаем в один {NUM}
    p = re.sub(r"(?:\{NUM\}\s*){2,}", "{NUM} ", p).strip()


    # 6) нормализуем пробелы и пунктуацию (исключая минус)
    p = re.sub(r"\s*([:/])\s*", r"\1", p)     # пробелы вокруг : и /
    p = re.sub(r"\s{2,}", " ", p)             # множественные пробелы → один
    p = p.strip()

    return p