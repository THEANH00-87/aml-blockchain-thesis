import os
import json
import mysql.connector
from web3 import Web3
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

# ===== Cấu hình =====
load_dotenv()

RPC_URL = os.getenv("ALCHEMY_RPC_URL")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")
DB_PASSWORD = os.getenv("DB_PASSWORD")

app = Flask(__name__)
CORS(app)  # Cho phép frontend web gọi API này (khác domain/port)

# ===== Kết nối Web3 và Smart Contract =====
w3 = Web3(Web3.HTTPProvider(RPC_URL))
with open("contract_abi.json", "r") as f:
    contract_abi = json.load(f)
contract = w3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=contract_abi)
account = w3.eth.account.from_key(PRIVATE_KEY)

# ===== Hàm tiện ích: mở kết nối MySQL mới cho mỗi request =====
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password=DB_PASSWORD,
        database="aml_thesis"
    )

# ===== API 1: Lấy danh sách giao dịch =====
@app.route("/api/transactions", methods=["GET"])
def get_transactions():
    limit = request.args.get("limit", 50, type=int)
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM transactions ORDER BY id DESC LIMIT %s", (limit,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(rows)

# ===== API 2: Lấy danh sách kết quả dự đoán AI =====
@app.route("/api/predictions", methods=["GET"])
def get_predictions():
    label = request.args.get("label", None)  # lọc theo 'licit' hoặc 'illicit' nếu có
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    if label:
        cursor.execute("SELECT * FROM predictions WHERE predicted_label = %s ORDER BY id DESC LIMIT 100", (label,))
    else:
        cursor.execute("SELECT * FROM predictions ORDER BY id DESC LIMIT 100")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(rows)

# ===== API 3: Lấy danh sách chuỗi nghi ngờ =====
@app.route("/api/suspicious-chains", methods=["GET"])
def get_suspicious_chains():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM suspicious_chains ORDER BY chain_length DESC LIMIT 50")
    rows = cursor.fetchall()
    for row in rows:
        row["tx_id_list"] = json.loads(row["tx_id_list"])  # chuyển chuỗi JSON thành list thật
    cursor.close()
    conn.close()
    return jsonify(rows)

# ===== API 4: Lấy danh sách báo cáo đã ghi lên blockchain (từ MySQL, nhanh) =====
@app.route("/api/reports", methods=["GET"])
def get_reports():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM str_reports ORDER BY id DESC LIMIT 50")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(rows)

# ===== API 5: Lấy dữ liệu trực tiếp từ blockchain (chứng minh tính bất biến) =====
@app.route("/api/blockchain/reports", methods=["GET"])
def get_blockchain_reports():
    total = contract.functions.getReportCount().call()
    reports = []
    for i in range(total):
        tx_id, reason, timestamp, reporter = contract.functions.getReport(i).call()
        reports.append({
            "index": i,
            "txId": tx_id,
            "reason": reason,
            "timestamp": timestamp,
            "reporter": reporter
        })
    return jsonify({"total": total, "reports": reports})

# ===== API 6: Tạo báo cáo mới, ghi lên blockchain + lưu MySQL =====
@app.route("/api/reports", methods=["POST"])
def create_report():
    data = request.get_json()
    tx_id = data.get("tx_id")
    reason = data.get("reason")

    if not tx_id or not reason:
        return jsonify({"error": "Thiếu tx_id hoặc reason"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    nonce = w3.eth.get_transaction_count(account.address)
    txn = contract.functions.createReport(int(tx_id), reason).build_transaction({
        "chainId": 11155111,
        "gas": 300000,
        "gasPrice": w3.eth.gas_price,
        "nonce": nonce,
    })
    signed_txn = w3.eth.account.sign_transaction(txn, private_key=PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    cursor.execute("INSERT IGNORE INTO transactions (tx_id) VALUES (%s)", (tx_id,))
    cursor.execute(
        "INSERT INTO str_reports (tx_id, reason, status, blockchain_tx_hash) VALUES (%s, %s, 'confirmed', %s)",
        (tx_id, reason, tx_hash.hex())
    )
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({
        "success": True,
        "tx_hash": tx_hash.hex(),
        "block": receipt.blockNumber
    })

# ===== Chạy server =====
if __name__ == "__main__":
    app.run(debug=True, port=5000)