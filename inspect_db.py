import sys
import mysql.connector

def inspect_database():
    print("==================================================")
    print("🚗 AUTOINTEL DATABASE INSPECTOR")
    print("==================================================")
    
    try:
        conn = mysql.connector.connect(
            host="127.0.0.1",
            port=3306,
            user="root",
            password="",
            database="vehicle_intelligence"
        )
        print("✅ Status: Connected to local MySQL successfully (Port: 3306)")
        cursor = conn.cursor(dictionary=True)
        
        # 1. List Tables
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        print("\n📂 Database Tables Found:")
        for t in tables:
            key_name = list(t.keys())[0]
            table_name = t[key_name]
            
            # Get row count for each table
            count_cursor = conn.cursor()
            count_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = count_cursor.fetchone()[0]
            count_cursor.close()
            
            print(f"   ├─ 📄 {table_name} ({row_count} rows)")
            
        # 2. Inspect Users Table
        print("\n👤 Registered User Accounts:")
        cursor.execute("SELECT id, username, email, role, created_at FROM users")
        users = cursor.fetchall()
        print("   " + "-" * 65)
        print("   | ID  | Username | Email               | Role  | Created At          |")
        print("   " + "-" * 65)
        for u in users:
            print(f"   | {u['id']:<3} | {u['username']:<8} | {u['email']:<19} | {u['role']:<5} | {str(u['created_at']):<19} |")
        print("   " + "-" * 65)
        
        # 3. Inspect Predictions Table Structure
        print("\n⚙️ Schema details for 'predictions' Table:")
        cursor.execute("DESCRIBE predictions")
        columns = cursor.fetchall()
        for col in columns:
            print(f"   ├─ Field: {col['Field']:<22} | Type: {col['Type']:<12} | Null: {col['Null']}")
            
        # 4. Show sample prediction record (if any)
        cursor.execute("SELECT id, user_id, vehicle_brand, vehicle_model, service_type, predicted_cost, date FROM predictions LIMIT 1")
        sample = cursor.fetchone()
        if sample:
            print("\n📝 Sample Prediction Record:")
            for k, v in sample.items():
                print(f"   ├─ {k}: {v}")
        else:
            print("\n📝 Predictions Table: Empty (Run some predictions in forms to see records!)")
            
        cursor.close()
        conn.close()
        print("\n==================================================")
        print("💡 Tip: You can also query the database using standard tools.")
        print("==================================================")
        
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        print("Make sure your local MySQL server is running in the background!")

if __name__ == "__main__":
    inspect_database()
