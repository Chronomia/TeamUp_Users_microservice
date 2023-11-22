import requests

url = "http://ec2-44-219-26-13.compute-1.amazonaws.com:8000/users/"
headers = {
    "Content-Type": "application/json",
}
data = {
    "first_name": "Zixiao",
    "last_name": "Zhang",
    "email": "zixiaozhang00@gmail.com",
    "contact": "(917) 979-5232",
    "location": "New York, NY",
    "interests": ["Travel， Food"],
    "age": 22,
    "gender": "Female"
}
response = requests.post(url, json=data, headers=headers)
