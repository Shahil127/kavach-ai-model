import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def generate_discharge_pdf(data: dict) -> str:
    """
    Generates a PDF discharge summary matching the template's layout using ReportLab.
    Returns the file path to the generated PDF.
    """
    output_filename = "generated_discharge_summary.pdf"
    
    # Set up the document
    doc = SimpleDocTemplate(
        output_filename, 
        pagesize=letter,
        rightMargin=30, leftMargin=30,
        topMargin=30, bottomMargin=18
    )
    
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    title_style.alignment = 1 # Center
    
    heading_style = styles['Heading2']
    heading_style.textColor = colors.darkblue
    heading_style.keepWithNext = True
    
    subheading_style = ParagraphStyle(
        name='SubHeading',
        parent=styles['Normal'],
        keepWithNext=True
    )
    
    normal_style = styles['Normal']
    
    elements = []
    
    # Title
    elements.append(Paragraph("DISCHARGE SUMMARY", title_style))
    elements.append(Spacer(1, 20))
    
    # Pre-process data to parse any stringified JSON objects
    import json
    parsed_data = {}
    for k, v in data.items():
        if isinstance(v, str) and v.strip().startswith("{") and v.strip().endswith("}"):
            try:
                parsed_data[k] = json.loads(v)
            except:
                parsed_data[k] = v
        else:
            parsed_data[k] = v
            
    data = parsed_data

    # Create top section table (Patient Info)
    def extract_demographics(data_node):
        from typing import Dict
        import re
        flat_data: Dict[str, str] = {}
        def flatten(d):
            for k, v in d.items():
                if isinstance(v, dict):
                    flatten(v)
                elif not isinstance(v, list):
                    # Split CamelCase (e.g. 'PatientName' -> 'Patient Name', 'HospitalID' -> 'Hospital ID')
                    # To preserve ID formatting we use lookbehind and lookahead
                    spaced_k = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', k)
                    flat_data[spaced_k.lower().strip()] = str(v).strip()
        flatten(data_node)
        
        def find_best(hints):
            # Exact matches
            for hint in hints:
                for k, v in flat_data.items():
                    if hint == k.replace("_", " ") and len(v) < 60:
                        return v
            # Substring matches
            for hint in hints:
                for k, v in flat_data.items():
                    clean_k = " " + k.replace("_", " ") + " "
                    if f" {hint} " in clean_k and len(v) < 60:
                        if hint == "name" and any(x in clean_k for x in ["hospital", "doctor", "consultant", "father", "mother", "spouse", "attending"]):
                            continue
                        if hint == "id" and any(x in clean_k for x in ["transaction", "reference", "email", "bed"]):
                            continue
                        return v
            return ""
            
        return {
            "name": find_best(["patient name", "name", "full name"]),
            "age": find_best(["age", "patient age"]),
            "gender": find_best(["gender", "sex", "patient gender"]),
            "id": find_best(["hospital id", "patient id", "mrn", "uhid", "ipd no", "ipd number", "hospital no"]),
            "admit": find_best(["admission date", "date of admission", "admit date", "admitted on", "admit"]),
            "discharge": find_best(["discharge date", "date of discharge", "discharge on", "discharge"])
        }

    demos = extract_demographics(data)
    patient_name = demos["name"]
    age = demos["age"]
    gender = demos["gender"]
    hospital_id = demos["id"]
    admission_date = demos["admit"]
    discharge_date = demos["discharge"]

    patient_info_data = [
        ["Patient Name:", patient_name, "Hospital ID:", hospital_id],
        ["Age / Gender:", f"{age} / {gender}", "Admission Date:", admission_date],
        ["", "", "Discharge Date:", discharge_date]
    ]

    t = Table(patient_info_data, colWidths=[90, 170, 90, 170])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.whitesmoke),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.black),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('FONTNAME', (1,0), (1,-1), 'Helvetica'), # Values normal font
        ('FONTNAME', (3,0), (3,-1), 'Helvetica'), # Values normal font
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey)
    ]))
    elements.append(t)
    elements.append(Spacer(1, 20))

    # Helper function to render other sections properly
    def render_section(key, value):
        display_key = key.replace("_", " ").upper()
        
        # Skip top level patient_information dict since info is already extracted to header
        if display_key.replace(" ", "") in ["PATIENTINFORMATION", "PATIENTINFO", "DEMOGRAPHICS", "PATIENTDEMOGRAPHICS"]:
            return
            
        # Custom handler for Follow Up Instructions (flattens and appends hardcoded doctors)
        if "FOLLOW UP" in display_key or "FOLLOWUP" in display_key:
            elements.append(Paragraph("FOLLOW_UP_INSTRUCTIONS", heading_style))
            elements.append(Spacer(1, 5))
            
            # Extract dynamic bullet points
            def extract_bullets(v):
                if isinstance(v, list):
                    for item in v:
                        if isinstance(item, str):
                            elements.append(Paragraph(f"• {item}", normal_style))
                        elif isinstance(item, dict):
                            extract_bullets(item)
                elif isinstance(v, dict):
                    for dk, dv in v.items():
                        if "review with doctor" not in dk.lower():
                            extract_bullets(dv)
                elif isinstance(v, str):
                    if "., " in v:
                        for s in v.split("., "):
                            elements.append(Paragraph(f"• {s}", normal_style))
                    else:
                        elements.append(Paragraph(f"• {v}", normal_style))
            
            extract_bullets(value)
            
            # Add hardcoded doctors
            doctors = [
                "Dr. C. K. Kundu in OPD as required.", "Dr. Ravi P. in OPD as required.", "Dr. Joy Saibal Shome in OPD as required.",
                "Dr. Avradip Santra in OPD as required.", "Dr. Moumita Banerjee in OPD as required.", "Dr. Ranita Saha in OPD as required.",
                "Dr. Manoj Kumar Daga in OPD as required.", "Dr. Ratan Kumar Das in OPD as required.", "Dr. M.K.Das in OPD as required.",
                "Dr. Kuntal Roychowdhuri in OPD as required.", "Dr. Sabyasachi Paul in OPD as required.", "Dr. Suman Chatterjee in OPD as required.",
                "Dr. Suman Halder in OPD as required.", "Dr. D. Kahali in OPD as required.", "Dr. A.B. Malpani in OPD as required.",
                "Dr. Anjan Siotia in OPD after 4 to 6 weeks or SOS.", "Dr. T.K. Praharaj in OPD as required.", "Dr. Shuvo Dutta in OPD as required.",
                "Dr. Anil Mishra in OPD after 2 months / SOS.", "Dr. Aniruddha Mandal in OPD as required.", "Dr. Azizul Haque in OPD as required.",
                "Dr. Amanul Hoque in OPD as required.", "Dr. Rakesh Sarkar in OPD as required.", "Dr. Kuntal Bhattacharyya in OPD as required.",
                "Dr. Monotosh Panja in OPD as required.", "Dr. Madhumanti Panja in OPD as required.", "Dr. P. C. Bagchi in OPD as required.",
                "Dr. H. M. Rath in OPD as required.", "Dr. Achyut Sarkar in OPD as required.", "Dr. Sudeb Mukherjee in OPD as required.",
                "Dr. Niket Dilip Arora in OPD as required.", "Dr. Sudip Kumar Ghosh in OPD as required.", "Dr. Imran Ahmed in OPD as required.",
                "Dr. Aditya Verma in OPD as required.", "Dr. Tushar Kanti Patra in OPD as required.", "Dr. Pradip Bhowmik in OPD as required."
            ]
            for doc in doctors:
                elements.append(Paragraph(f"• To review with {doc}", normal_style))
                
            elements.append(Spacer(1, 15))
            return
            
        elements.append(Paragraph(display_key, heading_style))
        elements.append(Spacer(1, 5))
        
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    item_str = ", ".join(f"<b>{k.replace('_', ' ').title()}</b>: {v}" for k, v in item.items())
                    elements.append(Paragraph(f"• {item_str}", normal_style))
                else:
                    elements.append(Paragraph(f"• {str(item)}", normal_style))
        elif isinstance(value, dict):
            for k, v in value.items():
                if isinstance(v, (dict, list)):
                    elements.append(Paragraph(f"<b>{k.replace('_', ' ').title()}</b>:", subheading_style))
                    if isinstance(v, list):
                        for item in v:
                            if isinstance(item, dict):
                                item_str = ", ".join(f"<b>{sub_k.replace('_', ' ').title()}</b>: {sub_v}" for sub_k, sub_v in item.items())
                                elements.append(Paragraph(f"• {item_str}", normal_style))
                            else:
                                elements.append(Paragraph(f"• {str(item)}", normal_style))
                    else:
                        for sub_k, sub_v in v.items():
                            elements.append(Paragraph(f"• <b>{sub_k.replace('_', ' ').title()}</b>: {str(sub_v)}", normal_style))
                else:
                    elements.append(Paragraph(f"<b>{k.replace('_', ' ').title()}</b>: {v}", normal_style))
                elements.append(Spacer(1, 2))
        else:
            val_str = str(value)
            elements.append(Paragraph(val_str.replace("\n", "<br/>"), normal_style))
            
        elements.append(Spacer(1, 15))

    header_keys_clean = ["name", "patientname", "age", "gender", "sex", "hospitalid", "mrn", "admissiondate", "dischargedate", "patientdemographics", "patientinformation", "demographics"]
    footer_keys_clean = ["dischargeconsultantdetails", "hospitalcontactinformation", "contact"]

    # Process data to group related keys (unflatten)
    processed_data = {}
    footer_data = {}
    
    for key, value in data.items():
        clean_key = key.lower().replace("_", "").replace(" ", "")
        if clean_key in header_keys_clean:
            continue
            
        # Separate footer information
        if any(f in clean_key for f in footer_keys_clean):
            footer_data[key] = value
            continue

        if " - " in key:
            group, sub = key.split(" - ", 1)
        elif "_" in key:
            group, sub = key.split("_", 1)
        else:
            group, sub = key, None
            
        if sub:
            if group not in processed_data:
                processed_data[group] = {}
            if isinstance(processed_data[group], dict):
                processed_data[group][sub] = value
            else:
                # Collision fallback
                processed_data[key] = value
        else:
            if group not in processed_data:
                processed_data[group] = value
            elif isinstance(processed_data[group], dict) and isinstance(value, dict):
                processed_data[group].update(value)

    for key, value in processed_data.items():
        # Double check if any footer keys slipped into processed_data groups
        if "contact" in key.lower() and isinstance(value, dict):
            footer_data[key] = value
            continue
        render_section(key, value)

    # Render Footer / Signature Block
    elements.append(Spacer(1, 40))
    
    # Draw Doctor Signature Line
    doctor_name = "______________"
    doctor_title = ""
    doctor_reg = ""
    
    # Try to extract the doctor's details from the footer_data if the AI found it
    for fk, fv in footer_data.items():
        if "consultant" in fk.lower():
            if isinstance(fv, dict):
                doctor_name = str(fv.get("Name", fv.get("Doctor", "______________")))
                doctor_title = str(fv.get("Title", fv.get("Specialization", "")))
                doctor_reg = str(fv.get("MedicalRegistrationNo", fv.get("RegNo", "")))
            elif isinstance(fv, str):
                doctor_name = fv
                
    sig_style = ParagraphStyle(
        name='Signature',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        alignment=2 # Right align
    )
    
    elements.append(Paragraph(f"{doctor_name}", sig_style))
    if doctor_title:
        elements.append(Paragraph(f"{doctor_title}", ParagraphStyle(name='SigSub', parent=styles['Normal'], alignment=2)))
    if doctor_reg:
        elements.append(Paragraph(f"{doctor_reg}", ParagraphStyle(name='SigSub2', parent=styles['Normal'], alignment=2)))
        
    elements.append(Spacer(1, 30))
    
    # Draw Hospital Contact Info Centered
    hospital_name = "B M Birla Heart Hospital"
    hospital_address = "1/1 National Library Avenue, Kolkata - 700 027, India"
    hospital_phone = "+91 33 4088 4088"
    
    for fk, fv in footer_data.items():
        if "hospital" in fk.lower() and isinstance(fv, dict):
            hospital_name = str(fv.get("HospitalName", hospital_name))
            hospital_address = str(fv.get("Address", hospital_address))
            hospital_phone = str(fv.get("PhoneNumber", fv.get("Phone", hospital_phone)))
            
    footer_style = ParagraphStyle(
        name='FooterStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        textColor=colors.dimgrey,
        alignment=1 # Center align
    )
    
    elements.append(Paragraph(f"<b>{hospital_name}</b>", footer_style))
    elements.append(Paragraph(f"{hospital_address} | Tel: {hospital_phone}", footer_style))

    doc.build(elements)
    
    return output_filename
