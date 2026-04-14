import os
import time
import uuid
import logging
import logging.config
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ─────────────────────────────────────────────
# Structured logging — outputs to Render log stream
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("kavach.main")

from services.ai_service import process_case_file
from services.pdf_generator import generate_discharge_pdf

app = FastAPI(title="Discharge Summary Generator API")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_FILE_SIZE_BYTES = 40 * 1024 * 1024  # 40 MB

# ─────────────────────────────────────────────
# Pydantic Schema Models
# ─────────────────────────────────────────────
class PatientDetails(BaseModel):
    patient_name: str = ""
    age_sex: str = ""
    uhid: str = ""
    admission_date: str = ""
    discharge_date: str = ""
    bed_no: str = ""
    consultant: str = ""

class Diagnosis(BaseModel):
    primary: List[str] = []
    associated_conditions: List[str] = []

class Complaint(BaseModel):
    complaint: str = ""
    duration: str = ""

class PastHistory(BaseModel):
    condition: str = ""
    duration: str = ""
    remarks: str = ""

class Allergies(BaseModel):
    known: bool = False
    details: str = ""

class Vitals(BaseModel):
    pulse: str = ""
    bp: str = ""
    temperature: str = ""
    rr: str = ""
    spo2: str = ""

class GeneralExam(BaseModel):
    anaemia: bool = False
    cyanosis: bool = False
    clubbing: bool = False
    jaundice: bool = False
    oedema: bool = False

class SystemicExam(BaseModel):
    cardio: str = ""
    respiratory: str = ""
    gi: str = ""
    cns: str = ""

class ClinicalExam(BaseModel):
    vitals: Vitals
    general: GeneralExam
    systemic: SystemicExam

class Investigation(BaseModel):
    name: str = ""
    finding: str = ""

class ConditionAtDischarge(BaseModel):
    stable: bool = False
    improved: bool = False
    referred: bool = False
    ama: bool = False

class Medication(BaseModel):
    type: str = ""
    generic_name: str = ""
    brand_name: str = ""
    dose: str = ""
    frequency: str = ""
    duration: str = ""
    remarks: str = ""

class FollowUp(BaseModel):
    follow_up_date: str = ""
    reports: List[str] = []
    tests: List[str] = []
    specialty: str = ""
    extracted_doctor: str = ""
    recommended_doctor: str = ""

class StrictDischargeSummary(BaseModel):
    patient_details: PatientDetails
    diagnosis: Diagnosis
    presenting_complaints: List[Complaint] = []
    past_history: List[PastHistory] = []
    allergies: Allergies
    clinical_exam: ClinicalExam
    investigations: List[Investigation] = []
    procedures: str = ""
    hospital_course: str = ""
    condition_at_discharge: ConditionAtDischarge
    medications: List[Medication] = []
    nutrition: List[str] = []
    rehabilitation: str = ""
    follow_up: FollowUp

class DischargeData(BaseModel):
    data: StrictDischargeSummary


# ─────────────────────────────────────────────
# Upload endpoint
# ─────────────────────────────────────────────
@app.post("/upload")
async def upload_case_file(file: UploadFile = File(...)):
    request_id = f"REQ-{uuid.uuid4().hex[:6].upper()}"
    start_time = time.time()

    logger.info(f"[{request_id}] Upload started | filename: {file.filename}")

    if not file.filename.endswith(".pdf"):
        logger.warning(f"[{request_id}] Rejected: not a PDF")
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    file_bytes = await file.read()
    file_size_mb = len(file_bytes) / (1024 * 1024)

    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        logger.warning(f"[{request_id}] Rejected: file too large ({file_size_mb:.1f} MB)")
        raise HTTPException(status_code=400, detail=f"File too large ({file_size_mb:.1f} MB). Maximum allowed size is 40 MB.")

    logger.info(f"[{request_id}] File accepted | size: {file_size_mb:.1f} MB")

    temp_file_path = f"temp_{request_id}_{file.filename}"
    with open(temp_file_path, "wb") as f:
        f.write(file_bytes)

    # ─── Backend retry (2 attempts) ───
    last_error = None
    for attempt in range(1, 3):
        try:
            logger.info(f"[{request_id}] Extraction attempt {attempt}/2")
            extracted_data = process_case_file(temp_file_path, request_id=request_id)
            elapsed = time.time() - start_time
            logger.info(f"[{request_id}] Extraction SUCCESS | attempt: {attempt} | elapsed: {elapsed:.1f}s")
            return {"status": "success", "data": extracted_data}
        except Exception as e:
            last_error = e
            logger.error(f"[{request_id}] Extraction attempt {attempt} FAILED: {e}")
            if attempt < 2:
                logger.info(f"[{request_id}] Waiting 4s before retry...")
                time.sleep(4)

    # ─── Graceful degraded fallback ───
    elapsed = time.time() - start_time
    logger.error(f"[{request_id}] All attempts failed after {elapsed:.1f}s. Returning degraded fallback.")

    # Clean up temp file before returning
    try:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
    except Exception:
        pass

    raise HTTPException(status_code=500, detail="Processing failed. Please try again.")


# ─────────────────────────────────────────────
# PDF generation endpoint
# ─────────────────────────────────────────────
@app.post("/generate-pdf")
async def generate_pdf(data: DischargeData):
    try:
        pdf_path = generate_discharge_pdf(data.data.dict())
        from fastapi.responses import FileResponse
        return FileResponse(pdf_path, media_type="application/pdf", filename="final_discharge_summary.pdf")
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
