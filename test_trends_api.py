import requests

try:
    response = requests.get("http://127.0.0.1:8001/trends/data")
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print("Data keys:", data.keys())
        print("Dates:", data.get('dates'))
        print("Flood Risk:", data.get('flood_risk'))
    else:
        print("Error response:", response.text)
except Exception as e:
    print(f"Connection failed: {e}")
