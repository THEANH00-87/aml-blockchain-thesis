import pandas as pd
import networkx as nx

# ===== 1. Đọc dữ liệu =====
print("Đang đọc dữ liệu...")
edges = pd.read_csv("data/elliptic_txs_edgelist.csv")
classes = pd.read_csv("data/elliptic_txs_classes.csv")

# ===== 2. Xây dựng đồ thị có hướng (Directed Graph) =====
# Có hướng vì tiền chuyển từ giao dịch A -> giao dịch B, có thứ tự
print("Đang xây dựng đồ thị...")
G = nx.from_pandas_edgelist(
    edges, source="txId1", target="txId2", create_using=nx.DiGraph()
)

print(f"Số đỉnh (giao dịch): {G.number_of_nodes()}")
print(f"Số cạnh (liên kết): {G.number_of_edges()}")

# ===== 3. Gán nhãn illicit/licit/unknown vào từng node để tiện tra cứu =====
label_map = dict(zip(classes["txId"], classes["class"]))
nx.set_node_attributes(G, label_map, "label")

# ===== 4. Phân tích: bậc ra (out-degree) và bậc vào (in-degree) =====
# Bậc ra cao bất thường -> có thể là dấu hiệu "layering" (1 nguồn tiền chia ra nhiều nhánh)
out_degrees = dict(G.out_degree())
in_degrees = dict(G.in_degree())

# Lấy top 10 giao dịch có bậc ra cao nhất
top_out = sorted(out_degrees.items(), key=lambda x: x[1], reverse=True)[:10]
print("\n===== TOP 10 giao dịch có nhiều nhánh chuyển tiếp nhất (out-degree) =====")
for tx_id, degree in top_out:
    label = label_map.get(tx_id, "không rõ")
    print(f"txId: {tx_id} | Số nhánh chuyển đi: {degree} | Nhãn: {label}")

# ===== 5. Tìm chu trình (cycle) - dấu hiệu tiền "quay vòng" để rửa =====
print("\nĐang tìm chu trình trong đồ thị (có thể mất một chút thời gian)...")
try:
    cycles = list(nx.simple_cycles(G, length_bound=5))
    print(f"Số chu trình tìm được (độ dài <= 5): {len(cycles)}")
    if cycles:
        print("Ví dụ 5 chu trình đầu tiên:")
        for c in cycles[:5]:
            print(c)
except Exception as e:
    print("Không tìm được chu trình hoặc đồ thị quá lớn:", e)

# ===== 6. So sánh: các giao dịch illicit có xu hướng out-degree cao hơn không? =====
illicit_ids = classes[classes["class"] == "1"]["txId"].tolist()
illicit_out_degrees = [out_degrees.get(tx_id, 0) for tx_id in illicit_ids if tx_id in out_degrees]

licit_ids = classes[classes["class"] == "2"]["txId"].tolist()
licit_out_degrees = [out_degrees.get(tx_id, 0) for tx_id in licit_ids if tx_id in out_degrees]

print(f"\nOut-degree trung bình của giao dịch ILLICIT: {sum(illicit_out_degrees)/len(illicit_out_degrees):.3f}")
print(f"Out-degree trung bình của giao dịch LICIT: {sum(licit_out_degrees)/len(licit_out_degrees):.3f}")