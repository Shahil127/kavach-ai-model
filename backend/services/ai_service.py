import os
import json
import time
import google.generativeai as genai


def process_case_file(case_pdf_path: str, template_pdf_path: str = None) -> dict:
    """
    Production-safe extraction:
    - NO template leakage
    - NO hallucination
    - STRICT extraction only
    """

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash')

    print(f"Uploading case file {case_pdf_path}...")
    case_file_obj = genai.upload_file(case_pdf_path, mime_type="application/pdf")

    # Wait until ready
    while True:
        file_info = genai.get_file(case_file_obj.name)
        if file_info.state.name == "ACTIVE":
            break
        elif file_info.state.name == "FAILED":
            raise ValueError("File upload failed")
        time.sleep(2)

    # 🔥 FINAL CLEAN PROMPT
    prompt = """
    You are a STRICT medical data extraction system.

    -------------------------------------
    RULE 1: CASE FILE ONLY
    -------------------------------------
    Extract ONLY from the given document.
    DO NOT use any prior knowledge.

    -------------------------------------
    RULE 2: NO GUESSING
    -------------------------------------
    If data not present:
    - use "" for text
    - use [] for lists
    - use false for boolean

    -------------------------------------
    RULE 3: NO DEFAULT MEDICAL PATTERNS
    -------------------------------------
    DO NOT write:
    - coronary angiography
    - PTCA
    - aspirin combinations
    unless explicitly present

    -------------------------------------
    RULE 4: PROCEDURES
    -------------------------------------
    Extract ONLY if clearly mentioned
    else return ""

    -------------------------------------
    RULE 5: MEDICATIONS
    -------------------------------------
    Extract ONLY if present
    else return structured empty object:

    [
      {
        "generic_name": "",
        "brand_name": "",
        "dose": "",
        "frequency": "",
        "duration": "",
        "remarks": ""
      }
    ]

    -------------------------------------
    RULE 6: COURSE / PROCEDURAL NOTE
    -------------------------------------
    Only use facts from document
    NO generic sentences

    -------------------------------------
    RULE 7: DOCTOR
    -------------------------------------
    Extract ONLY if present
    else ""

    -------------------------------------
    RULE 8: OUTPUT
    -------------------------------------
    RETURN STRICT JSON ONLY

    EXPECTED JSON SCHEMA FORMAT:
    {
      "patient_details": {
        "patient_name": "",
        "age_sex": "",
        "uhid": "",
        "admission_date": "",
        "discharge_date": "",
        "bed_no": "",
        "consultant": ""
      },
      "diagnosis": {
        "primary": [],
        "associated_conditions": []
      },
      "presenting_complaints": [
        { "complaint": "", "duration": "" }
      ],
      "past_history": [
        { "condition": "", "duration": "", "remarks": "" }
      ],
      "allergies": {
        "known": false,
        "details": ""
      },
      "clinical_exam": {
        "vitals": {
          "pulse": "",
          "bp": "",
          "temperature": "",
          "rr": "",
          "spo2": ""
        },
        "general": {
          "anaemia": false,
          "cyanosis": false,
          "clubbing": false,
          "jaundice": false,
          "oedema": false
        },
        "systemic": {
          "cardio": "",
          "respiratory": "",
          "gi": "",
          "cns": ""
        }
      },
      "investigations": [
        { "name": "", "finding": "" }
      ],
      "procedures": "",
      "hospital_course": "",
      "condition_at_discharge": {
        "stable": false,
        "improved": false,
        "referred": false,
        "ama": false
      },
      "medications": [
        {
          "generic_name": "",
          "brand_name": "",
          "dose": "",
          "frequency": "",
          "duration": "",
          "remarks": ""
        }
      ],
      "nutrition": [],
      "rehabilitation": "Gradual ambulation advised. Avoid strenuous activity. Follow cardiac rehabilitation if applicable.",
      "follow_up": {
        "instructions": [
          "[PLEASE CONFIRM YOUR APPOINTMENT FOR FOLLOW UP FROM APPOINTMENT DESK- 9007666895]",
          "For Medical query, contact Dr. ______",
          "For Other query contact Service care coordinator – 9051888973",
          "For any Medicational query, contact Medication Nurse – 6292290663",
          "(Timing: 10am–6pm Except Holiday)",
          "For diet query, contact Dietician – 9007033037 (Timing 12pm–3pm)",
          "Please inform your Doctor before: Changing medications, Dental/invasive procedures",
          "When to contact doctor: Chest pain, breathlessness, syncope, Fever >101°F, Bleeding, Leg swelling, Sugar fluctuation",
          "Emergency: 033-4088-4000"
        ],
        "follow_up_date": "",
        "reports": [],
        "tests": [],
        "specialty": "",
        "extracted_doctor": "",
        "recommended_doctor": ""
      }
    }
    """

    print("Calling Gemini...")
    response = model.generate_content([case_file_obj, prompt])

    genai.delete_file(case_file_obj.name)

    text = response.text.strip()

    # Clean markdown
    if text.startswith("```"):
        text = text.replace("```json", "").replace("```", "")

    data = json.loads(text)

    # 🔥 BACKEND VALIDATION (CRITICAL)

    def clean_text(t):
        if not t:
            return ""
        if isinstance(t, dict):
            t = json.dumps(t)
        elif isinstance(t, list):
            t = ", ".join([str(i) for i in t])
        else:
            t = str(t)
            
        banned = [
            "coronary angiography",
            "ptca",
            "uneventful",
            "puncture site",
        ]
        for b in banned:
            if b in t.lower():
                return ""
        return t

    # Clean procedures
    data["procedures"] = clean_text(data.get("procedures"))

    # Clean hospital course
    data["hospital_course"] = clean_text(data.get("hospital_course"))
    
    # Recursively fix dicts inside arrays (where strings are expected)
    def sanitize_node(node):
        if isinstance(node, dict):
            return {k: sanitize_node(v) for k, v in node.items()}
        elif isinstance(node, list):
            new_list = []
            for item in node:
                if isinstance(item, dict):
                    # If it's a known object type like medication, complaint, investigation, keep it.
                    # We can assume objects with 'complaint', 'condition', 'known', 'vitals', 'name', 'generic_name' are valid.
                    # But if it's an unexpected dict inside arrays like 'primary', 'associated_conditions', 'nutrition', etc.
                    # We stringify it.
                    if "type" in item and "details" in item:
                        new_list.append(f"{item['type']}: {item['details']}")
                    elif any(k in item for k in ["complaint", "condition", "name", "generic_name", "vitals", "known", "instructions"]):
                        new_list.append(sanitize_node(item)) # valid schema object
                    else:
                        new_list.append(json.dumps(item))
                else:
                    new_list.append(item)
            return new_list
        return node
        
    data = sanitize_node(data)
    
    # Also specifically target known string fields that might be returned as dicts
    if isinstance(data.get("allergies", {}).get("details"), dict):
        data["allergies"]["details"] = json.dumps(data["allergies"]["details"])

    # Ensure meds structure
    if not data.get("medications"):
        data["medications"] = [{
            "generic_name": "",
            "brand_name": "",
            "dose": "",
            "frequency": "",
            "duration": "",
            "remarks": ""
        }]

    # Ensure follow-up exists
    if "follow_up" not in data:
        data["follow_up"] = {
            "instructions": [],
            "follow_up_date": "",
            "reports": [],
            "tests": [],
            "specialty": "",
            "extracted_doctor": "",
            "recommended_doctor": ""
        }

    return data