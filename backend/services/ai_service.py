import os
import json
import time
import logging
import google.generativeai as genai

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# BANNED TEMPLATE PHRASES (exact boilerplate only)
# These are generic cardiology discharge templates — NOT real patient sentences
# ─────────────────────────────────────────────
BANNED_TEMPLATE_PHRASES = [
    "was treated with , aspirin, clopidogrel",
    "treated with aspirin, clopidogrel, beta blockers, acei/arb, lmwh",
    "managed with aspirin, clopidogrel, beta blockers, acei/arb",
    "acei/arb, diuretics, lmwh",
    "post uncomplicated mi",
    "post lvf/chf",
    "post cag with findings",
    "post acs",
    "puncture site is healthy",
    "femoral sheath was removed",
    "after act was satisfactory",
    "overnight stay in ccu",
    "nikorandil, trimetazidine, statin, ranolazine",
    "antidiabetics, iv gtn/nitrate",
    "other drugs if any",
    "coronary angiography",
    "ptca",
]

def clean_text(t: str) -> str:
    """
    Only strips generic TEMPLATE boilerplate from hospital_course / procedures.
    Does NOT wipe real clinical narratives that happen to mention common drug names.
    Matches only complete banned phrases in isolation, not fragments inside real sentences.
    """
    if not t:
        return ""
    if isinstance(t, dict):
        t = json.dumps(t)
    elif isinstance(t, list):
        t = ", ".join([str(i) for i in t])
    else:
        t = str(t)

    t_lower = t.lower()
    # Only nuke the whole value if it IS the template phrase (not just contains one word from it)
    for phrase in BANNED_TEMPLATE_PHRASES:
        # Match if the phrase is more than 60% of the entire text — it IS the template
        if phrase in t_lower and len(phrase) > 0.6 * len(t_lower):
            logger.warning(f"clean_text: Blocked pure template phrase: '{phrase[:60]}...'")
            return ""
    return t


