import requests

username = "exampleuser"

url = f"http://ec2-44-219-26-13.compute-1.amazonaws.com:8000/users/655bf5b908d4f461da132299"

headers = {
    "Content-Type": "application/json",
}

response = requests.delete(url, headers=headers)
