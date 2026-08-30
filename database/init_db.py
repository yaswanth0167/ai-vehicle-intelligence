import os
import pandas as pd
import mysql.connector
from werkzeug.security import generate_password_hash
from backend.db_helper import DB_CONFIG

def init_database():
    print("========== INITIALIZING DATABASE ==========")
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 1. Connect without selecting database to try creating the database locally
    db_config_no_db = DB_CONFIG.copy()
    db_config_no_db.pop("database", None)
    
    try:
        conn = mysql.connector.connect(**db_config_no_db)
        cursor = conn.cursor()
        # Try to create local database if we are running locally (will fail on online cloud DBs, which is fine)
        try:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']}")
            print(f"Verified database '{DB_CONFIG['database']}' exists.")
        except mysql.connector.Error:
            pass
        cursor.close()
        conn.close()
    except mysql.connector.Error as e:
        print(f"Notice (connecting without db name): {e}")

    # 2. Connect directly to target database
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        print("Connected to target MySQL database successfully.")
    except mysql.connector.Error as e:
        print(f"Error connecting to MySQL: {e}")
        print("Make sure your database server is running and configured correctly.")
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
                # Skip CREATE DATABASE or USE statements to prevent errors on hosted databases
                if query.upper().startswith("CREATE DATABASE") or query.upper().startswith("USE "):
                    continue
                try:
                    cursor.execute(query)
                except mysql.connector.Error as e:
                    print(f"Error executing query: {e}")
        
        conn.commit()
        print("Database schema loaded successfully.")
    else:
        print("schema.sql not found!")
        return

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
    used_car_clean_path = os.path.join(project_root, "cleaned", "used_car_clean.csv")
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
        print(f"used_car_clean.csv not found at {used_car_clean_path}. Seeding fallback used car records...")
        cursor.execute("SELECT COUNT(*) FROM used_car_records")
        count = cursor.fetchone()[0]
        if count == 0:
            import random
            fallback_brands = ["Maruti", "Hyundai", "Honda", "Toyota", "Ford", "Mahindra", "Tata", "Kia", "BMW", "Audi"]
            fallback_models = {
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
            transmissions = ["Manual", "Automatic"]
            fuel_types = ["Petrol", "Diesel", "CNG"]
            owners = ["First", "Second", "Third"]
            
            insert_query = """
                INSERT INTO used_car_records (brand, model, year, age, transmission, fuel_type, owner, km_driven, ask_price)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            data_to_insert = []
            for _ in range(200):
                brand = random.choice(fallback_brands)
                model = random.choice(fallback_models[brand])
                year = random.randint(2012, 2023)
                age = 2026 - year
                transmission = random.choice(transmissions)
                fuel_type = random.choice(fuel_types)
                owner = random.choice(owners)
                km_driven = random.randint(5000, 150000)
                ask_price = random.randint(200000, 2500000)
                data_to_insert.append((brand, model, year, age, transmission, fuel_type, owner, km_driven, ask_price))
            
            cursor.executemany(insert_query, data_to_insert)
            conn.commit()
            print("Successfully seeded 200 mock used car records.")

    # Seed Historical Repair data (Dashboard statistics)
    repair_clean_path = os.path.join(project_root, "cleaned", "repair_clean.csv")
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
        print(f"repair_clean.csv not found at {repair_clean_path}. Seeding fallback repair records...")
        cursor.execute("SELECT COUNT(*) FROM repair_records")
        count = cursor.fetchone()[0]
        if count == 0:
            import random
            from datetime import timedelta
            vehicle_types = ["Car", "SUV", "Truck", "Van"]
            makes_models = ["Hyundai i20", "Maruti Swift", "Honda City", "Toyota Innova", "Ford EcoSport", "Tata Nexon"]
            service_types = ["Oil Change", "Brake Pad Replacement", "Transmission Repair", "Engine Diagnostics", "Tire Rotation", "AC Service"]
            parts = {
                "Oil Change": "Synthetic Oil, Oil Filter",
                "Brake Pad Replacement": "Brake Pads, Rotor Shims",
                "Transmission Repair": "Transmission Solenoid, Fluid",
                "Engine Diagnostics": "Oxygen Sensor, Spark Plugs",
                "Tire Rotation": "Wheel Weights",
                "AC Service": "Refrigerant Gas, Cabin Filter"
            }
            urgencies = ["Low", "Medium", "High", "Critical"]
            customer_types = ["Individual", "Corporate"]
            
            insert_query = """
                INSERT INTO repair_records (vehicle_type, make_model, service_type, parts_used, total_cost,
                                           estimated_cost, service_duration_hours, mileage_at_service,
                                           insurance_claim_used, technician_rating, tow_distance_miles,
                                           urgency_level, customer_type, repair_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            data_to_insert = []
            start_date = datetime(2025, 1, 1)
            for i in range(300):
                v_type = random.choice(vehicle_types)
                model = random.choice(makes_models)
                service = random.choice(service_types)
                part = parts[service]
                est_cost = random.randint(100, 2500)
                tot_cost = est_cost + random.randint(-50, 150)
                duration = round(random.uniform(1.0, 8.0), 1)
                mileage = random.randint(10000, 120000)
                ins = random.choice(["Yes", "No"])
                rating = round(random.uniform(3.0, 5.0), 1)
                tow = round(random.uniform(0.0, 25.0), 1) if random.random() > 0.8 else 0.0
                urgency = random.choice(urgencies)
                cust_type = random.choice(customer_types)
                rep_date = (start_date + timedelta(days=random.randint(0, 500))).strftime("%Y-%m-%d")
                data_to_insert.append((v_type, model, service, part, tot_cost, est_cost, duration, mileage, ins, rating, tow, urgency, cust_type, rep_date))
                
            cursor.executemany(insert_query, data_to_insert)
            conn.commit()
            print("Successfully seeded 300 mock repair records.")

    cursor.close()
    conn.close()
    print("========== DATABASE INITIALIZATION COMPLETED ==========")

if __name__ == "__main__":
    init_database()
