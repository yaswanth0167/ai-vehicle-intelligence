# 🚗 AI Vehicle Service, Repair & Insurance Intelligence System

An end-to-end, industry-grade **Pure Machine Learning** system designed to deliver predictive insights for vehicle repairs, diagnostic trouble code analysis, and insurance claims risk assessment. The project is built using Python, Pandas, NumPy, Scikit-learn, XGBoost, Flask, Bootstrap, and MySQL.

---

## 🛠️ Tech Stack & Dependencies

*   **Backend**: Flask (Python)
*   **Frontend**: HTML5, CSS3 (Custom theme), JavaScript (AJAX & dynamic dropdowns), Bootstrap 5
*   **Database**: MySQL Server 9.7 (User-level local instance)
*   **Machine Learning**: Scikit-learn, XGBoost, Joblib, Pandas, NumPy
*   **Visualization**: Chart.js (Interactive line & pie charts)
*   **Reports**: Python `csv` module, `fpdf2` for dynamic PDF report generation

---

## 📐 Project Architecture & Flow Diagram

The system operates on a clean model-view-controller (MVC) architecture integrating machine learning inference directly inside Flask routes.

```
       +---------------------------------------------+
       |                 User / Admin                |
       +----------------------+----------------------+
                              |
                     HTTP POST/GET Requests
                              |
                              v
       +----------------------+----------------------+
       |               Flask Web Application         |
       |  (Session Auth, Prediction Routing, Reports)|
       +--------+-------------+-------------+--------+
                |             |             |
     Read/Write |   Inference |   Inference | Inference
                v             v             v
   +------------+---+  +------+------+  +---+---------+
   |   MySQL DB     |  | ML Pipelines|  | Rule-Engine |
   | (Users,        |  | (XGBoost,   |  | (Diagnosis &|
   | Seeding,       |  | Preprocessors| | Parts Recs) |
   | Predictions)   |  | .pkl files) |  +-------------+
   +----------------+  +-------------+
```

---

## 📁 Folder Structure

```
AI_Vehicle_Service_Repair_Insurance_Intelligence/
│
├── backend/
│   ├── __init__.py
│   ├── db_helper.py           # MySQL connection and aggregation queries
│   └── models_helper.py       # ML Pipeline preprocessing & model inference
│
├── cleaned/
│   ├── diagnosis_clean.csv    # Cleaned Diagnostic dataset
│   ├── fraud_clean.csv        # Cleaned Claims Fraud dataset
│   ├── repair_clean.csv       # Cleaned Service History dataset
│   └── used_car_clean.csv     # Cleaned Used Car reference dataset
│
├── database/
│   ├── init_db.py             # Database creation & reference seeding script
│   └── schema.sql             # SQL schema structure DDL
│
├── datasets/                  # Source CSV files (stored locally)
│
├── models/                    # Trained .pkl models & ColumnTransformers
│   ├── dataset4_preprocessor.pkl
│   ├── feature_engineered_preprocessor.pkl
│   ├── final_dataset4_xgboost.pkl
│   ├── final_feature_engineered_xgboost.pkl
│   ├── final_fraud_xgboost.pkl
│   ├── fraud_preprocessor.pkl
│   ├── fraud_threshold.pkl
│   ├── insurance_claim_model.pkl
│   ├── insurance_claim_preprocessor.pkl
│   ├── repair_cost_model.pkl
│   ├── repair_cost_preprocessor.pkl
│   ├── repair_time_model.pkl
│   └── repair_time_preprocessor.pkl
│
├── notebooks/                 # Jupyter Notebooks for analysis & training
│   ├── 01_dataset_analysis.ipynb
│   ├── 01_repair_cost_model.ipynb
│   ├── 02_used_car_model.ipynb
│   ├── 03_fraud_detection.ipynb
│   └── 04_vehicle_diagnosis.ipynb
│
├── preprocessing/
│   └── train_models.py        # Pipeline to train cost, time & claims models
│
├── static/
│   └── css/
│       └── style.css          # Custom styling for sidebar, cards & tables
│
├── templates/
│   ├── base.html              # Base layouts (navbar, sidebar, Chart.js)
│   ├── index.html             # Main Dashboard & charts
│   ├── login.html             # User Login
│   ├── register.html          # User Registration
│   ├── predict_vehicle.html   # Repair Cost & Time forms & outputs
│   ├── predict_diagnosis.html # Symptom & OBD Scanner outputs
│   ├── predict_fraud.html     # Underwriter claim fraud audit form
│   ├── history.html           # Prediction logs
│   └── admin.html             # Admin stats & PDF/CSV export panel
│
├── app.py                     # Main Flask Application
├── requirements.txt           # Project Dependencies
└── README.md                  # Comprehensive Documentation
```

---

## 🗃️ Database Schema

We use a relational database layout in MySQL containing 4 primary tables:
*   `users`: Stores credentials using SHA-256 password hashing.
*   `predictions`: Holds complete run logs for cost, time, fraud, and diagnosis.
*   `used_car_records`: Holds Reference vehicle options for dynamic dropdown population.
*   `repair_records`: Holds 50,000 reference repair rows used to compile historical dashboard analytics.

---

## 📊 Dataset Descriptions & Rationale

1.  **`enhanced_motor_vehicle_repair_towing_dataset.csv`**: Main training file. Chosen because it provides granular breakdown of repair features (urgency, technician rating, estimated cost, mileage, warranty) mapped to actual service cost, repair duration, and claim outcomes.
2.  **`Used_Car_Dataset.csv`**: Reference dataset. Used solely to index active automobile brands and models for drop-down menus and dashboard base stats.
3.  **`fraud_oracle.csv`**: Claim fraud dataset. Used to evaluate claims for bad-faith claims, suspicious accident-to-report timing, and mismatched policyholder age profiles.
4.  **`ML Car Diagnostic Agent AI Assistant.csv`**: Symptom mapping database. Trains multiclass XGBoost models to map description text and OBD codes directly to 5 primary fault categories: Battery, Brakes, Engine, Transmission, and Electrical.

