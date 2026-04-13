import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=api_key)

print("Available models:")
try:
    for m in genai.list_models():
        print(f" - {m.name}")
except Exception as e:
    print(f"Error fetching models: {e}")
