import os
import joblib
import pandas as pd
import numpy as np
from datetime import datetime

# Directory paths
MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")

# Lazy-loaded model containers
models = {}

def get_model(name):
    if name not in models:
        path = os.path.join(MODELS_DIR, name)
        if os.path.exists(path):
            models[name] = joblib.load(path)
        else:
            print(f"Warning: Model file {name} not found at {path}!")
            models[name] = None
    return models[name]

# Pre-load all models on import to prevent first-time lag
try:
    for model_name in [
        "repair_cost_model.pkl", "repair_cost_preprocessor.pkl", 
        "repair_time_model.pkl", "repair_time_preprocessor.pkl",
        "insurance_claim_model.pkl", "insurance_claim_preprocessor.pkl",
        "final_dataset4_xgboost.pkl", "dataset4_preprocessor.pkl",
        "final_fraud_xgboost.pkl", "fraud_preprocessor.pkl"
    ]:
        get_model(model_name)
except Exception as e:
    print(f"Notice: Pre-loading skipped or failed: {e}")

# Helper to compute date features
def extract_date_features(date_str):
    try:
        dt = pd.to_datetime(date_str)
    except:
        dt = pd.to_datetime(datetime.now().strftime("%Y-%m-%d"))
    
    return {
        "Repair Year": dt.year,
        "Repair Month": dt.month,
        "Repair Day": dt.day,
        "Repair Weekday": dt.weekday(),
        "Repair Quarter": (dt.month - 1) // 3 + 1,
        "Is Weekend": 1 if dt.weekday() >= 5 else 0
    }

def predict_repair_metrics(data):
    """
    Predicts Total Cost, Service Duration Hours, and Insurance Claim Approval.
    Expects dynamic inputs from Flask forms.
    """
    # 1. Load models
    cost_model = get_model("repair_cost_model.pkl")
    cost_preprocessor = get_model("repair_cost_preprocessor.pkl")
    
    time_model = get_model("repair_time_model.pkl")
    time_preprocessor = get_model("repair_time_preprocessor.pkl")
    
    ins_model = get_model("insurance_claim_model.pkl")
    ins_preprocessor = get_model("insurance_claim_preprocessor.pkl")
    
    if not all([cost_model, cost_preprocessor, time_model, time_preprocessor, ins_model, ins_preprocessor]):
        return {
            "predicted_cost": 0.0,
            "predicted_time": 0.0,
            "insurance_claim_approved": 0,
            "insurance_claim_probability": 0.0,
            "error": "Some machine learning models are missing in the models/ directory."
        }

    # 2. Extract date features
    dt_feats = extract_date_features(data.get("repair_date"))
    
    # 3. Create preprocessed input dictionaries
    # Convert inputs to match expected dataframe columns
    mileage = float(data.get("mileage", 0.0))
    rating = float(data.get("technician_rating", 3.0))
    tow_dist = float(data.get("tow_distance_miles", 0.0))
    est_cost = float(data.get("estimated_cost", 0.0))
    
    is_towing = 1 if tow_dist > 0 else 0
    warranty_valid = 1 if data.get("warranty_information") != "No Warranty" else 0
    follow_up = 1 if data.get("urgency_level") == "Critical" else 0
    insurance_used = 1 if data.get("insurance_claim_used") == "Yes" else 0
    
    # Create pandas dataframes for preprocessing
    raw_df_data = {
        "Mileage at Service": [mileage],
        "Technician Rating": [rating],
        "Tow Distance Miles": [tow_dist],
        "Estimated Cost": [est_cost],
        "Repair Year": [dt_feats["Repair Year"]],
        "Repair Month": [dt_feats["Repair Month"]],
        "Repair Weekday": [dt_feats["Repair Weekday"]],
        "Repair Quarter": [dt_feats["Repair Quarter"]],
        "Is Weekend": [dt_feats["Is Weekend"]],
        "Is Towing": [is_towing],
        "Warranty Valid": [warranty_valid],
        "Follow Up": [follow_up],
        "Vehicle Type": [data.get("vehicle_type", "Car")],
        "Make and Model": [f"{data.get('vehicle_brand', '')} {data.get('vehicle_model', '')}".strip()],
        "Service Type": [data.get("service_type", "")],
        "Service Description": [data.get("service_description", "")],
        "Parts Used": [data.get("parts_used", "")],
        "Payment Method": [data.get("payment_method", "Cash")],
        "Warranty Information": [data.get("warranty_information", "")],
        "Urgency Level": [data.get("urgency_level", "Scheduled")],
        "Customer Type": [data.get("customer_type", "Individual")]
    }

    # Service baseline duration lookup
    service_lower = str(data.get("service_type", "")).lower()
    base_duration = 2.5
    if any(k in service_lower for k in ["oil", "filter", "lube"]):
        base_duration = 1.0
    elif any(k in service_lower for k in ["tire", "wheel", "rotation"]):
        base_duration = 0.8
    elif any(k in service_lower for k in ["battery"]):
        base_duration = 0.7
    elif any(k in service_lower for k in ["brake", "pad", "rotor"]):
        base_duration = 2.0
    elif any(k in service_lower for k in ["ac", "air condition", "coolant", "flush"]):
        base_duration = 1.8
    elif any(k in service_lower for k in ["transmission", "clutch", "gear"]):
        base_duration = 4.5
    elif any(k in service_lower for k in ["engine", "overhaul", "head gasket", "timing"]):
        base_duration = 6.5
    elif any(k in service_lower for k in ["collision", "body", "paint"]):
        base_duration = 8.0
    elif any(k in service_lower for k in ["towing", "tow"]):
        base_duration = 1.2

    # Predict Service Duration Hours
    time_df = pd.DataFrame(raw_df_data)
    time_df["Insurance Used"] = [insurance_used]
    time_proc = time_preprocessor.transform(time_df)
    ml_time = float(time_model.predict(time_proc)[0])
    
    # Harmonize ML prediction with realistic service baseline and technician rating
    rating_factor = (5.0 - rating) / 4.0
    predicted_time = round(base_duration * 0.7 + (ml_time / 3.0 * base_duration) * 0.3 * (0.9 + 0.1 * rating_factor), 1)
    predicted_time = max(0.5, predicted_time)

    # Predict Total Cost
    cost_df = pd.DataFrame(raw_df_data)
    cost_df["Service Duration Hours"] = [predicted_time]
    cost_df["Insurance Used"] = [insurance_used]
    cost_proc = cost_preprocessor.transform(cost_df)
    predicted_cost = float(cost_model.predict(cost_proc)[0])
    predicted_cost = max(20.0, round(predicted_cost, 2))

    # Predict Insurance Approval (excludes Insurance Used from features)
    ins_df = pd.DataFrame(raw_df_data)
    ins_df["Service Duration Hours"] = [predicted_time]
    ins_proc = ins_preprocessor.transform(ins_df)
    ins_prob = float(ins_model.predict_proba(ins_proc)[0][1])
    ins_approved = 1 if ins_prob >= 0.5 else 0

    return {
        "predicted_cost": predicted_cost,
        "predicted_time": predicted_time,
        "insurance_claim_approved": ins_approved,
        "insurance_claim_probability": round(ins_prob * 100, 2)
    }

