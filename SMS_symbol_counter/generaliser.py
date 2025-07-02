import csv
from collections import defaultdict
# Импортируем все необходимое из нашего нового модуля
from pattern_utils import compute_segments, dynamic_mask, super_generalize

INPUT_FILE   = "entry/to/data"
OUTPUT_FILE  = "patterns_report_full.csv"
SEP          = '\t'
MSG_COL      = "message"
TYPE_COL     = "traffic_type"

# ----------------------------------------------------------------------------
stats = defaultdict(lambda: {"count": 0, "example": None})

with open(INPUT_FILE, encoding="utf-8") as f:
    reader = csv.DictReader(f, delimiter=SEP, quoting=csv.QUOTE_NONE)
    for row in reader:
        text    = row.get(MSG_COL, "").strip()
        traffic = row.get(TYPE_COL, "").strip() or "Нет типа"
        if len(text) < 3: # Пропускаем слишком короткие сообщения
            continue

        # 1) базовая маскировка с помощью функции из pattern_utils
        pat = dynamic_mask(text)
        # 2) «супер-обобщение» с помощью функции из pattern_utils
        pat = super_generalize(pat)

        key = (pat, traffic)
        cell = stats[key]
        cell["count"] += 1
        # Храним самый длинный пример, чтобы он был полностью виден
        if cell["example"] is None or len(text) > len(cell["example"]):
            cell["example"] = text

# ----------------------------------------------------------------------------
with open(OUTPUT_FILE, "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f)
    w.writerow([
        "Pattern",
        "Example",
        "Total Count",
        "Length",
        "SMS Segments",
        "Traffic Type"
    ])
    for (pat, traffic), data in sorted(
            stats.items(),
            key=lambda kv: kv[1]["count"],
            reverse=True):
        example = data["example"]
        cnt     = data["count"]
        length, segs = compute_segments(example) # Используем compute_segments из pattern_utils
        w.writerow([
            pat,
            example,
            cnt,
            length,
            segs,
            traffic
        ])

print("Готово — полный отчёт с «супер-обобщением» в", OUTPUT_FILE)