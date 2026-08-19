import os
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# Load database configuration from environment variables with local fallbacks
DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", ""),
    "database": os.environ.get("DB_NAME", "vehicle_intelligence"),
    "port": int(os.environ.get("DB_PORT", 3306))
}

def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

def register_user(username, password, email, role='user'):
    conn = get_db_connection()
    cursor = conn.cursor()
    password_hash = generate_password_hash(password)
    try:
        cursor.execute(
            "INSERT INTO users (username, password_hash, email, role) VALUES (%s, %s, %s, %s)",
            (username, password_hash, email, role)
        )
        conn.commit()
        return True
    except mysql.connector.Error as e:
        print(f"Error registering user: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

def authenticate_user(username, password):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if user and check_password_hash(user["password_hash"], password):
        return user
    return None

def save_prediction(user_id, data):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        INSERT INTO predictions (
            user_id, vehicle_brand, vehicle_model, vehicle_type, fuel_type, transmission, 
            manufacturing_year, vehicle_age, mileage, service_type, estimated_cost, 
            parts_used, urgency_level, technician_rating, predicted_cost, predicted_time, 
            insurance_claim_approved, insurance_claim_probability, 
            diagnosis_problem, diagnosis_severity, diagnosis_recommendation
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
    """
    params = (
        user_id,
        data.get("vehicle_brand"),
        data.get("vehicle_model"),
        data.get("vehicle_type"),
        data.get("fuel_type"),
        data.get("transmission"),
        data.get("manufacturing_year"),
        data.get("vehicle_age"),
        data.get("mileage"),
        data.get("service_type"),
        data.get("estimated_cost"),
        data.get("parts_used"),
        data.get("urgency_level"),
        data.get("technician_rating"),
        data.get("predicted_cost"),
        data.get("predicted_time"),
        data.get("insurance_claim_approved"),
        data.get("insurance_claim_probability"),
        data.get("diagnosis_problem"),
        data.get("diagnosis_severity"),
        data.get("diagnosis_recommendation")
    )
    try:
        cursor.execute(query, params)
        conn.commit()
        return True
    except mysql.connector.Error as e:
        print(f"Error saving prediction: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

def get_user_history(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM predictions WHERE user_id = %s ORDER BY date DESC", (user_id,)
    )
    history = cursor.fetchall()
    cursor.close()
    conn.close()
    return history

def get_all_history():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT p.*, u.username FROM predictions p JOIN users u ON p.user_id = u.id ORDER BY p.date DESC"
    )
    history = cursor.fetchall()
    cursor.close()
    conn.close()
    return history

FALLBACK_BRANDS = ["Maruti", "Hyundai", "Honda", "Toyota", "Ford", "Mahindra", "Tata", "Kia", "BMW", "Audi"]

FALLBACK_MODELS = {
    "Maruti": ["Swift", "Baleno", "Alto", "Dzire", "WagonR"],
    "Hyundai": ["i20", "Creta", "Verna", "Grand i10", "Santro"],
    "Honda": ["City", "Civic", "Amaze", "Jazz", "WR-V"],
    "Toyota": ["Innova", "Fortuner", "Corolla", "Camry", "Yaris"],
    "Ford": ["EcoSport", "Figo", "Endeavour", "Aspire"],
    "Mahindra": ["Thar", "Scorpio", "XUV500", "Bolero"],
    "Tata": ["Nexon", "Harrier", "Safari", "Tiago"],
    "Kia": ["Seltos", "Sonet", "Carnival"],
    "BMW": ["3 Series", "5 Series", "X5", "X3"],
    "Audi": ["A4", "A6", "Q5", "Q3"]
}

def get_car_brands():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT brand FROM used_car_records ORDER BY brand")
        brands = [r[0] for r in cursor.fetchall() if r[0]]
        cursor.close()
        conn.close()
        if brands:
            return brands
    except Exception as e:
        print(f"Error fetching brands, using fallback: {e}")
    return FALLBACK_BRANDS

def get_car_models(brand):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT DISTINCT model FROM used_car_records WHERE brand = %s ORDER BY model", (brand,)
        )
        models = [r[0] for r in cursor.fetchall() if r[0]]
        cursor.close()
        conn.close()
        if models:
            return models
    except Exception as e:
        print(f"Error fetching models for {brand}, using fallback: {e}")
    return FALLBACK_MODELS.get(brand, ["Standard Sedan", "Standard SUV"])

def get_dashboard_stats(user_id=None):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    stats = {}
    
    if user_id:
        # User-specific statistics (only their own predictions)
        # 1. Total predictions
        cursor.execute("SELECT COUNT(*) as count FROM predictions WHERE user_id = %s", (user_id,))
        stats["total_predictions"] = cursor.fetchone()["count"]
        
        # 2. Avg Repair Cost
        cursor.execute("SELECT AVG(predicted_cost) as avg_cost FROM predictions WHERE user_id = %s", (user_id,))
        stats["avg_repair_cost"] = round(cursor.fetchone()["avg_cost"] or 0, 2)
        
        # 3. Avg Repair Time
        cursor.execute("SELECT AVG(predicted_time) as avg_time FROM predictions WHERE user_id = %s", (user_id,))
        stats["avg_repair_time"] = round(cursor.fetchone()["avg_time"] or 0, 2)
        
        # 4. Insurance Approval %
        cursor.execute("SELECT COUNT(*) as count FROM predictions WHERE user_id = %s AND insurance_claim_approved = 1", (user_id,))
        ins_approved = cursor.fetchone()["count"]
        stats["insurance_approval_percentage"] = round((ins_approved / stats["total_predictions"]) * 100, 2) if stats["total_predictions"] > 0 else 0
        
        # 5. Common problems
        cursor.execute("""
            SELECT diagnosis_problem as problem, COUNT(*) as count 
            FROM predictions 
            WHERE user_id = %s AND diagnosis_problem IS NOT NULL AND diagnosis_problem != '' 
            GROUP BY diagnosis_problem 
            ORDER BY count DESC 
            LIMIT 5
        """, (user_id,))
        stats["common_problems"] = cursor.fetchall()
        if not stats["common_problems"]:
            stats["common_problems"] = [{"problem": "No Diagnostics Recorded Yet", "count": 0}]
            
        # 6. Service Type Stats
        cursor.execute("""
            SELECT service_type, COUNT(*) as count, AVG(predicted_cost) as avg_cost 
            FROM predictions 
            WHERE user_id = %s
            GROUP BY service_type 
            ORDER BY count DESC 
            LIMIT 6
        """, (user_id,))
        stats["service_type_stats"] = cursor.fetchall()
        if not stats["service_type_stats"]:
            stats["service_type_stats"] = [{"service_type": "No Data", "count": 1, "avg_cost": 0}]
            
        # 7. Monthly Reports
        cursor.execute("""
            SELECT DATE_FORMAT(date, '%Y-%m') as month, COUNT(*) as count, SUM(predicted_cost) as total_cost 
            FROM predictions 
            WHERE user_id = %s
            GROUP BY month 
            ORDER BY month DESC 
            LIMIT 12
        """, (user_id,))
        stats["monthly_reports"] = sorted(cursor.fetchall(), key=lambda x: x["month"])
        if not stats["monthly_reports"]:
            stats["monthly_reports"] = [{"month": datetime.now().strftime("%Y-%m"), "total_cost": 0}]
            
    else:
        # Global Admin statistics (global repair records + all user predictions)
        # 1. Total Predictions & Repairs
        cursor.execute("SELECT COUNT(*) as count FROM predictions")
        pred_count = cursor.fetchone()["count"]
        cursor.execute("SELECT COUNT(*) as count FROM repair_records")
        repair_count = cursor.fetchone()["count"]
        stats["total_predictions"] = pred_count + repair_count
        
        # 2. Average Repair Cost
        cursor.execute("SELECT AVG(total_cost) as avg_cost FROM repair_records")
        avg_rep_cost = cursor.fetchone()["avg_cost"] or 0
        cursor.execute("SELECT AVG(predicted_cost) as avg_cost FROM predictions")
        avg_pred_cost = cursor.fetchone()["avg_cost"] or 0
        stats["avg_repair_cost"] = round((avg_rep_cost + avg_pred_cost) / (2 if avg_rep_cost and avg_pred_cost else 1), 2)
        
        # 3. Average Repair Time
        cursor.execute("SELECT AVG(service_duration_hours) as avg_time FROM repair_records")
        avg_rep_time = cursor.fetchone()["avg_time"] or 0
        cursor.execute("SELECT AVG(predicted_time) as avg_time FROM predictions")
        avg_pred_time = cursor.fetchone()["avg_time"] or 0
        stats["avg_repair_time"] = round((avg_rep_time + avg_pred_time) / (2 if avg_rep_time and avg_pred_time else 1), 2)
        
        # 4. Insurance Approval Percentage
        cursor.execute("SELECT COUNT(*) as count FROM repair_records WHERE insurance_claim_used = 'Yes'")
        rep_ins_count = cursor.fetchone()["count"]
        cursor.execute("SELECT COUNT(*) as count FROM predictions WHERE insurance_claim_approved = 1")
        pred_ins_count = cursor.fetchone()["count"]
        total_ins_approved = rep_ins_count + pred_ins_count
        stats["insurance_approval_percentage"] = round((total_ins_approved / stats["total_predictions"]) * 100, 2) if stats["total_predictions"] > 0 else 0
        
        # 5. Most Common Problems
        cursor.execute("""
            SELECT diagnosis_problem as problem, COUNT(*) as count 
            FROM predictions 
            WHERE diagnosis_problem IS NOT NULL AND diagnosis_problem != '' 
            GROUP BY diagnosis_problem 
            ORDER BY count DESC 
            LIMIT 5
        """)
        stats["common_problems"] = cursor.fetchall()
        if not stats["common_problems"]:
            cursor.execute("""
                SELECT service_type as problem, COUNT(*) as count 
                FROM repair_records 
                GROUP BY service_type 
                ORDER BY count DESC 
                LIMIT 5
            """)
            stats["common_problems"] = cursor.fetchall()
            
        # 6. Service Type Statistics
        cursor.execute("""
            SELECT service_type, COUNT(*) as count, AVG(total_cost) as avg_cost 
            FROM repair_records 
            GROUP BY service_type 
            ORDER BY count DESC 
            LIMIT 6
        """)
        stats["service_type_stats"] = cursor.fetchall()
        
        # 7. Monthly Cost Reports
        cursor.execute("""
            SELECT DATE_FORMAT(repair_date, '%Y-%m') as month, COUNT(*) as count, SUM(total_cost) as total_cost 
            FROM repair_records 
            WHERE repair_date IS NOT NULL
            GROUP BY month 
            ORDER BY month DESC 
            LIMIT 12
        """)
        stats["monthly_reports"] = sorted(cursor.fetchall(), key=lambda x: x["month"])
        
    cursor.close()
    conn.close()
    return stats