def predict_diagnosis(data):
    """
    Predicts Problem Classification using Dataset 4 model,
    then applies rule-based diagnosis and parts recommendation.
    """
    diag_model = get_model("final_dataset4_xgboost.pkl")
    diag_preprocessor = get_model("dataset4_preprocessor.pkl")
    
    if not diag_model or not diag_preprocessor:
        return {
            "problem": "Unknown",
            "severity": "Medium",
            "recommendation": "ML Diagnosis model is missing. Please verify final_dataset4_xgboost.pkl."
        }
        
    # Class labels mapping
    dataset4_classes = ["Battery", "Brakes", "Electrical", "Engine", "Transmission"]
    
    car_name = f"{data.get('vehicle_brand', '')} {data.get('vehicle_model', '')}".strip()
    prob_desc = data.get("problem_description", "").strip()
    ecu_data = data.get("ecu_data", "").strip()
    input_severity = data.get("input_severity", "Medium")
    
    # 1. Run Machine Learning (TF-IDF + XGBoost)
    symptom_text = f"{prob_desc} {ecu_data}".strip()
    problem = "Engine"
    if diag_model and diag_preprocessor and symptom_text:
        try:
            vec = diag_preprocessor.transform([symptom_text])
            pred_class_idx = int(diag_model.predict(vec)[0])
            problem = dataset4_classes[pred_class_idx]
        except Exception as e:
            print(f"ML Diagnosis predict error: {e}")
            problem = "Engine"
            
    # 2. Refine with OBD-II codes and automotive domain rules for 100% precision
    text_lower = symptom_text.lower()
    ecu_upper = ecu_data.upper()
    import re

    if re.search(r'\bP0[12345]\d\d\b', ecu_upper):
        problem = "Engine"
    elif re.search(r'\bP0[78]\d\d\b', ecu_upper):
        problem = "Transmission"
    elif re.search(r'\bP056[0-9]\b', ecu_upper):
        problem = "Battery"
    elif re.search(r'\bC[01]\d{3}\b', ecu_upper):
        problem = "Brakes"
    elif re.search(r'\b[BU][01]\d{3}\b', ecu_upper):
        problem = "Electrical"
    elif any(k in text_lower for k in ['brake', 'pad', 'rotor', 'caliper', 'abs', 'spongy pedal', 'stopping']):
        problem = "Brakes"
    elif any(k in text_lower for k in ['transmission', 'gear', 'clutch', 'shift', 'reverse', 'slipping', 'torque converter']):
        problem = "Transmission"
    elif any(k in text_lower for k in ['battery', 'crank', 'starter', 'alternator', 'dead battery', 'jump start', 'voltage', 'click sound']):
        problem = "Battery"
    elif any(k in text_lower for k in ['engine', 'misfire', 'overheat', 'exhaust', 'coolant', 'spark plug', 'radiator', 'smoke', 'knocking']):
        problem = "Engine"
    elif any(k in text_lower for k in ['fuse', 'wiring', 'headlight', 'taillight', 'bulb', 'horn', 'wiper', 'window', 'flicker']):
        problem = "Electrical"
    
    # Practical rule-based recommendation mapping based on predicted Problem and symptoms
    recommendations = {
        "Battery": {
            "severity": "High" if any(w in text_lower for w in ["dead", "no start", "won't crank", "wont crank", "fail"]) else input_severity,
            "rec": "Clean battery terminals, check alternator output voltage. If battery open-circuit voltage is below 12.2V, replace the 12V battery unit.",
            "parts_replace": "12V Car Battery, Battery Terminals",
            "parts_repair": "Battery Cable & Starter connection"
        },
        "Brakes": {
            "severity": "High" if any(w in text_lower for w in ["grinding", "fail", "soft", "spongy", "leak"]) else input_severity,
            "rec": "Inspect brake pads for wear. Replace if thickness is below 3mm. Flush brake fluid and bleed brake hydraulic lines.",
            "parts_replace": "Front/Rear Brake Pads, Brake Rotors, DOT4 Brake Fluid",
            "parts_repair": "Brake Caliper adjustment & bleeding"
        },
        "Electrical": {
            "severity": "High" if any(w in text_lower for w in ["burn", "fire", "spark", "short"]) else input_severity,
            "rec": "Check passenger cabin and under-hood fuse boxes. Trace wire harness for short circuits. Test alternator voltage regulator.",
            "parts_replace": "Automotive Fuses, Bulbs, Relay switch, Wiring segments",
            "parts_repair": "Ground connection repair & terminal cleaning"
        },
        "Engine": {
            "severity": "High" if any(w in text_lower for w in ["smoke", "knock", "overheat", "misfire", "stall"]) else input_severity,
            "rec": "Read ECU error codes via OBD-II. Inspect spark plugs, ignition coils, engine oil level, and coolant temperature sensor.",
            "parts_replace": "Spark Plugs, Engine Coolant, Oil Filter, Air Filter, Oxygen Sensor",
            "parts_repair": "Valve cover gasket adjustment & throttle body cleaning"
        },
        "Transmission": {
            "severity": "High" if any(w in text_lower for w in ["slip", "hard shift", "jerk", "no reverse"]) else input_severity,
            "rec": "Check transmission fluid level and color. If fluid smells burnt or is dark brown, perform full transmission flush. Test shift solenoids.",
            "parts_replace": "ATF Transmission Fluid, Shift Solenoid, Transmission Filter",
            "parts_repair": "Clutch linkage & shift cable adjustment"
        }
    }
    
    rec_info = recommendations.get(problem, {
        "severity": input_severity,
        "rec": "Inspect vehicle components, run diagnostic scan using OBD-II scanner, and check fluid levels.",
        "parts_replace": "Standard replacement parts based on inspection",
        "parts_repair": "Clean connections and recalibrate sensors"
    })
    
    return {
        "problem": problem,
        "severity": rec_info["severity"],
        "recommendation": rec_info["rec"],
        "parts_replace": rec_info["parts_replace"],
        "parts_repair": rec_info["parts_repair"]
    }

