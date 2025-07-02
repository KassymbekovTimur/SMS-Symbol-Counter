import csv
import re
import logging
from collections import Counter

# Логирование
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# Конфигурация
INPUT_FILE = "csv/in/2025-05-01_2025-05-31(1).csv"
OUTPUT_MD = "top_patterns.md"
OUTPUT_CSV_PREFIX = "patterns_part"
SEP = '\t'
MIN_LEN = 2
TOP_N = 200
MAX_ROWS_PER_FILE = 650_000

# Регулярки для шаблонов
PATTERNS = {
    "Sizdin belsendiru kody": re.compile(r"^Sizdin belsendiru kody / Vash kod aktivatsii:\d+", re.IGNORECASE),
    "Tekseru kody": re.compile(r"^Tekseru kody/Kod proverki:\d+", re.IGNORECASE),
    "Kod posylki": re.compile(r"^\d{3}KZ\.Kod posylki", re.IGNORECASE),
}

# Очистка
def clean_message(raw: str) -> str:
    return re.split(r"\d{4}-\d{2}-\d{2}", raw, maxsplit=1)[0].strip()

# Группировка
def group_patterns(counter: Counter) -> Counter:
    grouped = Counter()
    for (msg, traffic), count in counter.items():
        for label, regex in PATTERNS.items():
            if regex.match(msg):
                if label == "Kod posylki":
                    msg = "<код>KZ.Kod posylki -. Srok hranenia 14 dney. Uznat dopolnitelnuyu informaciu mozhete na post.kz."
                elif label == "Sizdin belsendiru kody":
                    msg = "Sizdin belsendiru kody / Vash kod aktivatsii:<код>"
                elif label == "Tekseru kody":
                    msg = "Tekseru kody/Kod proverki:<код>"
                break
        grouped[(msg, traffic)] += count
    return grouped

def write_csv_split(grouped, prefix, max_rows):
    file_index = 1
    row_count = 0
    current_writer = None
    out_file = None

    for i, ((msg, traffic), count) in enumerate(grouped.items()):
        if row_count % max_rows == 0:
            if out_file:
                out_file.close()
            filename = f"{prefix}_{file_index}.csv"
            out_file = open(filename, "w", encoding="utf-8", newline='')
            current_writer = csv.writer(out_file)
            current_writer.writerow(["Pattern", "Traffic Type", "Count"])
            file_index += 1
            row_count = 0
            logger.info(f"Создан новый CSV файл: {filename}")

        current_writer.writerow([msg, traffic, count])
        row_count += 1

    if out_file:
        out_file.close()
        logger.info(f"Всего файлов записано: {file_index - 1}")

if __name__ == "__main__":
    counter = Counter()

    with open(INPUT_FILE, encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=SEP, quoting=csv.QUOTE_NONE)
        header = next(reader)

        try:
            msg_idx = header.index("message")
            traffic_idx = header.index("traffic_type")
        except ValueError:
            raise Exception("Файл должен содержать колонки 'message' и 'traffic_type'")

        for row in reader:
            if len(row) <= max(msg_idx, traffic_idx):
                continue

            raw = row[msg_idx]
            traffic = row[traffic_idx].strip() or "UNKNOWN"
            msg = clean_message(raw)

            if len(msg) >= MIN_LEN:
                counter[(msg, traffic)] += 1

    grouped = group_patterns(counter)

    # Markdown вывод
    with open(OUTPUT_MD, "w", encoding="utf-8") as md:
        md.write("| # | Count | Traffic Type | Pattern |\n")
        md.write("|:-:|------:|:-------------|:--------|\n")
        for i, ((msg, traffic), count) in enumerate(grouped.most_common(TOP_N), start=1):
            safe = msg.replace("|", "\\|")
            md.write(f"| {i} | {count} | {traffic} | {safe} |\n")

    # CSV с разбивкой
    write_csv_split(grouped, OUTPUT_CSV_PREFIX, MAX_ROWS_PER_FILE)

    # Статистика
    print("Всего уникальных очищенных сообщений:", len(counter))
    print("Уникальных шаблонов после группировки:", len(grouped))
    print("After grouping: freq >= 10:", sum(1 for c in grouped.values() if c >= 10))
