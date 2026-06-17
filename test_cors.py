import httpx

url = "https://pmtrucs-internal-new.azurewebsites.net/api/v1/auth/login"
headers = {
    "Origin": "https://mango-water-005426500.7.azurestaticapps.net",
    "Access-Control-Request-Method": "POST",
}

try:
    # Test OPTIONS preflight
    resp = httpx.options(url, headers=headers)
    print("OPTIONS status:", resp.status_code)
    print("OPTIONS headers:", resp.headers)
except Exception as e:
    print("OPTIONS error:", e)

try:
    # Test POST request
    resp = httpx.post(url, headers={"Origin": "https://mango-water-005426500.7.azurestaticapps.net"}, data={"username": "admin", "password": "bad"})
    print("POST status:", resp.status_code)
    print("POST headers:", resp.headers)
except Exception as e:
    print("POST error:", e)
