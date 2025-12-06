
import requests
import sys

# URL conf
BASE_URL = "http://localhost:8000"
LOGIN_URL = f"{BASE_URL}/api/auth/token"

credentials = {
    "username": "admin@ambiental.local",
    "password": "admin123"
}

try:
    print(f"Testing login at: {LOGIN_URL}")
    print(f"Credentials: {credentials['username']} / {'*' * len(credentials['password'])}")
    
    response = requests.post(LOGIN_URL, data=credentials)
    
    print(f"Status Code: {response.status_code}")
    print(f"Content-Type: {response.headers.get('Content-Type')}")
    
    if response.status_code == 200:
        print("✅ Login Successful")
        print("Response JSON keys:", list(response.json().keys()))
    else:
        print("❌ Login Failed")
        print("Response text prefix:", response.text[:200])
        try:
           print("JSON:", response.json())
        except:
           print("Response is NOT JSON")

except Exception as e:
    print(f"❌ Error connecting to backend: {e}")
