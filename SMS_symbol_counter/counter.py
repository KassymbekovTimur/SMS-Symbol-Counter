import csv

csv.field_size_limit(10**7)

FILENAME = "merged_contextual.csv"
SEP = '\t'  # Или ',' если CSV с запятыми

with open(FILENAME, encoding="utf-8") as f:
    reader = csv.reader(f, delimiter=SEP)
    next(reader)  # Пропустить заголовок
    count = sum(1 for _ in reader)

print(f"📦 Всего сообщений: {count}")
