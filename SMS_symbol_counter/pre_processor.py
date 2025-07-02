import csv
import re
from datetime import datetime
from collections import defaultdict, deque

# Путь к входному и выходному CSV
INPUT_CSV  = "csv/in/2025-05-01_2025-05-31(1).csv"
OUTPUT_CSV = "csv/out/2025-05-01_2025-05-31_merged_strict.csv"
SEP        = '\t'
MSG_COL    = "message"
PHONE_COL  = "phone"
DATE_COL   = "send_date"
TIME_WINDOW = 20  # сек

# Регулярки для токенов
TOKEN_REGEXPS = [
    re.compile(r"\b[A-Z]{2}\d{5,}KZ\b"),  # AO123456KZ, CN168298188KZ…
    re.compile(r"\b\d{6}\b"),             # ровно 6 цифр (OTP)
]

# Регулярка для обнаружения начала фрагмента с «.Kod posylki»
CODE_START_RX = re.compile(r"^[A-Z0-9]{2,}\.Kod\s+posylki")

def extract_tokens(text):
    s = set()
    for rx in TOKEN_REGEXPS:
        s |= set(rx.findall(text))
    return s

def ends_complete(text):
    return bool(re.search(r"[\.!?]$", text.strip()))

def load_records(path):
    recs = []
    with open(path, newline='', encoding='utf-8') as f:
        rdr = csv.DictReader(f, delimiter=SEP, quoting=csv.QUOTE_NONE)
        for row in rdr:
            recs.append({
                "phone": row[PHONE_COL].strip(),
                "date":  datetime.fromisoformat(row[DATE_COL]),
                "msg":   row[MSG_COL].strip(),
                "row":   row
            })
    return recs

def build_graph(nodes):
    graph = defaultdict(list)
    by_phone = defaultdict(list)
    for i, n in enumerate(nodes):
        by_phone[n["phone"]].append(i)

    for phone, idxs in by_phone.items():
        for i in idxs:
            ti, mi, tok_i = nodes[i]["date"], nodes[i]["msg"], extract_tokens(nodes[i]["msg"])
            for j in idxs:
                if j <= i: continue
                tj, mj = nodes[j]["date"], nodes[j]["msg"]
                if abs((tj - ti).total_seconds()) > TIME_WINDOW:
                    continue

                # 1) надёжное слияние по ≥2 токенам
                tok_j = extract_tokens(mj)
                if len(tok_i & tok_j) >= 2:
                    graph[i].append(j)
                    graph[j].append(i)
                    continue

                # 2) слияние по незавершённости
                if not ends_complete(mi) or not ends_complete(mj):
                    graph[i].append(j)
                    graph[j].append(i)

    return graph

def find_components(graph, n):
    seen = [False]*n
    comps = []
    for i in range(n):
        if seen[i]: continue
        q, comp = deque([i]), []
        seen[i] = True
        while q:
            u = q.popleft()
            comp.append(u)
            for v in graph[u]:
                if not seen[v]:
                    seen[v] = True
                    q.append(v)
        comps.append(comp)
    return comps

def merge_component(nodes, comp):
    block = sorted((nodes[i] for i in comp), key=lambda r: r["date"])

    # если две части перепутаны местами, поправим
    if len(block) == 2:
        first, second = block
        if not re.match(r"^(Sizge|Salemdeme|/t/)", first["msg"]) and re.match(r"^(Sizge|Salemdeme|/t/)", second["msg"]):
            block.reverse()

    # склейка с учётом CODE_START_RX
    merged_parts = []
    for rec in block:
        text = rec["msg"].strip()
        if not merged_parts:
            merged_parts.append(text)
        else:
            prev = merged_parts[-1]
            # если следующий фрагмент — трек/код, сразу прилепляем без пробела
            if CODE_START_RX.search(text):
                merged_parts[-1] = prev + text
            else:
                # обычная склейка через пробел
                merged_parts[-1] = prev + " " + text

    merged_msg = merged_parts[0]
    out = block[0]["row"].copy()
    out[MSG_COL]  = merged_msg
    out[DATE_COL] = block[-1]["date"].isoformat()
    return out

def main():
    records = load_records(INPUT_CSV)
    graph   = build_graph(records)
    comps   = find_components(graph, len(records))

    output = []
    for comp in comps:
        if len(comp) == 1:
            output.append(records[comp[0]]["row"])
        else:
            output.append(merge_component(records, comp))

    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f,
            fieldnames=records[0]["row"].keys(),
            delimiter=SEP
        )
        writer.writeheader()
        writer.writerows(output)

    print(f"✅ Готово — {len(output)} строк в {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
