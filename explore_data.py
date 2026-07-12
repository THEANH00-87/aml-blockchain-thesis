import pandas as pd

# Đọc 3 file dữ liệu
features = pd.read_csv("data/elliptic_txs_features.csv", header=None)
edges = pd.read_csv("data/elliptic_txs_edgelist.csv")
classes = pd.read_csv("data/elliptic_txs_classes.csv")

print("===== FEATURES =====")
print("Số dòng, số cột:", features.shape)
print(features.head())

print("\n===== EDGES (cạnh giao dịch) =====")
print("Số dòng, số cột:", edges.shape)
print(edges.head())

print("\n===== CLASSES (nhãn) =====")
print("Số dòng, số cột:", classes.shape)
print(classes.head())
print("\nSố lượng theo từng nhãn:")
print(classes['class'].value_counts())