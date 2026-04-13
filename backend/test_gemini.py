import requests

api_key = "AIzaSyAVXp2DyKdc_TsJMEzpQ5Z5DEa3OUox3eQ"
models = [
    "gemini-2.5-flash-lite",
    "gemini-flash-latest",
    "gemini-3-flash-preview",
    "gemini-2.5-pro",
    "gemini-pro-latest"
]
payload = {"contents": [{"parts": [{"text": "hi hello"}]}]}
headers = {"Content-Type": "application/json"}

for m in models:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={api_key}"
    try:
        r = requests.post(url, headers=headers, json=payload)
        print(f"Model: {m} -> STATUS: {r.status_code}")
        if r.status_code == 200:
            print("WORKING MODEL FOUND:", m)
            break
    except Exception as e:
        pass
