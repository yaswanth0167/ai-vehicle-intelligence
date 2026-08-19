import os
import csv
import io
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, Response
from backend.db_helper import (
    register_user, authenticate_user, save_prediction, get_user_history, 
    get_all_history, get_car_brands, get_car_models, get_dashboard_stats
)
from backend import models_helper as mh
from fpdf import FPDF

app = Flask(__name__)
app.secret_key = "vehicle_intelligence_secret_key"

# Auto-initialize database tables and default accounts on boot
try:
    from database.init_db import init_database
    init_database()
except Exception as e:
    print(f"Warning: Could not automatically initialize database: {e}")

@app.context_processor
def inject_datetime():
    return {
        "datetime_now_str": datetime.now().strftime("%A, %d %B %Y")
    }

# Ensure templates and static directories are correctly configured
# The workspaces are in Y:/AI_Vehicle_Service_Repair_Insurance_Intelligence/

# Middleware to restrict routes to logged-in users
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

# Middleware to restrict routes to admins
def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("login"))
        if session["user"]["role"] != "admin":
            flash("Unauthorized access. Admin privileges required.", "danger")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return decorated_function

@app.route("/")
def index():
    if "user" in session:
        return redirect(url_for("dashboard"))
    return render_template("login.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if "user" in session:
        return redirect(url_for("dashboard"))
        
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        user = authenticate_user(username, password)
        if user:
            session["user"] = {
                "id": user["id"],
                "username": user["username"],
                "role": user["role"],
                "email": user["email"]
            }
            flash(f"Welcome back, {username}!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid username or password.", "danger")
            
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if "user" in session:
        return redirect(url_for("dashboard"))
        
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        email = request.form.get("email")
        
        if register_user(username, password, email, role="user"):
            flash("Registration successful. Please log in.", "success")
            return redirect(url_for("login"))
        else:
            flash("Username or email already exists.", "danger")
            
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    if session["user"]["role"] == "admin":
        stats = get_dashboard_stats()
    else:
        stats = get_dashboard_stats(user_id=session["user"]["id"])
    return render_template("index.html", stats=stats)

@app.route("/api/models/<brand>")
@login_required
def api_models(brand):
    models = get_car_models(brand)
    return jsonify(models)

@app.route("/predict/vehicle", methods=["GET", "POST"])
@login_required
def predict_vehicle():
    brands = get_car_brands()
    
    if request.method == "POST":
        # Collect form data
        brand = request.form.get("vehicle_brand")
        model = request.form.get("vehicle_model")
        year = int(request.form.get("manufacturing_year", datetime.now().year))
        mileage = float(request.form.get("mileage", 0.0))
        
        data = {
            "vehicle_brand": brand,
            "vehicle_model": model,
            "vehicle_type": request.form.get("vehicle_type"),
            "fuel_type": request.form.get("fuel_type"),
            "transmission": request.form.get("transmission"),
            "manufacturing_year": year,
            "vehicle_age": datetime.now().year - year,
            "mileage": mileage,
            "service_type": request.form.get("service_type"),
            "service_description": request.form.get("service_description"),
            "estimated_cost": float(request.form.get("estimated_cost", 0.0)),
            "parts_used": request.form.get("parts_used"),
            "warranty_information": request.form.get("warranty_information"),
            "customer_type": request.form.get("customer_type"),
            "urgency_level": request.form.get("urgency_level"),
            "technician_rating": float(request.form.get("technician_rating", 3.0)),
            "tow_distance_miles": float(request.form.get("tow_distance_miles", 0.0)),
            "insurance_claim_used": request.form.get("insurance_claim_used", "No"),
            "repair_date": datetime.now().strftime("%Y-%m-%d")
        }
        
        # Run predictions
        predictions = mh.predict_repair_metrics(data)
        
        # Merge predictions back to data dictionary
        data["predicted_cost"] = predictions["predicted_cost"]
        data["predicted_time"] = predictions["predicted_time"]
        data["insurance_claim_approved"] = predictions["insurance_claim_approved"]
        data["insurance_claim_probability"] = predictions["insurance_claim_probability"]
        
        # Save to database
        save_prediction(session["user"]["id"], data)
        flash("Predictions calculated and stored in database successfully!", "success")
        
        return render_template("predict_vehicle.html", brands=brands, result=data)
        
    return render_template("predict_vehicle.html", brands=brands, result=None)

@app.route("/predict/diagnosis", methods=["GET", "POST"])
@login_required
def predict_diagnosis():
    brands = get_car_brands()
    
    if request.method == "POST":
        brand = request.form.get("vehicle_brand")
        model = request.form.get("vehicle_model")
        year = int(request.form.get("manufacturing_year", datetime.now().year))
        
        data = {
            "vehicle_brand": brand,
            "vehicle_model": model,
            "manufacturing_year": year,
            "problem_description": request.form.get("problem_description"),
            "input_severity": request.form.get("severity", "Medium"),
            "ecu_data": request.form.get("ecu_data", "No Fault Codes"),
            "service_history": request.form.get("service_history", "Regular Service")
        }
        
        # Run ML Classification for problem classification, then recommend parts/actions via rules
        diag_result = mh.predict_diagnosis(data)
        
        # Pack everything to save in database as a prediction record
        pred_data = {
            "vehicle_brand": brand,
            "vehicle_model": model,
            "vehicle_type": "Car",
            "fuel_type": "Petrol",
            "transmission": "Manual",
            "manufacturing_year": year,
            "vehicle_age": datetime.now().year - year,
            "mileage": 0,
            "service_type": "Diagnosis",
            "estimated_cost": 0.0,
            "parts_used": diag_result["parts_replace"],
            "urgency_level": "Scheduled",
            "technician_rating": 5.0,
            "predicted_cost": 0.0,
            "predicted_time": 1.0,
            "insurance_claim_approved": 0,
            "insurance_claim_probability": 0.0,
            "diagnosis_problem": diag_result["problem"],
            "diagnosis_severity": diag_result["severity"],
            "diagnosis_recommendation": f"Recommendation: {diag_result['recommendation']} | Recommended Repair: {diag_result['parts_repair']}"
        }
        
        save_prediction(session["user"]["id"], pred_data)
        flash("Diagnosis predicted and stored successfully!", "success")
        
        return render_template("predict_diagnosis.html", brands=brands, result=diag_result, input_data=data)
        
    return render_template("predict_diagnosis.html", brands=brands, result=None)

@app.route("/predict/fraud", methods=["GET", "POST"])
@login_required
def predict_fraud_route():
    brands = get_car_brands()
    
    if request.method == "POST":
        data = {
            "vehicle_brand": request.form.get("vehicle_brand", "Honda"),
            "age": int(request.form.get("age", 35)),
            "driver_rating": int(request.form.get("driver_rating", 3)),
            "deductible": int(request.form.get("deductible", 400)),
            "year": int(request.form.get("year", 1994)),
            "vehicle_age": request.form.get("vehicle_age", "3 years"),
            "policy_holder_age": request.form.get("policy_holder_age", "31 to 35"),
            "claim_week_difference": int(request.form.get("claim_week_difference", 2)),
            "short_policy_accident": int(request.form.get("short_policy_accident", 0)),
            "month": request.form.get("month", "Jan"),
            "day_of_week": request.form.get("day_of_week", "Monday"),
            "accident_area": request.form.get("accident_area", "Urban"),
            "day_of_week_claimed": request.form.get("day_of_week_claimed", "Monday"),
            "month_claimed": request.form.get("month_claimed", "Jan"),
            "sex": request.form.get("sex", "Male"),
            "marital_status": request.form.get("marital_status", "Single"),
            "fault": request.form.get("fault", "Policy Holder"),
            "policy_type": request.form.get("policy_type", "Sedan - Liability"),
            "vehicle_category": request.form.get("vehicle_category", "Sedan"),
            "vehicle_price": request.form.get("vehicle_price", "20000 to 29000"),
            "days_policy_accident": request.form.get("days_policy_accident", "more than 30"),
            "days_policy_claim": request.form.get("days_policy_claim", "more than 30"),
            "past_number_of_claims": request.form.get("past_number_of_claims", "none"),
            "police_report_filed": request.form.get("police_report_filed", "No"),
            "witness_present": request.form.get("witness_present", "No"),
            "agent_type": request.form.get("agent_type", "External"),
            "number_of_suppliments": request.form.get("number_of_suppliments", "none"),
            "address_change_claim": request.form.get("address_change_claim", "no change"),
            "number_of_cars": request.form.get("number_of_cars", "1-2"),
            "base_policy": request.form.get("base_policy", "Liability")
        }
        
        # Run Fraud ML Inference
        fraud_result = mh.predict_fraud(data)
        
        return render_template("predict_fraud.html", brands=brands, result=fraud_result, input_data=data)
        
    return render_template("predict_fraud.html", brands=brands, result=None)

@app.route("/history")
@login_required
def history():
    if session["user"]["role"] == "admin":
        history_list = get_all_history()
    else:
        history_list = get_user_history(session["user"]["id"])
        
    return render_template("history.html", history=history_list)

@app.route("/admin")
@admin_required
def admin_panel():
    stats = get_dashboard_stats()
    history_list = get_all_history()
    return render_template("admin.html", stats=stats, history=history_list)

@app.route("/admin/export/csv")
@admin_required
def export_csv():
    history_list = get_all_history()
    
    # Create CSV in-memory buffer
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Headers
    writer.writerow([
        "ID", "User", "Date", "Brand", "Model", "Vehicle Type", 
        "Estimated Cost", "Predicted Cost ($)", "Predicted Time (hrs)", 
        "Insurance Claims Used", "Diagnosis Problem", "Diagnosis Severity"
    ])
    
    for row in history_list:
        writer.writerow([
            row["id"], row["username"], row["date"], row["vehicle_brand"], row["vehicle_model"], 
            row["vehicle_type"], row["estimated_cost"], row["predicted_cost"], row["predicted_time"], 
            "Approved" if row["insurance_claim_approved"] == 1 else "Denied", 
            row["diagnosis_problem"] or "N/A", row["diagnosis_severity"] or "N/A"
        ])
        
    response = Response(output.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=vehicle_predictions_report.csv"
    return response

@app.route("/admin/export/pdf")
@admin_required
def export_pdf():
    history_list = get_all_history()
    
    # Set up FPDF PDF Report
    class PDF(FPDF):
        def header(self):
            self.set_fill_color(33, 37, 41) # Dark gray header background
            self.rect(0, 0, 210, 40, "F")
            self.set_text_color(255, 255, 255)
            self.set_font("helvetica", "B", 18)
            self.cell(0, 15, "AI VEHICLE INTELLIGENCE SYSTEM", border=0, align="C")
            self.ln(8)
            self.set_font("helvetica", "", 12)
            self.cell(0, 10, "Predictions History & System Audit Log", border=0, align="C")
            self.ln(20)
            
        def footer(self):
            self.set_y(-15)
            self.set_font("helvetica", "I", 8)
            self.set_text_color(128, 128, 128)
            self.cell(0, 10, f"Page {self.page_no()}/{{nb}} | Report generated on {datetime.now().strftime('%Y-%m-%d')}", align="C")

    pdf = PDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_font("helvetica", "", 9)
    pdf.set_text_color(0, 0, 0)
    
    # Table headers
    headers = ["ID", "User", "Vehicle", "Est. Cost", "Pred. Cost", "Duration", "Ins. Status"]
    col_widths = [10, 25, 55, 25, 25, 25, 25]
    
    # Print Table Headers
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("helvetica", "B", 10)
    for i, h in enumerate(headers):
        pdf.cell(col_widths[i], 8, h, border=1, align="C", fill=True)
    pdf.ln()
    
    # Table Rows
    pdf.set_font("helvetica", "", 9)
    for row in history_list:
        pdf.cell(col_widths[0], 8, str(row["id"]), border=1, align="C")
        pdf.cell(col_widths[1], 8, str(row["username"])[:12], border=1, align="C")
        pdf.cell(col_widths[2], 8, f"{row['vehicle_brand']} {row['vehicle_model']}"[:28], border=1)
        pdf.cell(col_widths[3], 8, f"${row['estimated_cost']:.2f}", border=1, align="C")
        pdf.cell(col_widths[4], 8, f"${row['predicted_cost']:.2f}", border=1, align="C")
        pdf.cell(col_widths[5], 8, f"{row['predicted_time']:.1f} hrs", border=1, align="C")
        pdf.cell(col_widths[6], 8, "Approved" if row["insurance_claim_approved"] == 1 else "Denied", border=1, align="C")
        pdf.ln()
        
    # Output PDF
    pdf_bytes = pdf.output()
    
    response = Response(pdf_bytes, mimetype="application/pdf")
    response.headers["Content-Disposition"] = "attachment; filename=vehicle_predictions_report.pdf"
    return response

if __name__ == "__main__":
    app.run(debug=True, port=5000)