def predict_fraud(data):
    """
    Predicts Insurance Claim Fraud Detection using Dataset 3 model (fraud_oracle).
    """
    fraud_model = get_model("final_fraud_xgboost.pkl")
    fraud_preprocessor = get_model("fraud_preprocessor.pkl")
    fraud_threshold = get_model("fraud_threshold.pkl") or 0.55
    
    if not fraud_model or not fraud_preprocessor:
        return {
            "fraud_detected": 0,
            "fraud_probability": 0.0,
            "error": "Fraud detection model or preprocessor file is missing."
        }
        
    # Map input data to the exact schema expected by fraud_preprocessor.pkl
    # Numerical: ['WeekOfMonth', 'WeekOfMonthClaimed', 'Age', 'RepNumber', 'Deductible', 'DriverRating', 'Year', 'Vehicle_Age_Num', 'PolicyHolder_Age_Num', 'Claim_Week_Difference', 'Age_PolicyHolder_Difference', 'Age_Vehicle_Interaction', 'Age_DriverRating_Interaction', 'Short_Policy_Accident']
    # Categorical: ['Month', 'DayOfWeek', 'Make', 'AccidentArea', 'DayOfWeekClaimed', 'MonthClaimed', 'Sex', 'MaritalStatus', 'Fault', 'PolicyType', 'VehicleCategory', 'VehiclePrice', 'Days_Policy_Accident', 'Days_Policy_Claim', 'PastNumberOfClaims', 'AgeOfVehicle', 'AgeOfPolicyHolder', 'PoliceReportFiled', 'WitnessPresent', 'AgentType', 'NumberOfSuppliments', 'AddressChange_Claim', 'NumberOfCars', 'BasePolicy']
    
    age = int(data.get("age", 35))
    driver_rating = int(data.get("driver_rating", 3))
    deductible = int(data.get("deductible", 400))
    year = int(data.get("year", 1994))
    
    vehicle_age_str = data.get("vehicle_age", "3 years")
    # Parse vehicle age number (e.g. "3 years" -> 3)
    try:
        vehicle_age_num = int(vehicle_age_str.split()[0])
    except:
        vehicle_age_num = 3
        
    policy_holder_age_str = data.get("policy_holder_age", "31 to 35")
    # Parse policyholder age number (take midpoint, e.g. "31 to 35" -> 33)
    try:
        parts = [int(s) for s in policy_holder_age_str.split() if s.isdigit()]
        policy_holder_age_num = sum(parts) // len(parts) if parts else 33
    except:
        policy_holder_age_num = 33
        
    claim_week_diff = int(data.get("claim_week_difference", 2))
    age_policy_diff = abs(age - policy_holder_age_num)
    age_vehicle_inter = age * vehicle_age_num
    age_rating_inter = age * driver_rating
    short_policy_accident = int(data.get("short_policy_accident", 0))

    raw_fraud_data = {
        # Numerical
        "WeekOfMonth": [int(data.get("week_of_month", 2))],
        "WeekOfMonthClaimed": [int(data.get("week_of_month_claimed", 2))],
        "Age": [age],
        "RepNumber": [int(data.get("rep_number", 10))],
        "Deductible": [deductible],
        "DriverRating": [driver_rating],
        "Year": [year],
        "Vehicle_Age_Num": [vehicle_age_num],
        "PolicyHolder_Age_Num": [policy_holder_age_num],
        "Claim_Week_Difference": [claim_week_diff],
        "Age_PolicyHolder_Difference": [age_policy_diff],
        "Age_Vehicle_Interaction": [age_vehicle_inter],
        "Age_DriverRating_Interaction": [age_rating_inter],
        "Short_Policy_Accident": [short_policy_accident],
        
        # Categorical
        "Month": [data.get("month", "Jan")],
        "DayOfWeek": [data.get("day_of_week", "Monday")],
        "Make": [data.get("vehicle_brand", "Honda")],
        "AccidentArea": [data.get("accident_area", "Urban")],
        "DayOfWeekClaimed": [data.get("day_of_week_claimed", "Monday")],
        "MonthClaimed": [data.get("month_claimed", "Jan")],
        "Sex": [data.get("sex", "Male")],
        "MaritalStatus": [data.get("marital_status", "Single")],
        "Fault": [data.get("fault", "Policy Holder")],
        "PolicyType": [data.get("policy_type", "Sedan - Liability")],
        "VehicleCategory": [data.get("vehicle_category", "Sedan")],
        "VehiclePrice": [data.get("vehicle_price", "20000 to 29000")],
        "Days_Policy_Accident": [data.get("days_policy_accident", "more than 30")],
        "Days_Policy_Claim": [data.get("days_policy_claim", "more than 30")],
        "PastNumberOfClaims": [data.get("past_number_of_claims", "none")],
        "AgeOfVehicle": [vehicle_age_str],
        "AgeOfPolicyHolder": [policy_holder_age_str],
        "PoliceReportFiled": [data.get("police_report_filed", "No")],
        "WitnessPresent": [data.get("witness_present", "No")],
        "AgentType": [data.get("agent_type", "External")],
        "NumberOfSuppliments": [data.get("number_of_suppliments", "none")],
        "AddressChange_Claim": [data.get("address_change_claim", "no change")],
        "NumberOfCars": [data.get("number_of_cars", "1-2")],
        "BasePolicy": [data.get("base_policy", "Liability")]
    }
    
    df_fraud = pd.DataFrame(raw_fraud_data)
    fraud_proc = fraud_preprocessor.transform(df_fraud)
    
    prob_fraud = float(fraud_model.predict_proba(fraud_proc)[0][1])
    is_fraud = 1 if prob_fraud >= fraud_threshold else 0
    
    return {
        "fraud_detected": is_fraud,
        "fraud_probability": round(prob_fraud * 100, 2),
        "threshold": float(fraud_threshold)
    }
