import requests

update_url = "http://localhost:8000/users/65578061ab42592f44051019/update"

update_data = {
    "age": 23,
}

headers = {
    "Content-Type": "application/json",
}

response = requests.put(update_url, json=update_data, headers=headers)

print("Status Code:", response.status_code)
print("Response:", response.json())