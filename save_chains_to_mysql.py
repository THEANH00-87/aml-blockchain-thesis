import pandas as pd
import networkx as nx
import mysql.connector
import json

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "dECUONG312@",
    "database": "aml_thesis"
}

# ===== 1. Đọc dữ liệu =====
print("Đang đọc dữ liệu...")
edges = pd.read_csv("data/elliptic_txs_edgelist.csv")
classes = pd.read_csv("data/elliptic_txs_classes.csv")
unknown_predictions = pd.read_csv("data/unknown_predictions.csv")

# ===== 2. Xây dựng đồ thị =====
print("Đang xây dựng đồ thị...")
G = nx.from_pandas_edgelist(edges, source="txId1", target="txId2", create_using=nx.DiGraph())
label_map = dict(zip(classes["txId"], classes["class"]))

# ===== 3. Mở rộng nhãn với kết quả AI đoán cho unknown =====
CONFIDENCE_THRESHOLD = 0.9
label_map_expanded = dict(label_map)
so_luong_them = 0
for _, row in unknown_predictions.iterrows():
    if row["predicted_label"] == "illicit" and row["confidence"] >= CONFIDENCE_THRESHOLD:
        label_map_expanded[row["txId"]] = "1"
        so_luong_them += 1
print(f"Đã bổ sung {so_luong_them} giao dịch từ AI vào danh sách nghi ngờ.")

def do_dai_chuoi_illicit(G, start_node, label_map_dung):
    chain = [start_node]
    current = start_node
    while True:
        successors = list(G.successors(current))
        next_illicit = [s for s in successors if label_map_dung.get(s) == "1"]
        if not next_illicit:
            break
        current = next_illicit[0]
        chain.append(current)
    return chain

# ===== 4. Quét toàn bộ chuỗi với nhãn MỞ RỘNG =====
print("Đang quét các chuỗi illicit (nhãn mở rộng)...")
illicit_ids = [tx_id for tx_id, label in label_map_expanded.items() if label == "1"]
all_chains = []
visited = set()
for tx_id in illicit_ids:
    if tx_id in visited:
        continue
    chain = do_dai_chuoi_illicit(G, tx_id, label_map_expanded)
    visited.update(chain)
    if len(chain) > 1:
        all_chains.append(chain)

all_chains.sort(key=len, reverse=True)
print(f"Tìm được {len(all_chains)} chuỗi (>= 2 giao dịch)")

# Chỉ lưu các chuỗi dài >= 5 giao dịch
chains_to_save = [c for c in all_chains if len(c) >= 5]
print(f"Sẽ lưu {len(chains_to_save)} chuỗi đáng chú ý (độ dài >= 5) vào MySQL")

# ===== 5. Kết nối MySQL, xóa dữ liệu cũ, lưu bộ mới =====
conn = mysql.connector.connect(**DB_CONFIG)
cursor = conn.cursor()

print("Đang xóa dữ liệu chuỗi cũ...")
cursor.execute("DELETE FROM suspicious_chains")
conn.commit()

count = 0
for chain in chains_to_save:
    chain_json = json.dumps(chain)
    sql = "INSERT INTO suspicious_chains (chain_length, tx_id_list) VALUES (%s, %s)"
    cursor.execute(sql, (len(chain), chain_json))
    count += 1

conn.commit()
cursor.close()
conn.close()
print(f"\nHoàn tất! Đã lưu {count} chuỗi nghi ngờ (bộ mở rộng) vào bảng suspicious_chains.")