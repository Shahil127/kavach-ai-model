import google.generativeai as genai
import sys

try:
    genai.configure(api_key="AIzaSyAVXp2DyKdc_TsJMEzpQ5Z5DEa3OUox3eQ")
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(m.name)
except Exception as e:
    print(e)
