import os
import pandas as pd
import mysql.connector
from werkzeug.security import generate_password_hash

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "port": 3306
}

def init_database():
    print("========== INITIALIZING DATABASE ==========")
    
    # Connect to MySQL Server
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        print("Connected to MySQL server successfully.")
    except mysql.connector.Error as e:
        print(f"Error connecting to MySQL: {e}")
        print("Make sure your custom MySQL process is running on port 3306.")
        return

    # Read and execute schema.sql
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    if os.path.exists(schema_path):
        print(f"Executing schema from {schema_path}...")
        with open(schema_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()
        
        # Split by semicolon to execute queries one by one
        queries = schema_sql.split(";")
        for query in queries:
            query = query.strip()
            if query:
                try:
                    cursor.execute(query)
                except mysql.connector.Error as e:
                    print(f"Error executing query: {e}")
        
        conn.commit()
        print("Database schema loaded successfully.")
    else:
        print("schema.sql not found!")
        return

    # Connect directly to the new database
    cursor.close()
    conn.close()
    
    db_config_with_db = DB_CONFIG.copy()
    db_config_with_db["database"] = "vehicle_intelligence"
    conn = mysql.connector.connect(**db_config_with_db)
    cursor = conn.cursor()

    # Create Default Users if they do not exist
    print("Seeding default users...")
    cursor.execute("SELECT id FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        admin_pass_hash = generate_password_hash("admin123")
        cursor.execute(
            "INSERT INTO users (username, password_hash, email, role) VALUES (%s, %s, %s, %s)",
            ("admin", admin_pass_hash, "admin@vehicleintel.com", "admin")
        )
        print("Admin user seeded (admin / admin123)")

    cursor.execute("SELECT id FROM users WHERE username = 'user'")
    if not cursor.fetchone():
        user_pass_hash = generate_password_hash("user123")
        cursor.execute(
            "INSERT INTO users (username, password_hash, email, role) VALUES (%s, %s, %s, %s)",
            ("user", user_pass_hash, "user@vehicleintel.com", "user")
        )
        print("Standard user seeded (user / user123)")
    conn.commit()

    # Seed Used Cars reference data (dropdowns)
    used_car_clean_path = r"y:\AI_Vehicle_Service_Repair_Insurance_Intelligence\cleaned\used_car_clean.csv"
    if os.path.exists(used_car_clean_path):
        print("Seeding used_car_records reference table...")
        cursor.execute("SELECT COUNT(*) FROM used_car_records")
        count = cursor.fetchone()[0]
        if count == 0:
            df = pd.read_csv(used_car_clean_path)
            # Standardize columns to match SQL schema
            # brand, model, year, age, transmission, fuel_type, owner, km_driven, ask_price
            insert_query = """
                INSERT INTO used_car_records (brand, model, year, age, transmission, fuel_type, owner, km_driven, ask_price)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            data_to_insert = []
            for _, row in df.iterrows():
                data_to_insert.append((
                    str(row.get("Brand", "")),
                    str(row.get("model", "")),
                    int(row.get("Year", 2020)),
                    int(row.get("Age", 0)),
                    str(row.get("Transmission", "")),
                    str(row.get("FuelType", "")),
                    str(row.get("Owner", "")),
                    float(row.get("kmDriven", 0.0)),
                    float(row.get("AskPrice", 0.0))
                ))
            
            # Insert in chunks for efficiency
            chunk_size = 1000
            for i in range(0, len(data_to_insert), chunk_size):
                cursor.executemany(insert_query, data_to_insert[i:i+chunk_size])
            conn.commit()
            print(f"Successfully seeded {len(data_to_insert)} used car records.")
        else:
            print("used_car_records table already seeded.")
    else:
        print(f"used_car_clean.csv not found at {used_car_clean_path}!")

    # Seed Historical Repair data (Dashboard statistics)
    repair_clean_path = r"y:\AI_Vehicle_Service_Repair_Insurance_Intelligence\cleaned\repair_clean.csv"
    if os.path.exists(repair_clean_path):
        print("Seeding repair_records dashboard statistics table...")
        cursor.execute("SELECT COUNT(*) FROM repair_records")
        count = cursor.fetchone()[0]
        if count == 0:
            # We sample 50,000 rows for dashboard stats so that it's fast to query but statistically representative
            print("Reading and sampling repair_clean.csv...")
            df = pd.read_csv(repair_clean_path)
            if len(df) > 50000:
                df_sample = df.sample(50000, random_state=42)
            else:
                df_sample = df
            
            insert_query = """
                INSERT INTO repair_records (vehicle_type, make_model, service_type, parts_used, total_cost,
                                           estimated_cost, service_duration_hours, mileage_at_service,
                                           insurance_claim_used, technician_rating, tow_distance_miles,
                                           urgency_level, customer_type, repair_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            data_to_insert = []
            for _, row in df_sample.iterrows():
                # Format date string safely
                rep_date = str(row.get("Repair Date", "2024-01-01"))
                if len(rep_date) > 10:
                    rep_date = rep_date[:10]
                
                data_to_insert.append((
                    str(row.get("Vehicle Type", "")),
                    str(row.get("Make and Model", "")),
                    str(row.get("Service Type", "")),
                    str(row.get("Parts Used", "")),
                    float(row.get("Total Cost", 0.0)),
                    float(row.get("Estimated Cost", 0.0)),
                    float(row.get("Service Duration Hours", 0.0)),
                    int(row.get("Mileage at Service", 0)),
                    str(row.get("Insurance Claim Used", "No")),
                    float(row.get("Technician Rating", 3.0)),
                    float(row.get("Tow Distance Miles", 0.0)),
                    str(row.get("Urgency Level", "")),
                    str(row.get("Customer Type", "")),
                    rep_date
                ))
            
            # Insert in chunks
            chunk_size = 1000
            for i in range(0, len(data_to_insert), chunk_size):
                cursor.executemany(insert_query, data_to_insert[i:i+chunk_size])
            conn.commit()
            print(f"Successfully seeded {len(data_to_insert)} repair records for analytics.")
        else:
            print("repair_records table already seeded.")
    else:
        print(f"repair_clean.csv not found at {repair_clean_path}!")

    cursor.close()
    conn.close()
    print("========== DATABASE INITIALIZATION COMPLETED ==========")

if __name__ == "__main__":
    init_database()
