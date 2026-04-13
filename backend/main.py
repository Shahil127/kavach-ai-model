import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from services.ai_service import process_case_file
from services.pdf_generator import generate_discharge_pdf

app = FastAPI(title="Discharge Summary Generator API")

# Setup CORS for the Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    generic_name: str = ""
    brand_name: str = ""
    dose: str = ""
    frequency: str = ""
    duration: str = ""
    remarks: str = ""

class FollowUp(BaseModel):
    instructions: List[str] = []
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

@app.post("/upload")
async def upload_case_file(file: UploadFile = File(...)):
    """
    Receives a patient case file PDF, sends it to Gemini along with the template
    to extract structured JSON data.
    """
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
    
    # Save the uploaded file temporarily
    temp_file_path = f"temp_{file.filename}"
    with open(temp_file_path, "wb") as f:
        f.write(await file.read())
        
    try:
        # Template is expected to be in the parent directory as per user description
        template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Discharge_summary.pdf")
        
        if not os.path.exists(template_path):
            raise HTTPException(status_code=500, detail="Template PDF not found.")
            
        # Process the file using the AI service
        extracted_data = process_case_file(temp_file_path, template_path)
        
        return {"status": "success", "data": extracted_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up temporary file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

@app.post("/generate-pdf")
async def generate_pdf(data: DischargeData):
    """
    Takes the structured JSON data (after user review) and generates
    the final formatted discharge summary PDF.
    """
    try:
        # Pydantic models validate and serialize beautifully, 
        # but the PDF generator might just expect a dict.
        # So we pass data.data.dict()
        pdf_path = generate_discharge_pdf(data.data.dict())
        # We can either return the file directly or return a URL to it
        # Returning direct download via FileResponse would be better
        from fastapi.responses import FileResponse
        return FileResponse(pdf_path, media_type="application/pdf", filename="final_discharge_summary.pdf")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
