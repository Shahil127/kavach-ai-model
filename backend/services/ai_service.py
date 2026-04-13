import os
import json
import time
import google.generativeai as genai


def process_case_file(case_pdf_path: str) -> dict:
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
    RULE 5: MEDICATIONS — CRITICAL EXTRACTION RULE
    -------------------------------------
    This case file has TWO distinct medication zones:

    ZONE A — "DISCHARGE MEDICATION / PRESENT MEDICATION" table
    - This is the ONLY valid source for discharge medications
    - It is a structured table with columns: Type/Form (Tab/Cap/Inj), Trade Name, Generic Name, Quantity, Strength, Mode, Frequency, Time, To Continue
    - It appears near the bottom of the document AFTER the "CONDITION AT DISCHARGE" section
    - Extract ONLY from this table

    ZONE B — "COURSE IN HOSPITAL" narratives
    - These contain drug names mentioned as part of inpatient treatment (e.g., "treated with Aspirin, Clopidogrel, Beta blockers, ACEI/ARB, LMWH...")
    - These are narrative treatment records, NOT discharge prescriptions
    - COMPLETELY IGNORE all drug names found in COURSE IN HOSPITAL section
    - COMPLETELY IGNORE all drug names found in procedure notes

    EXTRACTION RULES:
    1. For each row in the DISCHARGE MEDICATION table, extract:
       - type: from "Type/Form" column (e.g., "Tab", "Cap", "Inj", "Syrup")
       - brand_name: from "Trade Name" column (e.g., "Ecosprin", "Plavix", "Atorlip")
       - generic_name: from "Generic Name" column (e.g., "Aspirin", "Clopidogrel", "Atorvastatin")
       - dose: combine Quantity + Strength if both present (e.g., "10 x 75mg" → just use Strength: "75mg")
       - frequency: from "Frequency" column (e.g., "OD", "BD", "TDS")
       - duration: from "To Continue" or Time column if written, else ""
       - remarks: any special instruction written (e.g., "Night", "SL", "before food")

    2. If the DISCHARGE MEDICATION table is empty or not found, return ONE empty row:
       [{"type": "", "generic_name": "", "brand_name": "", "dose": "", "frequency": "", "duration": "", "remarks": ""}]

    3. DO NOT include any drug mentioned ONLY in:
       - Course in Hospital section
       - Procedure notes
       - Investigaton findings
       - Any narrative text

    4. DO NOT hallucinate durations. If "To Continue" column is blank, set duration to "".

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
          "type": "",
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
            "was treated with , aspirin, clopidogrel",
            "treated with aspirin, clopidogrel",
            "managed with aspirin, clopidogrel",
            "acei/arb, diuretics, lmwh",
            "beta blockers, acei/arb",
            "nikorandil, trimetazidine, statin, ranolazine",
            "antidiabetics, iv gtn/nitrate",
            "other drugs if any",
            "post uncomplicated mi",
            "post lvf/chf",
            "post cag with findings",
            "post acs",
            "puncture site is healthy",
            "femoral sheath was removed",
            "after act was satisfactory",
            "overnight stay in ccu",
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
                    if "event_type" in item and "details" in item:
                        new_list.append(f"{item['event_type']}: {item['details']}")
                    elif any(k in item for k in ["complaint", "condition", "name", "generic_name", "vitals", "known"]):
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
    def validate_medications(meds: list) -> list:
        \"\"\"
        Post-extraction validation pass for discharge medications.
        Removes meds that look like they came from IP narrative instead of discharge table.
        \"\"\"
        # These terms appear in IP treatment narratives but rarely in discharge tables as standalone entries
        ip_only_terms = [
            "lmwh", "iv gtn", "iv nitrate", "nikorandil", "trimetazidine",
            "ranolazine", "inj.", "injection", "thrombolysis", "streptokinase",
            "tenecteplase", "diuretics", "furosemide", "antibiotics"
        ]
        
        validated = []
        for med in meds:
            if not isinstance(med, dict):
                continue
            med_text = f"{med.get('generic_name', '')} {med.get('brand_name', '')} {med.get('remarks', '')}".lower()
            
            # Flag: if it's an IV-only drug with no oral dose, likely IP
            is_ip_only = any(term in med_text for term in ip_only_terms)
            
            # Flag: if no brand name AND no dose, it's likely hallucinated from narrative
            is_empty_row = not med.get('generic_name') and not med.get('brand_name')
            
            if is_empty_row:
                continue  # drop truly empty rows
            
            if is_ip_only:
                # Don't drop silently — flag it for review instead
                med['remarks'] = f"[REVIEW - possible IP med] {med.get('remarks', '')}".strip()
            
            validated.append(med)
        
        # Ensure at least one row
        if not validated:
            validated = [{"type": "", "generic_name": "", "brand_name": "", "dose": "", "frequency": "", "duration": "", "remarks": ""}]
        
        return validated

    data["medications"] = validate_medications(data.get("medications", []))

    # Ensure meds structure
    if not data.get("medications"):
        data["medications"] = [{
            "type": "",
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
            "follow_up_date": "",
            "reports": [],
            "tests": [],
            "specialty": "",
            "extracted_doctor": "",
            "recommended_doctor": ""
        }

    return data