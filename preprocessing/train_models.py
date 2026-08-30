import os
import time
import joblib
import numpy as np
import pandas as pd
from xgboost import XGBRegressor, XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix
)

def train_and_save_models():
    print("========== STARTING MODEL TRAINING PIPELINE ==========")
    
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    repair_clean_path = os.path.join(project_root, "cleaned", "repair_clean.csv")
    models_dir = os.path.join(project_root, "models")
    os.makedirs(models_dir, exist_ok=True)
    
    if not os.path.exists(repair_clean_path):
        print(f"Error: {repair_clean_path} not found!")
        return
        
    print("Loading cleaned dataset...")
    df = pd.read_csv(repair_clean_path)
    print(f"Dataset loaded successfully. Shape: {df.shape}")
    
    # 1. Feature Engineering
    print("Performing feature engineering...")
    df["Repair Date"] = pd.to_datetime(df["Repair Date"])
    df["Repair Year"] = df["Repair Date"].dt.year
    df["Repair Month"] = df["Repair Date"].dt.month
    df["Repair Day"] = df["Repair Date"].dt.day
    df["Repair Weekday"] = df["Repair Date"].dt.weekday
    df["Repair Quarter"] = df["Repair Date"].dt.quarter
    
    df["Is Weekend"] = (df["Repair Weekday"] >= 5).astype(int)
    df["Is Towing"] = (df["Towing Date"] != "No Towing").astype(int)
    df["Warranty Valid"] = (df["Is Warranty Valid"] == "Yes").astype(int)
    df["Follow Up"] = (df["Follow-up Needed"] == "Yes").astype(int)
    df["Insurance Used"] = (df["Insurance Claim Used"] == "Yes").astype(int)
    
    # Downsample for training efficiency (e.g., 100,000 rows yields strong generalization in seconds)
    print("Sampling 100,000 rows for model training...")
    df_sample = df.sample(100000, random_state=42).copy()
    
    # ----------------------------------------------------
    # MODEL 1: Repair Cost Prediction (Regressor)
    # ----------------------------------------------------
    print("\n--- Training MODEL 1: Repair Cost Predictor ---")
    
    # Define features
    num_features_cost = [
        "Service Duration Hours",
        "Mileage at Service",
        "Technician Rating",
        "Tow Distance Miles",
        "Estimated Cost",
        "Repair Year",
        "Repair Month",
        "Repair Weekday",
        "Repair Quarter",
        "Is Weekend",
        "Is Towing",
        "Warranty Valid",
        "Follow Up",
        "Insurance Used"
    ]
    
    cat_features_cost = [
        "Vehicle Type",
        "Make and Model",
        "Service Type",
        "Service Description",
        "Parts Used",
        "Payment Method",
        "Warranty Information",
        "Urgency Level",
        "Customer Type"
    ]
    
    X_cost = df_sample[num_features_cost + cat_features_cost]
    y_cost = df_sample["Total Cost"]
    
    X_train_c, X_test_c, y_train_c, y_test_c = train_test_split(
        X_cost, y_cost, test_size=0.2, random_state=42
    )
    
    # Create preprocessing pipeline
    preprocessor_cost = ColumnTransformer(
        transformers=[
            ("num", Pipeline([("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())]), num_features_cost),
            ("cat", Pipeline([("imputer", SimpleImputer(strategy="most_frequent")), ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False))]), cat_features_cost)
        ]
    )
    
    print("Preprocessing cost features...")
    X_train_c_proc = preprocessor_cost.fit_transform(X_train_c)
    X_test_c_proc = preprocessor_cost.transform(X_test_c)
    
    print("Training XGBoost Regressor...")
    cost_model = XGBRegressor(
        n_estimators=150,
        learning_rate=0.08,
        max_depth=6,
        subsample=0.8,
        colsample_bytree=0.8,
        objective="reg:squarederror",
        random_state=42,
        n_jobs=-1
    )
    
    start = time.time()
    cost_model.fit(X_train_c_proc, y_train_c)
    print(f"Model 1 trained in {time.time() - start:.2f} seconds.")
    
    # Evaluation
    y_pred_c = cost_model.predict(X_test_c_proc)
    mae_c = mean_absolute_error(y_test_c, y_pred_c)
    mse_c = mean_squared_error(y_test_c, y_pred_c)
    rmse_c = np.sqrt(mse_c)
    r2_c = r2_score(y_test_c, y_pred_c)
    
    print(f"Cost Model Evaluation:\n  MAE: {mae_c:.4f}\n  RMSE: {rmse_c:.4f}\n  R2 Score: {r2_c:.4f}")
    
    # Save Model and Preprocessor
    joblib.dump(cost_model, os.path.join(models_dir, "repair_cost_model.pkl"))
    joblib.dump(preprocessor_cost, os.path.join(models_dir, "repair_cost_preprocessor.pkl"))
    print("Saved cost model & preprocessor.")
    
    # ----------------------------------------------------
    # MODEL 2: Repair Time Prediction (Regressor)
    # ----------------------------------------------------
    print("\n--- Training MODEL 2: Repair Time Predictor ---")
    
    num_features_time = [
        "Mileage at Service",
        "Technician Rating",
        "Tow Distance Miles",
        "Estimated Cost",
        "Repair Year",
        "Repair Month",
        "Repair Weekday",
        "Repair Quarter",
        "Is Weekend",
        "Is Towing",
        "Warranty Valid",
        "Follow Up",
        "Insurance Used"
    ]
    
    cat_features_time = cat_features_cost.copy()
    
    X_time = df_sample[num_features_time + cat_features_time]
    y_time = df_sample["Service Duration Hours"]
    
    X_train_t, X_test_t, y_train_t, y_test_t = train_test_split(
        X_time, y_time, test_size=0.2, random_state=42
    )
    
    preprocessor_time = ColumnTransformer(
        transformers=[
            ("num", Pipeline([("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())]), num_features_time),
            ("cat", Pipeline([("imputer", SimpleImputer(strategy="most_frequent")), ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False))]), cat_features_time)
        ]
    )
    
    print("Preprocessing time features...")
    X_train_t_proc = preprocessor_time.fit_transform(X_train_t)
    X_test_t_proc = preprocessor_time.transform(X_test_t)
    
    print("Training XGBoost Regressor...")
    time_model = XGBRegressor(
        n_estimators=150,
        learning_rate=0.08,
        max_depth=6,
        subsample=0.8,
        colsample_bytree=0.8,
        objective="reg:squarederror",
        random_state=42,
        n_jobs=-1
    )
    
    start = time.time()
    time_model.fit(X_train_t_proc, y_train_t)
    print(f"Model 2 trained in {time.time() - start:.2f} seconds.")
    
    # Evaluation
    y_pred_t = time_model.predict(X_test_t_proc)
    mae_t = mean_absolute_error(y_test_t, y_pred_t)
    mse_t = mean_squared_error(y_test_t, y_pred_t)
    rmse_t = np.sqrt(mse_t)
    r2_t = r2_score(y_test_t, y_pred_t)
    
    print(f"Time Model Evaluation:\n  MAE: {mae_t:.4f}\n  RMSE: {rmse_t:.4f}\n  R2 Score: {r2_t:.4f}")
    
    joblib.dump(time_model, os.path.join(models_dir, "repair_time_model.pkl"))
    joblib.dump(preprocessor_time, os.path.join(models_dir, "repair_time_preprocessor.pkl"))
    print("Saved time model & preprocessor.")

    # ----------------------------------------------------
    # MODEL 3: Insurance Claim Prediction (Classifier)
    # ----------------------------------------------------
    print("\n--- Training MODEL 3: Insurance Claim Approval Predictor ---")
    
    num_features_ins = [
        "Service Duration Hours",
        "Mileage at Service",
        "Technician Rating",
        "Tow Distance Miles",
        "Estimated Cost",
        "Repair Year",
        "Repair Month",
        "Repair Weekday",
        "Repair Quarter",
        "Is Weekend",
        "Is Towing",
        "Warranty Valid",
        "Follow Up"
    ]
    
    cat_features_ins = cat_features_cost.copy()
    
    X_ins = df_sample[num_features_ins + cat_features_ins]
    y_ins = df_sample["Insurance Used"]
    
    X_train_i, X_test_i, y_train_i, y_test_i = train_test_split(
        X_ins, y_ins, test_size=0.2, random_state=42, stratify=y_ins
    )
    
    preprocessor_ins = ColumnTransformer(
        transformers=[
            ("num", Pipeline([("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())]), num_features_ins),
            ("cat", Pipeline([("imputer", SimpleImputer(strategy="most_frequent")), ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False))]), cat_features_ins)
        ]
    )
    
    print("Preprocessing insurance features...")
    X_train_i_proc = preprocessor_ins.fit_transform(X_train_i)
    X_test_i_proc = preprocessor_ins.transform(X_test_i)
    
    print("Training XGBoost Classifier...")
    ins_model = XGBClassifier(
        n_estimators=150,
        learning_rate=0.08,
        max_depth=6,
        subsample=0.8,
        colsample_bytree=0.8,
        objective="binary:logistic",
        eval_metric="logloss",
        random_state=42,
        n_jobs=-1
    )
    
    start = time.time()
    ins_model.fit(X_train_i_proc, y_train_i)
    print(f"Model 3 trained in {time.time() - start:.2f} seconds.")
    
    # Evaluation
    y_pred_i = ins_model.predict(X_test_i_proc)
    y_prob_i = ins_model.predict_proba(X_test_i_proc)[:, 1]
    
    acc_i = accuracy_score(y_test_i, y_pred_i)
    prec_i = precision_score(y_test_i, y_pred_i, zero_division=0)
    rec_i = recall_score(y_test_i, y_pred_i, zero_division=0)
    f1_i = f1_score(y_test_i, y_pred_i, zero_division=0)
    roc_i = roc_auc_score(y_test_i, y_prob_i)
    
    print(f"Insurance Model Evaluation:\n  Accuracy: {acc_i:.4f}\n  Precision: {prec_i:.4f}\n  Recall: {rec_i:.4f}\n  F1 Score: {f1_i:.4f}\n  ROC-AUC: {roc_i:.4f}")
    
    joblib.dump(ins_model, os.path.join(models_dir, "insurance_claim_model.pkl"))
    joblib.dump(preprocessor_ins, os.path.join(models_dir, "insurance_claim_preprocessor.pkl"))
    print("Saved insurance model & preprocessor.")
    
    print("\n========== ALL MODEL TRAINING COMPLETED SUCCESSFULLY ==========")

if __name__ == "__main__":
    train_and_save_models()
