import requests

url = "http://localhost:8000/users/"
headers = {
    "Content-Type": "application/json",
}
data = {
    "username": "zz2983",
    "first_name": "Zixiao",
    "last_name": "Zhang",
    "email": "zixiaozhang00@gmail.com",
    "contact": "(917) 979-5232",
    "location": "New York, NY",
    "interests": ["Travel， Food"],
    "age": 22,
    "gender": "Female",
    "friends": [],
    "group_member_list": [],
    "group_organizer_list": [],
    "event_organizer_list": [],
    "event_participation_list": []
}
response = requests.post(url, json=data, headers=headers)