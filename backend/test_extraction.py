import os
import json
import argparse
from dotenv import load_dotenv
from services.ai_service import process_case_file

load_dotenv()

def main():
    parser = argparse.ArgumentParser(description="Test Gemini Extraction directly")
    parser.add_argument("--case", type=str, required=True, help="Path to the patient case file PDF")
    parser.add_argument("--template", type=str, default="../Discharge_summary.pdf", help="Path to the template PDF")
    
    args = parser.parse_args()
    
    print(f"Testing extraction with Case File: {args.case}")
    print(f"Template File: {args.template}")
    
    try:
        result = process_case_file(args.case, args.template)
        print("\n--- EXTRACTION SUCCESS ---")
        print(json.dumps(result, indent=2))
        
        # Save to a file for easy viewing
        output_file = "extraction_result.json"
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2)
            
        print(f"\nResult also saved to {output_file}")
    except Exception as e:
        print(f"\n--- EXTRACTION FAILED ---")
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
