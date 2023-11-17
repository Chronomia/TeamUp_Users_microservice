import requests

list_users_url = "http://localhost:8000/users/"

params = {
    "interest": "Music",
    "location": "New York, NY",
}

headers = {
    "Content-Type": "application/json",
}

response = requests.get(list_users_url, params=params, headers=headers)

print("Status Code:", response.status_code)
print("Response:", response.json() if response.content else "No Content")