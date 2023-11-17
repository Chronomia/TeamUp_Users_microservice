import requests

url = "http://localhost:8000/users/"
headers = {
    "Content-Type": "application/json",
}
data = {
    "username": "zz2983",
    "first_name": "Zixiao",
    "last_name": "Zhang",
    "email": "zz2983@columbia.edu",
    "contact": "(213) 879-0909",
    "location": "New York, NY",
    "interests": "Travel, Food",
    "age": 22,
    "gender": "Female",
    "friends":[],
    "group_member_list":[],
    "group_organizer_list":[],
    "event_organizer_list":[],
    "event_participation_list":[]
}
username = "65561dd83274a6af6fa14e22"
url1 =f"http://localhost:8000/users/{username}"
data_1 = {"id":"65561dd83274a6af6fa14e22"}
response = requests.delete(url + username)
print(response.status_code)
print(response)
