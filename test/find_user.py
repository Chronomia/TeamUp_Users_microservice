import requests

url = f"http://localhost:8000/users/6556f63c3274a6af6fa14e23"

headers = {
    "Content-Type": "application/json",
}

response = requests.get(url, headers=headers)

print(response.status_code)