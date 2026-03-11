import pandas as pd
import json

INPUT_FILE = "markers.xlsx"
OUTPUT_FILE = "markers.json"

df = pd.read_excel(INPUT_FILE, header=0)

result = {}

for _, row in df.iterrows():
    category = str(row[0]).strip()
    queries_raw = row[1]

    if not category or pd.isna(queries_raw):
        continue

    try:
        queries = json.loads(queries_raw)
        result[category] = queries
    except json.JSONDecodeError:
        print(f"❌ Ошибка JSON в категории: {category}")

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"✅ Готово: {OUTPUT_FILE}")
