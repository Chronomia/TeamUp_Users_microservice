import requests
import json

with open('user.json', 'r') as file:
    user_data = json.load(file)

url = "http://localhost:8000/users/"
headers = {
    "Content-Type": "application/json",
}

for user in user_data:
    response = requests.post(url, json=user, headers=headers)
