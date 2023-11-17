import requests

username = "exampleuser"

url = f"http://localhost:8000/users/65578061ab42592f44051019"

headers = {
    "Content-Type": "application/json",
}

response = requests.delete(url, headers=headers)
