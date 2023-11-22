import requests

url = f"http://ec2-44-219-26-13.compute-1.amazonaws.com:8000/users/id/6556f63c3274a6af6fa14e23"

headers = {
    "Content-Type": "application/json",
}

response = requests.get(url, headers=headers)

print(response.status_code)
