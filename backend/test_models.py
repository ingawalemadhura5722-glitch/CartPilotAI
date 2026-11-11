import os
import time

from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

MODELS = [
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3.8-flash",
]

for model in MODELS:
    start = time.time()
    try:
        text = client.models.generate_content(model=model, contents="Say hi in 3 words").text
        print(f"OK   {model:26} {time.time() - start:4.1f}s  {text.strip()[:40]!r}")
    except Exception as exc:
        print(f"FAIL {model:26} {str(exc)[:100]}")