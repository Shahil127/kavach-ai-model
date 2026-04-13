import os
import json
import argparse
from dotenv import load_dotenv
from services.ai_service import process_case_file

load_dotenv()

def main():
    parser = argparse.ArgumentParser(description="Test Gemini Extraction directly")
    parser.add_argument("--case", type=str, required=True, help="Path to the patient case file PDF")
    
    args = parser.parse_args()
    
    print(f"Testing extraction with Case File: {args.case}")
    
    try:
        result = process_case_file(args.case)
        print("\n--- EXTRACTION SUCCESS ---")
        print(json.dumps(result, indent=2))
        
        with open("extraction_result.json", "w") as f:
            json.dump(result, f, indent=2)
        print("\nResult saved to extraction_result.json")
    except Exception as e:
        print(f"\n--- EXTRACTION FAILED ---")
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
