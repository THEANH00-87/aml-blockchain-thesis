import pandas as pd
import networkx as nx
import mysql.connector
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier

# ===== CẤU HÌNH KẾT NỐI MYSQL — nhớ đổi mật khẩu đúng của bạn =====
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "dECUONG312@",   # <-- đổi thành mật khẩu MySQL bạn đã đặt
    "database": "aml_thesis"
}

# ===== 1. Đọc dữ liệu =====
print("Đang đọc dữ liệu...")
features = pd.read_csv("data/elliptic_txs_features.csv", header=None)
edges = pd.read_csv("data/elliptic_txs_edgelist.csv")
classes = pd.read_csv("data/elliptic_txs_classes.csv")

features.columns = ["txId", "time_step"] + [f"feat_{i}" for i in range(1, 166)]

# ===== 2. Xây đồ thị để tính out_degree/in_degree =====
G = nx.from_pandas_edgelist(edges, source="txId1", target="txId2", create_using=nx.DiGraph())
out_degrees = dict(G.out_degree())
in_degrees = dict(G.in_degree())

# ===== 3. Kết nối MySQL =====
print("Đang kết nối MySQL...")
conn = mysql.connector.connect(**DB_CONFIG)
cursor = conn.cursor()

# ===== 4. Đẩy dữ liệu vào bảng `transactions` (giới hạn 5000 dòng đầu để demo nhanh) =====
print("Đang lưu vào bảng transactions...")
sample = features.head(5000)  # chỉ lấy mẫu 5000 dòng để chạy nhanh, không cần đẩy hết 200k dòng
count = 0
for _, row in sample.iterrows():
    tx_id = int(row["txId"])
    time_step = int(row["time_step"])
    out_deg = out_degrees.get(tx_id, 0)
    in_deg = in_degrees.get(tx_id, 0)
    sql = """INSERT IGNORE INTO transactions (tx_id, time_step, out_degree, in_degree)
             VALUES (%s, %s, %s, %s)"""
    cursor.execute(sql, (tx_id, time_step, out_deg, in_deg))
    count += 1

conn.commit()
print(f"Đã lưu {count} giao dịch vào bảng transactions.")

# ===== 5. Huấn luyện lại mô hình AI và lưu kết quả dự đoán vào bảng `predictions` =====
print("\nĐang huấn luyện mô hình để lấy dự đoán...")
data = features.merge(classes, on="txId", how="inner")
data = data[data["class"] != "unknown"]
data["label"] = data["class"].apply(lambda x: 1 if x == "1" else 0)

X = data.drop(columns=["txId", "class", "label"])
y = data["label"]
X_train, X_test, y_train, y_test, txid_train, txid_test = train_test_split(
    X, y, data["txId"], test_size=0.2, random_state=42, stratify=y
)

model = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
model.fit(X_train, y_train)

y_pred = model.predict(X_test)
y_pred_proba = model.predict_proba(X_test)

print("Đang lưu kết quả dự đoán vào bảng predictions...")
count_pred = 0
for tx_id, pred, proba in zip(txid_test, y_pred, y_pred_proba):
    label = "illicit" if pred == 1 else "licit"
    confidence = float(max(proba))

    # Đảm bảo tx_id đã có trong bảng transactions (bắt buộc vì có khóa ngoại)
    cursor.execute(
        "INSERT IGNORE INTO transactions (tx_id) VALUES (%s)", (int(tx_id),)
    )
    sql = """INSERT INTO predictions (tx_id, predicted_label, confidence_score)
             VALUES (%s, %s, %s)"""
    cursor.execute(sql, (int(tx_id), label, confidence))
    count_pred += 1

conn.commit()
print(f"Đã lưu {count_pred} kết quả dự đoán vào bảng predictions.")

# ===== 6. Đóng kết nối =====
cursor.close()
conn.close()
print("\nHoàn tất! Dữ liệu đã được lưu vào MySQL.")