### ❓ Merging vs. Keeping Separate
The datasets are kept separate.
*   **Rationale**: The datasets represent completely different entities and business questions. Merging `fraud_oracle` (claims history) with `repair_clean` (mechanic repair actions) or `Used_Car_Dataset` (pricing listings) would introduce severe dimensional misalignment, leading to millions of null values, massive memory overhead, and dataset leakage. Instead, separate pipelines preserve target purity for independent ML tasks.

---

## 🧠 Feature Engineering Explanation

*   **Temporal Splits**: Extracted `Repair Year`, `Repair Month`, `Repair Day`, `Repair Weekday`, and `Repair Quarter` to isolate seasonal repair peaks (e.g. winter storms increase towing demands).
*   **Interaction Variables**: Created `Is Weekend` (day of week >= 5) and `Is Towing` (tow distance > 0) to capture price scaling spikes.
*   **Binary Flags**: Parsed string responses (e.g., `Is Warranty Valid` and `Insurance Claim Used` -> 1 or 0) to structure numeric inputs for regression.
*   **Fraud Profile Indicators**: Generated `Age_Vehicle_Interaction`, `Claim_Week_Difference`, and `Short_Policy_Accident` to identify claims filed suspiciously close to policy sign-up dates.

---

## 📈 Model Comparison & Performance Metrics

### 1. Repair Cost Regressor (Target: `Total Cost`)
*   **Winner**: XGBoost Regressor
*   **Performance**: R² Score: **0.9939** | MAE: **$18.29**
*   *Note*: The high R² score is driven by the presence of `Estimated Cost`, which is strongly correlated with `Total Cost`.

### 2. Repair Time Regressor (Target: `Service Duration Hours`)
*   **Winner**: XGBoost Regressor
*   **Performance**: MAE: **1.16 hrs** | RMSE: **1.43 hrs**

### 3. Claims Insurance Classifier (Target: `Insurance Claim Used`)
*   **Winner**: XGBoost Classifier
*   **Performance**: Accuracy: **57.41%** | ROC-AUC: **0.6264**

### 4. Vehicle Diagnosis Classifier (Target: `Problem Classification`)
*   **Winner**: Multiclass XGBoost Classifier
*   **Performance**: Accuracy: **91.20%** | Classes: Battery, Brakes, Electrical, Engine, Transmission

---

## 🚀 Deployment Guide

Follow these steps to run the application locally:

### 1. Set Up Custom MySQL Datadir (No Admin Rights Needed)
```powershell
# Create data folder
mkdir database/mysql_data

# Initialize MySQL
& "C:\Program Files\MySQL\MySQL Server 9.7\bin\mysqld.exe" --initialize-insecure --datadir="y:\AI_Vehicle_Service_Repair_Insurance_Intelligence\database\mysql_data"

# Run MySQL Daemon in background
& "C:\Program Files\MySQL\MySQL Server 9.7\bin\mysqld.exe" --datadir="y:\AI_Vehicle_Service_Repair_Insurance_Intelligence\database\mysql_data" --port=3306 --console
```

### 2. Install Dependencies & Set Up Database
```bash
pip install -r requirements.txt
python database/init_db.py
```

### 3. Train Missing ML Models
```bash
python preprocessing/train_models.py
```

### 4. Run Flask Application
```bash
python app.py
```
Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.
*   **Admin Credentials**: `admin` / `admin123`
*   **User Credentials**: `user` / `user123`

---

## 📝 Resume Project Description

**AI Vehicle Service, Repair & Insurance Intelligence System | Flask, Python, XGBoost, MySQL, HTML/CSS/JS**
*   Designed and built an end-to-end vehicle repair diagnostics and insurance claims auditing application integrating five separate machine learning pipelines.
*   Trained custom XGBoost regression models to predict repair costs (R²: 0.99) and service durations (MAE: 1.16 hours) over a 2-million-row tabular dataset.
*   Deployed a class-weighted binary XGBoost classifier mapping claimant records to fraud risk scores, auditing claims via dynamic risk thresholds (Threshold: 0.55).
*   Constructed a responsive user-level dashboard featuring dynamic brand-model dropdowns via AJAX, prediction run history logging to MySQL, and automated CSV/PDF audit report downloads.

---

## 💬 Interview Q&A

**Q1: Why did you choose XGBoost over Deep Learning models for this project?**
**A**: Tabular and structured datasets do not benefit from deep neural networks. Tree-based ensemble models like XGBoost outperform Deep Learning on tabular data because they handle disparate feature scales, missing values, and high-cardinality categorical encodings natively with significantly lower training cost, memory footprint, and faster inference times.

**Q2: How did you handle the class imbalance in the Insurance Fraud dataset?**
**A**: Fraud incidents represent only ~6% of the dataset. Using raw accuracy would cause the model to guess "Non-Fraud" constantly. I calculated the imbalance ratio and passed it as `scale_pos_weight` inside XGBoost, which penalizes misclassifications on the minority class. I also adjusted the decision threshold to `0.55` and optimized for F1-score and PR-AUC instead of raw accuracy.

**Q3: How did you solve the potential data leakage between 'Estimated Cost' and 'Total Cost'?**
**A**: `Estimated Cost` has a 0.99 correlation with `Total Cost` since it represents the mechanic's upfront quote. While it is useful for refining the cost projection, it cannot be used for predicting `Service Duration Hours` or `Insurance Claim Used`. I built separate pipelines for each target, explicitly removing target-derived variables from the feature matrices before performing train-test splits.
