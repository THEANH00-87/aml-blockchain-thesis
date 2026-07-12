import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix

# ===== 1. Đọc dữ liệu =====
print("Đang đọc dữ liệu...")
features = pd.read_csv("data/elliptic_txs_features.csv", header=None)
classes = pd.read_csv("data/elliptic_txs_classes.csv")

# Đặt tên cột dễ hiểu hơn: cột 0 = txId, cột 1 = time_step, còn lại là feature
features.columns = ["txId", "time_step"] + [f"feat_{i}" for i in range(1, 166)]

# ===== 2. Ghép features với nhãn theo txId =====
data = features.merge(classes, on="txId", how="inner")
print("Sau khi ghép:", data.shape)

# ===== 3. Tách riêng phần CÓ NHÃN (để train) và phần UNKNOWN (để đoán sau) =====
data_labeled = data[data["class"] != "unknown"].copy()
data_unknown = data[data["class"] == "unknown"].copy()
print("Số giao dịch có nhãn (dùng để train/test):", data_labeled.shape[0])
print("Số giao dịch unknown (sẽ dự đoán sau):", data_unknown.shape[0])
print(data_labeled["class"].value_counts())

# Đổi nhãn: '1' (illicit) -> 1, '2' (licit) -> 0  (để dễ tính toán)
data_labeled["label"] = data_labeled["class"].apply(lambda x: 1 if x == "1" else 0)

# ===== 4. Tách dữ liệu đầu vào (X) và nhãn (y) =====
X = data_labeled.drop(columns=["txId", "class", "label"])
y = data_labeled["label"]

# ===== 5. Chia tập train/test (80% train, 20% test) =====
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print(f"\nSố mẫu train: {len(X_train)}, test: {len(X_test)}")

# ===== 6. Huấn luyện mô hình Random Forest =====
print("\nĐang huấn luyện mô hình...")
model = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
model.fit(X_train, y_train)

# ===== 7. Đánh giá mô hình (trên phần đã biết đáp án) =====
y_pred = model.predict(X_test)

print("\n===== KẾT QUẢ ĐÁNH GIÁ (trên tập test đã biết đáp án) =====")
print(classification_report(y_test, y_pred, target_names=["licit (0)", "illicit (1)"]))

print("Ma trận nhầm lẫn (Confusion Matrix):")
print(confusion_matrix(y_test, y_pred))

# ===== 8. ÁP DỤNG model đã học để đoán cho UNKNOWN (bước mới thêm) =====
print("\n\n===== DỰ ĐOÁN CHO CÁC GIAO DỊCH UNKNOWN =====")
X_unknown = data_unknown.drop(columns=["txId", "class"])

unknown_pred = model.predict(X_unknown)
unknown_proba = model.predict_proba(X_unknown)

data_unknown["predicted_label"] = ["illicit" if p == 1 else "licit" for p in unknown_pred]
data_unknown["confidence"] = unknown_proba.max(axis=1)

so_luong_illicit = (data_unknown["predicted_label"] == "illicit").sum()
so_luong_licit = (data_unknown["predicted_label"] == "licit").sum()

print(f"Tổng số giao dịch unknown đã đoán: {len(data_unknown)}")
print(f"  → Đoán là ILLICIT (nghi ngờ rửa tiền): {so_luong_illicit}")
print(f"  → Đoán là LICIT (có khả năng bình thường): {so_luong_licit}")

print("\nTop 20 giao dịch unknown có độ tin cậy 'illicit' cao nhất:")
top_illicit = data_unknown[data_unknown["predicted_label"] == "illicit"] \
    .sort_values("confidence", ascending=False) \
    .head(20)
print(top_illicit[["txId", "predicted_label", "confidence"]].to_string(index=False))

# Lưu toàn bộ kết quả ra file CSV để xem lại sau
data_unknown[["txId", "predicted_label", "confidence"]].to_csv(
    "data/unknown_predictions.csv", index=False
)
print("\nĐã lưu toàn bộ kết quả dự đoán vào file: data/unknown_predictions.csv")