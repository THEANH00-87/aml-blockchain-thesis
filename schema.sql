CREATE DATABASE IF NOT EXISTS aml_thesis;
USE aml_thesis;

-- Bảng lưu thông tin giao dịch
CREATE TABLE transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tx_id BIGINT NOT NULL UNIQUE,
    time_step INT,
    out_degree INT DEFAULT 0,
    in_degree INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bảng lưu kết quả AI dự đoán
CREATE TABLE predictions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tx_id BIGINT NOT NULL,
    predicted_label ENUM('licit', 'illicit') NOT NULL,
    confidence_score FLOAT,
    model_version VARCHAR(50) DEFAULT 'random_forest_v1',
    predicted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tx_id) REFERENCES transactions(tx_id)
);

-- Bảng lưu các chuỗi/đường dây nghi ngờ từ phân tích đồ thị
CREATE TABLE suspicious_chains (
    id INT AUTO_INCREMENT PRIMARY KEY,
    chain_length INT NOT NULL,
    tx_id_list TEXT NOT NULL,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bảng báo cáo giao dịch đáng ngờ (STR) - sẽ đồng bộ lên blockchain
CREATE TABLE str_reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tx_id BIGINT NOT NULL,
    reason VARCHAR(255),
    status ENUM('pending', 'reviewed', 'confirmed', 'dismissed') DEFAULT 'pending',
    blockchain_tx_hash VARCHAR(66),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tx_id) REFERENCES transactions(tx_id)
);

-- Bảng tài khoản cán bộ tuân thủ
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin', 'compliance_officer') DEFAULT 'compliance_officer',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);