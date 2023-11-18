import requests

username = "exampleuser"

url = f"http://localhost:8000/users/id/6558405db11eb1c3d4462d0b"

headers = {
    "Content-Type": "application/json",
}

response = requests.delete(url, headers=headers)
