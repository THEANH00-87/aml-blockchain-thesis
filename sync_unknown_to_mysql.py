import pandas as pd
import mysql.connector

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "dECUONG312@",
    "database": "aml_thesis"
}

# ===== 1. Đọc kết quả dự đoán cho unknown =====
print("Đang đọc dữ liệu dự đoán unknown...")
df = pd.read_csv("data/unknown_predictions.csv")
print(f"Tổng số dòng cần đồng bộ: {len(df)}")

# ===== 2. Kết nối MySQL =====
conn = mysql.connector.connect(**DB_CONFIG)
cursor = conn.cursor()

# ===== 3. Đảm bảo tất cả tx_id đã có trong bảng transactions (bắt buộc vì khóa ngoại) =====
print("Đang đồng bộ bảng transactions...")
tx_ids = [(int(tx_id),) for tx_id in df["txId"]]

batch_size = 5000
for i in range(0, len(tx_ids), batch_size):
    batch = tx_ids[i:i+batch_size]
    cursor.executemany("INSERT IGNORE INTO transactions (tx_id) VALUES (%s)", batch)
    conn.commit()
    print(f"  Đã xử lý {min(i+batch_size, len(tx_ids))}/{len(tx_ids)} transactions...")

# ===== 4. Xóa các dự đoán "unknown" cũ (nếu có, để tránh trùng khi chạy lại) =====
print("Đang xóa dự đoán unknown cũ (nếu có)...")
cursor.execute("DELETE FROM predictions WHERE model_version = 'random_forest_v1_unknown'")
conn.commit()

# ===== 5. Chèn toàn bộ kết quả dự đoán mới vào bảng predictions =====
print("Đang lưu dự đoán mới vào bảng predictions...")
insert_data = [
    (int(row["txId"]), row["predicted_label"], float(row["confidence"]), "random_forest_v1_unknown")
    for _, row in df.iterrows()
]

sql = """INSERT INTO predictions (tx_id, predicted_label, confidence_score, model_version)
         VALUES (%s, %s, %s, %s)"""

for i in range(0, len(insert_data), batch_size):
    batch = insert_data[i:i+batch_size]
    cursor.executemany(sql, batch)
    conn.commit()
    print(f"  Đã lưu {min(i+batch_size, len(insert_data))}/{len(insert_data)} dự đoán...")

cursor.close()
conn.close()
print(f"\nHoàn tất! Đã đồng bộ {len(df)} dự đoán (unknown) vào MySQL.")