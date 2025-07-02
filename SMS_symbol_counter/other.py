import pandas as pd
from pathlib import Path

# Папка с частями
parts = sorted(Path("csv/out").glob("initial_file.csv"))

# Читаем все в один DataFrame
dfs = []
for p in parts:
    df = pd.read_csv(p, encoding="utf-8")
    dfs.append(df)
full = pd.concat(dfs, ignore_index=True)

# Агрегируем: суммируем Count по Pattern и Traffic Type
summary = (
    full
      .groupby(["Pattern", "Traffic Type"], as_index=False)
      .agg({"Count": "sum"})
      .sort_values("Count", ascending=False)
)

# Сохраняем сводный CSV
summary.to_csv("patterns_aggregated.csv", index=False, encoding="utf-8")

print("Получили", len(summary), "уникальных (Pattern, Traffic) комбинаций.")
print("Всего строк в агрегате:", len(full))
