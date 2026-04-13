import requests

api_key = "AIzaSyAVXp2DyKdc_TsJMEzpQ5Z5DEa3OUox3eQ"
model = "gemini-3-flash-preview"
url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

payload = {"contents": [{"parts": [{"text": "hi hello"}]}]}
headers = {"Content-Type": "application/json"}

try:
    print(f"Asking the {model} model: 'hi hello'...")
    r = requests.post(url, headers=headers, json=payload)
    print("\n--- STATUS CODE ---")
    print(r.status_code)
    
    print("\n--- MODEL RESPONSE TEXT ---")
    if r.status_code == 200:
        data = r.json()
        print(data['candidates'][0]['content']['parts'][0]['text'])
    else:
        print("ERROR:", r.text)
except Exception as e:
    print("FATAL ERROR:", e)
