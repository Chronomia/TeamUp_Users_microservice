import requests

update_url = "http://localhost:8000/users/6557ed5752f6af7655975db2/update"

update_data = {
    "age": 22,
}

headers = {
    "Content-Type": "application/json",
}

response = requests.put(update_url, json=update_data, headers=headers)

print("Status Code:", response.status_code)
print("Response:", response.json())
