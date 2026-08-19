import os
import joblib
import pandas as pd
import numpy as np
from datetime import datetime

# Directory paths
MODELS_DIR = r"y:\AI_Vehicle_Service_Repair_Insurance_Intelligence\models"

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

    # For Cost model, we need Service Duration Hours. We predict time first!
    # Predict Service Duration Hours
    time_df = pd.DataFrame(raw_df_data)
    time_df["Insurance Used"] = [insurance_used]
    time_proc = time_preprocessor.transform(time_df)
    predicted_time = float(time_model.predict(time_proc)[0])
    # Enforce realistic lower bound
    predicted_time = max(0.5, round(predicted_time, 1))

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
    
    # Construct expected features for dataset 4 preprocessor
    # Columns: ['Car Name', 'Problem Description', 'Severity', 'Diagnosis', 'How to Fix the Problem', 
    #           'Solution Used', 'ECU Data', 'Service History', 'Car_Brand', 'Car_Year', 'Car_Age', 'Diagnosis_Severity']
    car_name = f"{data.get('vehicle_brand', '')} {data.get('vehicle_model', '')}".strip()
    prob_desc = data.get("problem_description", "")
    input_severity = data.get("input_severity", "Medium")
    ecu_data = data.get("ecu_data", "Unknown")
    service_history = data.get("service_history", "None")
    car_year = int(data.get("manufacturing_year", 2018))
    car_age = datetime.now().year - car_year
    
    # Create dataframe for prediction
    raw_diag_data = {
        "Car Name": [car_name],
        "Problem Description": [prob_desc],
        "Severity": [input_severity],
        "Diagnosis": ["Unknown"], # Filled dynamically
        "How to Fix the Problem": ["Unknown"],
        "Solution Used": ["Unknown"],
        "ECU Data": [ecu_data],
        "Service History": [service_history],
        "Car_Brand": [data.get("vehicle_brand", "")],
        "Car_Year": [car_year],
        "Car_Age": [car_age],
        "Diagnosis_Severity": [input_severity]
    }
    
    df_diag = pd.DataFrame(raw_diag_data)
    diag_proc = diag_preprocessor.transform(df_diag)
    
    pred_class_idx = int(diag_model.predict(diag_proc)[0])
    problem = dataset4_classes[pred_class_idx]
    
    # Practical rule-based recommendation mapping based on predicted Problem and symptoms
    recommendations = {
        "Battery": {
            "severity": "High" if "dead" in prob_desc.lower() or "no start" in prob_desc.lower() else "Medium",
            "rec": "Clean battery terminals, check alternator output. If battery voltage is below 12V, replace the battery unit.",
            "parts_replace": "12V Car Battery, Battery Terminals",
            "parts_repair": "Battery Cable connection"
        },
        "Brakes": {
            "severity": "High" if "noise" in prob_desc.lower() or "soft" in prob_desc.lower() else "Medium",
            "rec": "Inspect brake pads for wear. Replace if thickness is below 3mm. Flush brake fluid and bleed brake lines.",
            "parts_replace": "Front/Rear Brake Pads, Brake Rotors, Brake Fluid",
            "parts_repair": "Brake Caliper adjustment"
        },
        "Electrical": {
            "severity": "Medium",
            "rec": "Check passenger cabin fuse box. Trace wire harness for short circuits. Test alternator voltage regulator.",
            "parts_replace": "Fuses, Headlight Bulbs, Wiring Harness segments",
            "parts_repair": "Ground connection repair"
        },
        "Engine": {
            "severity": "High" if "smoke" in prob_desc.lower() or "knocking" in prob_desc.lower() or "overheat" in prob_desc.lower() else "Medium",
            "rec": "Read ECU error codes (ODB-II). Check engine oil level and coolant temperature sensor. Inspect spark plugs.",
            "parts_replace": "Spark Plugs, Engine Coolant, Oil Filter, Air Filter",
            "parts_repair": "Valve cover gasket adjustment"
        },
        "Transmission": {
            "severity": "High" if "slipping" in prob_desc.lower() or "hard shift" in prob_desc.lower() else "Medium",
            "rec": "Check transmission fluid level and color. If fluid smells burnt, flush immediately. Test transmission solenoid valves.",
            "parts_replace": "Transmission Fluid, Shift Solenoid, Transmission Filter",
            "parts_repair": "Clutch linkage adjustment"
        }
    }
    
    rec_info = recommendations.get(problem, {
        "severity": "Medium",
        "rec": "Inspect vehicle components, run diagnostic scan using OBD-II scanner, and check fluid levels.",
        "parts_replace": "General parts depending on check",
        "parts_repair": "Adjust connections and clear codes"
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
