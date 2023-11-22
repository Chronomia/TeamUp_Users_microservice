import random
import string

import requests
import json

with open('user.json', 'r') as file:
    user_data = json.load(file)

url = "http://ec2-44-219-26-13.compute-1.amazonaws.com:8000/users/"
headers = {
    "Content-Type": "application/json",
}

for user in user_data:
    user["password"] = ''.join(random.choices(string.ascii_letters + string.digits, k=20))
    user["interests"] = user["interests"].split(', ')
    response = requests.post(url, json=user, headers=headers)
