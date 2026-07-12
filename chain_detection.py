import pandas as pd
import networkx as nx

# ===== 1. Đọc dữ liệu =====
print("Đang đọc dữ liệu...")
edges = pd.read_csv("data/elliptic_txs_edgelist.csv")
classes = pd.read_csv("data/elliptic_txs_classes.csv")
unknown_predictions = pd.read_csv("data/unknown_predictions.csv")  # kết quả AI đoán cho unknown

# ===== 2. Xây dựng đồ thị =====
print("Đang xây dựng đồ thị...")
G = nx.from_pandas_edgelist(
    edges, source="txId1", target="txId2", create_using=nx.DiGraph()
)
label_map = dict(zip(classes["txId"], classes["class"]))
nx.set_node_attributes(G, label_map, "label")

# ===== 3. Tạo bản đồ nhãn MỞ RỘNG: nhãn gốc + AI đoán cho unknown (độ tin cậy cao) =====
CONFIDENCE_THRESHOLD = 0.9  # chỉ tin những dự đoán có độ tin cậy >= 90%
label_map_expanded = dict(label_map)  # copy từ nhãn gốc

so_luong_them_moi = 0
for _, row in unknown_predictions.iterrows():
    if row["predicted_label"] == "illicit" and row["confidence"] >= CONFIDENCE_THRESHOLD:
        label_map_expanded[row["txId"]] = "1"  # coi như illicit thật để tìm chuỗi
        so_luong_them_moi += 1

print(f"Đã bổ sung {so_luong_them_moi} giao dịch (AI đoán illicit, độ tin cậy >= {CONFIDENCE_THRESHOLD}) vào danh sách nghi ngờ.")

# ===== 4. Hàm đếm chuỗi các giao dịch ILLICIT nối tiếp nhau (dùng chung cho cả 2 lần chạy) =====
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

def quet_toan_bo_chuoi(label_map_dung, danh_sach_illicit_ids):
    all_chains = []
    visited = set()
    for tx_id in danh_sach_illicit_ids:
        if tx_id in visited:
            continue
        chain = do_dai_chuoi_illicit(G, tx_id, label_map_dung)
        visited.update(chain)
        if len(chain) > 1:
            all_chains.append(chain)
    all_chains.sort(key=len, reverse=True)
    return all_chains

# ===== 5. Chạy với nhãn GỐC (chỉ 4.545 illicit đã biết) =====
print("\n===== KẾT QUẢ VỚI NHÃN GỐC (chỉ dữ liệu đã biết) =====")
illicit_ids_goc = classes[classes["class"] == "1"]["txId"].tolist()
chains_goc = quet_toan_bo_chuoi(label_map, illicit_ids_goc)
print(f"Số chuỗi tìm được: {len(chains_goc)}")
if chains_goc:
    print(f"Chuỗi dài nhất: {len(chains_goc[0])} giao dịch")

# ===== 6. Chạy với nhãn MỞ RỘNG (bao gồm cả AI đoán từ unknown) =====
print("\n===== KẾT QUẢ VỚI NHÃN MỞ RỘNG (đã có thêm AI đoán) =====")
illicit_ids_mo_rong = [tx_id for tx_id, label in label_map_expanded.items() if label == "1"]
chains_mo_rong = quet_toan_bo_chuoi(label_map_expanded, illicit_ids_mo_rong)
print(f"Số chuỗi tìm được: {len(chains_mo_rong)}")

print("\n===== TOP 10 chuỗi dài nhất (nhãn mở rộng) =====")
for i, chain in enumerate(chains_mo_rong[:10]):
    print(f"Chuỗi {i+1} (dài {len(chain)} giao dịch): {chain[:10]}{'...' if len(chain) > 10 else ''}")

if chains_mo_rong:
    do_dai_trung_binh = sum(len(c) for c in chains_mo_rong) / len(chains_mo_rong)
    print(f"\nĐộ dài trung bình của các chuỗi (nhãn mở rộng): {do_dai_trung_binh:.2f}")

# ===== 7. So sánh trực tiếp =====
print("\n===== SO SÁNH =====")
print(f"Nhãn gốc:      {len(chains_goc)} chuỗi, dài nhất {len(chains_goc[0]) if chains_goc else 0}")
print(f"Nhãn mở rộng:  {len(chains_mo_rong)} chuỗi, dài nhất {len(chains_mo_rong[0]) if chains_mo_rong else 0}")
print(f"→ Tìm thêm được {len(chains_mo_rong) - len(chains_goc)} chuỗi nhờ kết hợp với dự đoán AI")