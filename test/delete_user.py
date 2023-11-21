import requests

username = "exampleuser"

url = f"http://localhost:8000/users/655bf5b908d4f461da132299"

headers = {
    "Content-Type": "application/json",
}

response = requests.delete(url, headers=headers)
