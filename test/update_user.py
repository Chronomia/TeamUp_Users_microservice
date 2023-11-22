import requests

update_url = "http://localhost:8000/users/655bf58308d4f461da132298/update"

update_data = {
    "age": "30",
}

headers = {
    "Content-Type": "application/json",
}

response = requests.put(update_url, json=update_data, headers=headers)