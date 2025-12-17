from typing import List
from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
import json
import pandas as pd
import joblib
from feature_engineering import engineer_features

# -----------------------------
# Load model and feature list
# -----------------------------
model = joblib.load("final_model.joblib")

with open("feature_columns.json", "r") as f:
    FEATURE_COLUMNS = json.load(f)

# -----------------------------
# Create FastAPI app
# -----------------------------
app = FastAPI(
    title="Klarna Pay Later Default Model - AOB",
    description="Predicts probability of default for a Pay Later loan",
    version="1.0"
)

# -----------------------------
# Input schema
# -----------------------------
class LoanApplication(BaseModel):
    loan_id: str
    loan_amount: float
    existing_klarna_debt: float
    days_since_first_loan: int
    num_active_loans: int

    new_exposure_7d: float
    new_exposure_14d: float

    num_failed_payments_3m: int
    num_failed_payments_6m: int
    num_failed_payments_1y: int

    num_confirmed_payments_3m: int
    num_confirmed_payments_6m: int

    amount_repaid_3m: float
    amount_repaid_6m: float
    amount_repaid_1y: float

    merchant_group: str
    merchant_category: str
    
# -----------------------------
# Prediction endpoint
# -----------------------------

@app.post("/predict")
def predict_default(application: LoanApplication):

    df = pd.DataFrame([application.dict()])

    loan_id = df.pop("loan_id")[0]

    # Engineer features
    df = engineer_features(df)
    
    # Select model columns
    df = df[FEATURE_COLUMNS]
    
    # Predict probabilities
    pd_default = model.predict_proba(df)[:, 1][0]

    return {"loan_id": loan_id, "probability_of_default": float(pd_default)}


# --- Batch prediction endpoint ---
@app.post("/predict_batch")
def predict_default_batch(applications: List[LoanApplication]):
    # Convert list of Pydantic objects to DataFrame
    df = pd.DataFrame([app.dict() for app in applications])
    
    loan_ids = df.pop("loan_id")

    # Engineer features
    df = engineer_features(df)

    # Select model columns
    df = df[FEATURE_COLUMNS]

    # Predict probabilities
    probabilities = model.predict_proba(df)[:, 1].tolist()

    # Combine loan_ids and predictions
    results = [{"loan_id": lid, "probability_of_default": prob} for lid, prob in zip(loan_ids, probabilities)]

    return {"predictions": results}

@app.post("/predict_csv")
async def predict_csv(file: UploadFile = File(...)):
    # Read CSV into DataFrame
    df = pd.read_csv(file.file)
    
    # Extract loan_id
    loan_ids = df.pop("loan_id")
    
    # Engineer features
    df = engineer_features(df)
    
    # Keep only model columns
    df_model = df[FEATURE_COLUMNS]
    
    # Predict probabilities
    probabilities = model.predict_proba(df_model)[:, 1].tolist()
    
    # Combine loan_ids with predictions
    results = [{"loan_id": lid, "probability_of_default": prob} for lid, prob in zip(loan_ids, probabilities)]
    
    return {"predictions": results}

