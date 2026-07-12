import os
import json
import mysql.connector
from web3 import Web3
from dotenv import load_dotenv

# ===== 1. Đọc cấu hình từ file .env =====
load_dotenv()

RPC_URL = os.getenv("ALCHEMY_RPC_URL")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# ===== 2. Kết nối tới mạng Sepolia qua Alchemy =====
print("Đang kết nối tới mạng Sepolia...")
w3 = Web3(Web3.HTTPProvider(RPC_URL))

if w3.is_connected():
    print("Kết nối thành công! Block mới nhất:", w3.eth.block_number)
else:
    print("Kết nối thất bại, kiểm tra lại RPC URL trong file .env")
    exit()

# ===== 3. Load ABI và khởi tạo đối tượng contract =====
with open("contract_abi.json", "r") as f:
    contract_abi = json.load(f)

contract = w3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=contract_abi)

# ===== 4. Lấy địa chỉ ví từ private key =====
account = w3.eth.account.from_key(PRIVATE_KEY)
wallet_address = account.address
print("Địa chỉ ví đang dùng để ghi báo cáo:", wallet_address)

# ===== 5. Kết nối MySQL, lấy các chuỗi nghi ngờ chưa được đẩy lên blockchain =====
print("\nĐang kết nối MySQL...")
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password=DB_PASSWORD,
    database="aml_thesis"
)
cursor = conn.cursor(dictionary=True)

# Lấy 3 chuỗi nghi ngờ dài nhất để demo (giới hạn số lượng vì mỗi lần ghi tốn phí gas thật)
cursor.execute("SELECT id, chain_length, tx_id_list FROM suspicious_chains ORDER BY chain_length DESC LIMIT 3")
chains = cursor.fetchall()

print(f"Tìm được {len(chains)} chuỗi để đẩy lên blockchain.")

# ===== 6. Ghi từng báo cáo lên smart contract =====
nonce = w3.eth.get_transaction_count(wallet_address)

for chain in chains:
    tx_id_list = json.loads(chain["tx_id_list"])
    first_tx_id = tx_id_list[0]  # lấy giao dịch đầu tiên trong chuỗi làm đại diện
    reason = f"Chuoi illicit dai {chain['chain_length']} giao dich lien tiep"

    print(f"\nĐang ghi báo cáo cho txId={first_tx_id}, lý do: {reason}")

    # Xây dựng transaction gọi hàm createReport
    txn = contract.functions.createReport(first_tx_id, reason).build_transaction({
        "chainId": 11155111,  # ID của mạng Sepolia
        "gas": 300000,
        "gasPrice": w3.eth.gas_price,
        "nonce": nonce,
    })

    # Ký giao dịch bằng private key
    signed_txn = w3.eth.account.sign_transaction(txn, private_key=PRIVATE_KEY)

    # Gửi giao dịch lên mạng
    tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
    print(f"Đã gửi giao dịch, hash: {tx_hash.hex()}")

    # Đợi giao dịch được xác nhận
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Xác nhận thành công! Block: {receipt.blockNumber}")

    # Đảm bảo tx_id đã có trong bảng transactions trước (bắt buộc vì có khóa ngoại)
    cursor.execute(
        "INSERT IGNORE INTO transactions (tx_id) VALUES (%s)", (first_tx_id,)
    )

    # Cập nhật vào bảng str_reports trong MySQL
    insert_sql = """INSERT INTO str_reports (tx_id, reason, status, blockchain_tx_hash)
                     VALUES (%s, %s, 'confirmed', %s)"""
    cursor.execute(insert_sql, (first_tx_id, reason, tx_hash.hex()))
    conn.commit()

    nonce += 1  # tăng nonce cho giao dịch tiếp theo

# ===== 7. Kiểm tra tổng số báo cáo hiện có trên blockchain =====
total_reports = contract.functions.getReportCount().call()
print(f"\nHoàn tất! Tổng số báo cáo hiện có trên blockchain: {total_reports}")

cursor.close()
conn.close()