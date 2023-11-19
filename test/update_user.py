import requests

update_url = "http://localhost:8000/users/65584096b11eb1c3d4462d0c/update"

update_data = {
    "age": 23,
}

headers = {
    "Content-Type": "application/json",
}

response = requests.put(update_url, json=update_data, headers=headers)