def _build_prompt() -> str:
    return """
    You are a STRICT medical data extraction system.

    -------------------------------------
    RULE 0: REASONING SCRATCHPAD (CRITICAL)
    -------------------------------------
    You MUST output a "_clinical_reasoning_scratchpad" string at the top of the JSON. Quoting exactly from the document, explicitly justify every diagnosis and medication you extract. You are strictly banned from adding anything not physically written in the case file.

    -------------------------------------
    RULE 1: CASE FILE ONLY
    -------------------------------------
    Extract ONLY from the given document.
    DO NOT use any prior knowledge.

    -------------------------------------
    RULE 2: NO GUESSING -> "to be filled"
    -------------------------------------
    If data is not present in the document:
    - use "to be filled" for text
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
    A DISCHARGE medication is ONLY something the patient takes HOME by themselves.
    It must meet ALL of the following criteria:
    - A self-administrable form: Tab, Cap, Syrup, Drops, or a self-injectable Pen
    - Has a patient-self-administered frequency: OD, BD, TDS, HS, at night, before food, etc.
    - NOT something applied by a nurse or doctor at a wound site
    - NOT something applied or administered in a clinical setting

    STRICTLY EXCLUDE these from discharge medications (drop them entirely):
    - Any row where the name contains: dressing, soaking, wash, betadine, saline, gauze, bandage, pack, suture
    - Any ointment/cream/gel/lotion that is applied TO a wound, radial/femoral site, or surgical site
      (e.g., Fusicdc L/A ointment on puncture site = EXCLUDED)
    - Any row labelled as "Daily dressing", "Wound care", "Soaking", or similar
    - Any drug that requires a doctor or nurse to administer in clinic (IV, IM injection regimens requiring hospital visit)

    Self-applied topicals (patient applies at home on non-wound skin) ARE allowed if explicitly stated.

    GENERIC NAME RESOLUTION:
    If the generic name column is blank but the brand name is given, resolve it from pharmacological knowledge.
    Common examples: Ecosprin→Aspirin, Clopilet/Plavix→Clopidogrel, Aztor/Atorlip→Atorvastatin,
    Telma→Telmisartan, Glimestar→Glimepiride, Cilacar→Cilnidipine, Eptoin→Phenytoin,
    Valprol CR→Valproate, Pan/Pantocid→Pantoprazole, Fusicdc→Fusidic acid,
    Ecosprin AV→Aspirin+Atorvastatin combination.
    This is pure pharmacological fact — resolving a brand to a generic is allowed.

    EXTRACTION RULES:
    1. For each VALID discharge medication row, extract:
       - type: from Type/Form column (e.g., "Tab", "Cap", "Syrup")
       - brand_name: from Trade Name column
       - generic_name: from Generic Name column, OR resolved from brand name if blank
       - dose: Strength column value (e.g., "75mg")
       - frequency: from Frequency column (e.g., "OD", "BD", "TDS")
       - duration: from "To Continue" column if written, else ""
       - remarks: any special instruction written

    2. If no valid discharge medications found, return ONE empty row:
       [{"type": "", "generic_name": "", "brand_name": "", "dose": "", "frequency": "", "duration": "", "remarks": ""}]

    3. DO NOT include any drug mentioned ONLY in:
       - Course in Hospital section
       - Procedure notes
       - Investigation findings
       - Any narrative text

    4. DO NOT hallucinate durations. If "To Continue" column is blank, set duration to "".

    -------------------------------------
    RULE 6: COURSE / PROCEDURAL NOTE
    -------------------------------------
    Synthesize a comprehensive paragraph summarizing the patient's procedures and course in hospital logically over time, BUT ONLY IF sufficient clinical timeline information is explicitly available in the extracted data.
    If sufficient detailed context does not exist to justify synthesizing a summary, strictly output "to be filled" and DO NOT guess.

    -------------------------------------
    RULE 7: DOCTOR
    -------------------------------------
    Extract ONLY if present
    else "to be filled"

    -------------------------------------
    RULE 8: OUTPUT & CONFIDENCE
    -------------------------------------
    RETURN STRICT JSON ONLY. Provide a "_confidence_scores" section rating clarity (1 to 100).

    EXPECTED JSON SCHEMA FORMAT:
    {
      "_clinical_reasoning_scratchpad": "",
      "_confidence_scores": {
        "patient_details": 100,
        "diagnosis": 100,
        "presenting_complaints": 100,
        "past_history": 100,
        "allergies": 100,
        "clinical_exam": 100,
        "investigations": 100,
        "procedures": 100,
        "hospital_course": 100,
        "condition_at_discharge": 100,
        "medications": 100,
        "follow_up": 100
      },
      "patient_details": {
        "patient_name": "to be filled",
        "age_sex": "to be filled",
        "uhid": "to be filled",
        "admission_date": "to be filled",
        "discharge_date": "to be filled",
        "bed_no": "to be filled",
        "consultant": "to be filled"
      },
      "diagnosis": {
        "primary": [],
        "associated_conditions": []
      },
      "presenting_complaints": [
        { "complaint": "to be filled", "duration": "to be filled" }
      ],
      "past_history": [
        { "condition": "to be filled", "duration": "to be filled", "remarks": "to be filled" }
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


def _upload_and_wait(case_pdf_path: str) -> object:
    """Upload PDF to Gemini and wait until ACTIVE."""
    logger.info(f"Uploading file to Gemini: {case_pdf_path}")
    file_obj = genai.upload_file(case_pdf_path, mime_type="application/pdf")
    while True:
        info = genai.get_file(file_obj.name)
        if info.state.name == "ACTIVE":
            break
        elif info.state.name == "FAILED":
            raise ValueError("Gemini file upload processing FAILED")
        time.sleep(2)
    logger.info(f"File ACTIVE in Gemini: {file_obj.name}")
    return file_obj


def _call_model(model, file_obj, prompt: str) -> str:
    """Call Gemini model and return raw text response."""
    response = model.generate_content([file_obj, prompt])
    return response.text.strip()


def _parse_json(raw_text: str) -> dict:
    """Strip markdown fences and parse JSON."""
    text = raw_text
    if text.startswith("```"):
        text = text.replace("```json", "").replace("```", "")
    return json.loads(text.strip())


def _quality_check(data: dict) -> list[str]:
    """
    Returns a list of field names that failed quality thresholds.
    These are the gaps that will trigger Model B.
    """
    gaps = []

    # Hospital course: empty or suspiciously short
    hc = data.get("hospital_course", "")
    if not hc or hc == "to be filled" or len(str(hc)) < 30:
        gaps.append("hospital_course")

    # Procedures
    proc = data.get("procedures", "")
    if not proc or proc == "to be filled":
        gaps.append("procedures")

    # Medications: only one row and it's all blanks/to be filled
    meds = data.get("medications", [])
    if not meds or (len(meds) == 1 and not meds[0].get("generic_name") and not meds[0].get("brand_name")):
        gaps.append("medications")

    # Primary diagnosis empty
    if not data.get("diagnosis", {}).get("primary"):
        gaps.append("diagnosis")

    return gaps


def _merge_data(primary: dict, secondary: dict, gaps: list[str]) -> dict:
    """
    Merge secondary model results into primary gaps only.
    Primary values always win where they exist; secondary only fills blanks.
    """
    merged = {**primary}

    if "hospital_course" in gaps:
        sec_hc = secondary.get("hospital_course", "")
        if sec_hc and sec_hc != "to be filled" and len(str(sec_hc)) > len(str(merged.get("hospital_course", ""))):
            merged["hospital_course"] = sec_hc
            logger.info("Merge: hospital_course filled from Model B")

    if "procedures" in gaps:
        sec_proc = secondary.get("procedures", "")
        if sec_proc and sec_proc != "to be filled":
            merged["procedures"] = sec_proc
            logger.info("Merge: procedures filled from Model B")

    if "medications" in gaps:
        sec_meds = secondary.get("medications", [])
        if sec_meds and len(sec_meds) > 0 and (sec_meds[0].get("generic_name") or sec_meds[0].get("brand_name")):
            merged["medications"] = sec_meds
            logger.info(f"Merge: medications filled from Model B ({len(sec_meds)} rows)")

    if "diagnosis" in gaps:
        sec_diag = secondary.get("diagnosis", {})
        if sec_diag.get("primary"):
            merged["diagnosis"] = sec_diag
            logger.info("Merge: diagnosis filled from Model B")

    return merged


def _post_process(data: dict) -> dict:
    """Sanitize, validate, and normalize the extracted data."""

    # Clean procedures and hospital_course
    data["procedures"] = clean_text(data.get("procedures", ""))
    data["hospital_course"] = clean_text(data.get("hospital_course", ""))

    # Recursively fix unexpected dict/list types
    def sanitize_node(node):
        if isinstance(node, dict):
            return {k: sanitize_node(v) for k, v in node.items()}
        elif isinstance(node, list):
            new_list = []
            for item in node:
                if isinstance(item, dict):
                    if "event_type" in item and "details" in item:
                        new_list.append(f"{item['event_type']}: {item['details']}")
                    elif any(k in item for k in ["complaint", "condition", "name", "generic_name", "vitals", "known"]):
                        new_list.append(sanitize_node(item))
                    else:
                        new_list.append(json.dumps(item))
                else:
                    new_list.append(item)
            return new_list
        return node

    data = sanitize_node(data)

    if isinstance(data.get("allergies", {}).get("details"), dict):
        data["allergies"]["details"] = json.dumps(data["allergies"]["details"])

    # ─────────────────────────────────────────────
    # Wound care / non-discharge item filters
    # ─────────────────────────────────────────────
    WOUND_CARE_KEYWORDS = [
        "dressing", "daily dressing", "betadine", "normal saline", "saline wash",
        "gauze", "bandage", "packing", "wound care", "wound wash", "soaking",
        "suture", "stitch", "radial site", "femoral site", "puncture site",
    ]

    WOUND_TOPICAL_TYPES = ["dressing"]
    WOUND_TOPICAL_BRANDS = ["fusicdc", "fusidic", "betadine ointment", "silver sulfadiazine", "soframycin"]

    validated_meds = []
    for med in data.get("medications", []):
        if not isinstance(med, dict):
            continue

        name_text = f"{med.get('generic_name', '')} {med.get('brand_name', '')} {med.get('remarks', '')} {med.get('type', '')}".lower()

        # Tier 1: Drop by wound care keywords
        if any(kw in name_text for kw in WOUND_CARE_KEYWORDS):
            logger.info(f"Wound care row excluded: {med.get('brand_name', '')}")
            continue

        # Tier 2: Drop wound-applied topicals by type + known brand
        med_type = med.get("type", "").lower()
        med_brand = med.get("brand_name", "").lower()
        if any(t in med_type for t in WOUND_TOPICAL_TYPES):
            logger.info(f"Wound topical (type) excluded: {med.get('brand_name', '')}")
            continue
        if any(b in med_brand for b in WOUND_TOPICAL_BRANDS):
            logger.info(f"Wound topical (brand) excluded: {med.get('brand_name', '')}")
            continue

        # Tier 3: Drop truly empty rows (no brand and no generic)
        is_empty = not med.get("generic_name") and not med.get("brand_name")
        if is_empty:
            continue

        # Keep — passes all filters
        validated_meds.append(med)

    if not validated_meds:
        validated_meds = [{"type": "to be filled", "generic_name": "to be filled", "brand_name": "to be filled",
                           "dose": "to be filled", "frequency": "to be filled", "duration": "to be filled", "remarks": "to be filled"}]
    data["medications"] = validated_meds

    # Ensure follow_up exists
    if "follow_up" not in data:
        data["follow_up"] = {
            "follow_up_date": "to be filled",
            "reports": [], "tests": [],
            "specialty": "to be filled",
            "extracted_doctor": "to be filled",
            "recommended_doctor": "to be filled"
        }

    return data


def process_case_file(case_pdf_path: str, request_id: str = "N/A") -> dict:
    """
    Production-safe extraction with:
    - Smart clean_text() that preserves real clinical content
    - Selective dual-model extraction (Model B only triggered on quality gaps)
    - Structured logging for Render traceability
    """
    api_key_primary = os.environ.get("GEMINI_API_KEY_PRIMARY")
    api_key_secondary = os.environ.get("GEMINI_API_KEY_SECONDARY")

    if not api_key_primary:
        raise ValueError("GEMINI_API_KEY_PRIMARY not found in environment")

    model_name = "gemini-3-flash-preview"
    prompt = _build_prompt()

    # ─── MODEL A (Primary key) ───
    logger.info(f"[{request_id}] Configuring primary Gemini client | model: {model_name}")
    genai.configure(api_key=api_key_primary)
    model_a = genai.GenerativeModel(model_name)

    file_obj_a = None
    try:
        file_obj_a = _upload_and_wait(case_pdf_path)
        logger.info(f"[{request_id}] Calling Model A...")
        raw_a = _call_model(model_a, file_obj_a, prompt)
        data_a = _parse_json(raw_a)
        logger.info(f"[{request_id}] Model A extraction complete")
    except Exception as e:
        logger.error(f"[{request_id}] Model A failed: {e}")
        raise
    finally:
        if file_obj_a:
            try:
                genai.delete_file(file_obj_a.name)
            except Exception:
                pass

    # ─── QUALITY CHECK ───
    gaps = _quality_check(data_a)

    if not gaps:
        logger.info(f"[{request_id}] Quality check passed — skipping Model B")
        return _post_process(data_a)

    logger.warning(f"[{request_id}] Quality gaps detected: {gaps} — triggering Model B")

    if not api_key_secondary:
        logger.warning(f"[{request_id}] No secondary key available — returning Model A result with gaps")
        return _post_process(data_a)

    # ─── MODEL B (Secondary key) ───
    file_obj_b = None
    try:
        genai.configure(api_key=api_key_secondary)
        model_b = genai.GenerativeModel(model_name)
        file_obj_b = _upload_and_wait(case_pdf_path)
        logger.info(f"[{request_id}] Calling Model B...")
        raw_b = _call_model(model_b, file_obj_b, prompt)
        data_b = _parse_json(raw_b)
        logger.info(f"[{request_id}] Model B extraction complete — merging gaps")
        merged = _merge_data(data_a, data_b, gaps)
        return _post_process(merged)
    except Exception as e:
        logger.error(f"[{request_id}] Model B failed: {e} — falling back to Model A result")
        return _post_process(data_a)
    finally:
        if file_obj_b:
            try:
                genai.delete_file(file_obj_b.name)
            except Exception:
                pass