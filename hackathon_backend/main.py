from datetime import date

import mysql.connector
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


app = FastAPI(
    title="ClaimSure AI",
    description="Intelligent Motor Insurance Claims and Fraud Detection Platform",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="claimssure_ai",
    )


# ------------------------------
# Request models
# ------------------------------

class ClaimCreate(BaseModel):
    claimant_name: str = Field(min_length=2, max_length=100)
    policy_number: str = Field(min_length=3, max_length=50)
    vehicle_registration: str = Field(min_length=3, max_length=20)
    accident_date: date
    claim_amount: float = Field(gt=0)
    accident_description: str = Field(min_length=10, max_length=2000)


class ClaimStatusUpdate(BaseModel):
    status: str = Field(min_length=1, max_length=30)


# ------------------------------
# Home and health
# ------------------------------

@app.get("/")
def home():
    return {
        "project": "ClaimSure AI",
        "message": "Motor insurance claims backend is running",
        "version": "1.0.0",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "ClaimSure AI Backend",
    }


# ------------------------------
# Submit an insurance claim
# POST /claims
# ------------------------------

@app.post("/claims")
def create_claim(claim: ClaimCreate):
    if claim.accident_date > date.today():
        raise HTTPException(
            status_code=400,
            detail="Accident date cannot be in the future",
        )

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                ph.policyholder_id,
                v.vehicle_id,
                p.policy_id
            FROM policies p
            JOIN vehicles v
                ON v.policy_id = p.policy_id
            JOIN policyholders ph
                ON ph.policyholder_id = v.policyholder_id
            WHERE p.policy_number = %s
              AND v.vehicle_number = %s
            """,
            (claim.policy_number, claim.vehicle_registration),
        )

        record = cursor.fetchone()

        if record is None:
            raise HTTPException(
                status_code=404,
                detail="Policy number and vehicle registration do not match",
            )

        cursor.execute(
            """
            INSERT INTO claims (
                policyholder_id,
                vehicle_id,
                policy_id,
                accident_date,
                accident_description,
                claim_amount,
                claim_status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                record["policyholder_id"],
                record["vehicle_id"],
                record["policy_id"],
                claim.accident_date,
                claim.accident_description,
                claim.claim_amount,
                "Registered",
            ),
        )

        new_claim_id = cursor.lastrowid
        conn.commit()

        return {
            "message": "Claim submitted successfully to MySQL",
            "claim": {
                "claim_id": new_claim_id,
                "claimant_name": claim.claimant_name,
                "policy_number": claim.policy_number,
                "vehicle_registration": claim.vehicle_registration,
                "accident_date": str(claim.accident_date),
                "claim_amount": claim.claim_amount,
                "accident_description": claim.accident_description,
                "status": "Registered",
            },
        }

    except mysql.connector.Error as err:
        if conn is not None:
            conn.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {err}",
        )

    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


# ------------------------------
# Retrieve all claims
# GET /claims
# ------------------------------

@app.get("/claims")
def get_all_claims():
    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT *
            FROM claims
            ORDER BY claim_id DESC
            """
        )
        all_claims = cursor.fetchall()

        return {
            "total_claims": len(all_claims),
            "claims": all_claims,
        }

    except mysql.connector.Error as err:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {err}",
        )

    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


# ------------------------------
# Retrieve one claim
# GET /claims/{claim_id}
# ------------------------------

@app.get("/claims/{claim_id}")
def get_claim(claim_id: int):
    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM claims WHERE claim_id = %s",
            (claim_id,),
        )
        claim = cursor.fetchone()

        if claim is None:
            raise HTTPException(
                status_code=404,
                detail="Claim not found",
            )

        return claim

    except mysql.connector.Error as err:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {err}",
        )

    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


# ------------------------------
# Demo risk assessment
# This is not a real fraud detector.
# POST /claims/{claim_id}/risk-assessment
# ------------------------------

@app.post("/claims/{claim_id}/risk-assessment")
def assess_claim_risk(claim_id: int):
    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT claim_id, accident_description, claim_amount
            FROM claims
            WHERE claim_id = %s
            """,
            (claim_id,),
        )
        claim = cursor.fetchone()

        if claim is None:
            raise HTTPException(
                status_code=404,
                detail="Claim not found",
            )

        flags = []
        description = (claim["accident_description"] or "").lower()

        if float(claim["claim_amount"]) >= 500000:
            flags.append("High claim amount requires review")

        if len(description) < 30:
            flags.append("Limited accident description")

        score = min(len(flags) * 30, 60)

        return {
            "claim_id": claim_id,
            "demo_risk_score": score,
            "review_required": len(flags) > 0,
            "flags": flags,
            "model_status": "DEMO_RULES_NOT_PRODUCTION_ML",
            "message": (
                "This preliminary demo result does not prove fraud "
                "or determine claim eligibility. Human review is required."
            ),
        }

    except mysql.connector.Error as err:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {err}",
        )

    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


# ------------------------------
# Demo claim summary
# This is a template, not real GenAI.
# POST /claims/{claim_id}/ai-summary
# ------------------------------

@app.post("/claims/{claim_id}/ai-summary")
def generate_ai_summary(claim_id: int):
    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT c.claim_id, v.vehicle_number, c.claim_amount
            FROM claims c
            JOIN vehicles v ON c.vehicle_id = v.vehicle_id
            WHERE c.claim_id = %s
            """,
            (claim_id,),
        )
        claim = cursor.fetchone()

        if claim is None:
            raise HTTPException(
                status_code=404,
                detail="Claim not found",
            )

        summary = (
            f"Claim {claim['claim_id']} was submitted for vehicle "
            f"{claim['vehicle_number']}. "
            f"The reported claim amount is {claim['claim_amount']}. "
            "A reviewer should verify the submitted information."
        )

        return {
            "claim_id": claim["claim_id"],
            "summary": summary,
            "ai_status": "PLACEHOLDER_NOT_GENAI",
            "message": (
                "This is a demo summary, not a real AI assessment. "
                "Human review is required."
            ),
        }

    except mysql.connector.Error as err:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {err}",
        )

    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


# ------------------------------
# Update claim status in MySQL
# POST /claims/{claim_id}/status
# ------------------------------

@app.post("/claims/{claim_id}/status")
def update_claim_status(claim_id: int, update: ClaimStatusUpdate):
    # These values should match the allowed values in your database.
    allowed_statuses = {
        "Registered",
        "Under Review",
        "Approved",
        "Rejected",
        "Settled",
        "Survey Assigned",
    }

    requested_status = update.status.strip()
    matching_status = next(
        (status for status in allowed_statuses
         if status.casefold() == requested_status.casefold()),
        None,
    )

    if matching_status is None:
        raise HTTPException(
            status_code=400,
            detail=f"Status must be one of: {sorted(allowed_statuses)}",
        )

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT claim_id FROM claims WHERE claim_id = %s",
            (claim_id,),
        )
        existing_claim = cursor.fetchone()

        if existing_claim is None:
            raise HTTPException(
                status_code=404,
                detail="Claim not found",
            )

        cursor.execute(
            "UPDATE claims SET claim_status = %s WHERE claim_id = %s",
            (matching_status, claim_id),
        )
        conn.commit()

        return {
            "message": "Claim status updated successfully in MySQL",
            "claim_id": claim_id,
            "status": matching_status,
        }

    except mysql.connector.Error as err:
        if conn is not None:
            conn.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {err}",
        )

    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()
