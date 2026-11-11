
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

client_id = os.getenv("PAYPAL_CLIENT_ID")
client_secret = os.getenv("PAYPAL_CLIENT_SECRET")
base_url = os.getenv(
    "PAYPAL_BASE_URL",
    "https://api-m.sandbox.paypal.com"
)

if not client_id or not client_secret:
    print("ERROR: PayPal credentials are missing from backend/.env")
else:
    try:
        response = httpx.post(
            f"{base_url}/v1/oauth2/token",
            auth=(client_id, client_secret),
            data={"grant_type": "client_credentials"},
            headers={"Accept": "application/json"},
            timeout=20.0
        )

        if response.status_code == 200:
            print("SUCCESS: PayPal Sandbox connection works!")
            print("Access token received successfully.")
            print("Token type:", response.json().get("token_type"))
        else:
            print("PayPal connection failed.")
            print("HTTP status:", response.status_code)
            print("Response:", response.text[:1000])

    except httpx.RequestError as error:
        print("Network error:", str(error))
