CREATE DATABASE IF NOT EXISTS vehicle_intelligence;
USE vehicle_intelligence;

-- Users Table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    role VARCHAR(20) DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Predictions History Table
CREATE TABLE IF NOT EXISTS predictions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    vehicle_brand VARCHAR(50) NOT NULL,
    vehicle_model VARCHAR(50) NOT NULL,
    vehicle_type VARCHAR(50) NOT NULL,
    fuel_type VARCHAR(20) NOT NULL,
    transmission VARCHAR(20) NOT NULL,
    manufacturing_year INT NOT NULL,
    vehicle_age INT NOT NULL,
    mileage INT NOT NULL,
    service_type VARCHAR(100) NOT NULL,
    estimated_cost FLOAT NOT NULL,
    parts_used VARCHAR(255) NOT NULL,
    urgency_level VARCHAR(20) NOT NULL,
    technician_rating FLOAT NOT NULL,
    predicted_cost FLOAT NOT NULL,
    predicted_time FLOAT NOT NULL,
    insurance_claim_approved TINYINT(1) NOT NULL,
    insurance_claim_probability FLOAT NOT NULL,
    diagnosis_problem VARCHAR(100) DEFAULT NULL,
    diagnosis_severity VARCHAR(20) DEFAULT NULL,
    diagnosis_recommendation TEXT DEFAULT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Historical Repair Records Table for Admin Dashboard
CREATE TABLE IF NOT EXISTS repair_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    vehicle_type VARCHAR(50),
    make_model VARCHAR(100),
    service_type VARCHAR(100),
    parts_used VARCHAR(255),
    total_cost FLOAT,
    estimated_cost FLOAT,
    service_duration_hours FLOAT,
    mileage_at_service INT,
    insurance_claim_used VARCHAR(5),
    technician_rating FLOAT,
    tow_distance_miles FLOAT,
    urgency_level VARCHAR(50),
    customer_type VARCHAR(50),
    repair_date DATE
);

-- Used Car Reference Table for dynamic UI dropdowns and stats
CREATE TABLE IF NOT EXISTS used_car_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    brand VARCHAR(50),
    model VARCHAR(50),
    year INT,
    age INT,
    transmission VARCHAR(20),
    fuel_type VARCHAR(20),
    owner VARCHAR(20),
    km_driven FLOAT,
    ask_price FLOAT
);
