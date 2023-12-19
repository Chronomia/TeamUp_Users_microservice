import unittest
import requests


class UserTest(unittest.TestCase):

    def setUp(self):
        self.url = "http://127.0.0.1:8000/"
        self.headers = {
            "Content-Type": "application/json"
        }
        self.user = {
            "username": "test",
            "first_name": "Test First Name",
            "last_name": "Test Last Name",
            "email": "test@gmail.com",
            "contact": "(123) 456-7890",
            "location": "New York, NY",
            "interests": ["Music", "Travel", "Food"],
            "age": 23,
            "gender": "Male",
            "friends": [],
            "password": "12345678"
        }
        response = requests.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'user_service_status': 'ONLINE'})

    def test_create_user(self):
        response = requests.post(self.url + "users", json=self.user, headers=self.headers)
        self.assertEqual(response.status_code, 201)

    def test_delete_user(self):
        response = requests.get(self.url + "users/name/" + self.user["username"], headers=self.headers)
        user_id = response.json()["id"]
        deleted = requests.delete(self.url + "users/" + user_id, headers=self.headers)
        self.assertEqual(deleted.status_code, 200)

    def test_list_users(self):
        params = {
            "interest": "Music",
            "location": "New York, NY",
        }

        result = {'users': [
            {'username': 'jsumshon7', 'first_name': 'Joana', 'last_name': 'Sumshon', 'email': 'jsumshon7@gmail.com',
             'contact': '(565) 889-0999', 'location': 'New York, NY',
             'interests': ['Music', 'Gaming', 'Arts & Creativity'], 'age': 45, 'gender': 'Female'},
            {'username': 'bcoumbex', 'first_name': 'Benjamin', 'last_name': 'Coumbe', 'email': 'bcoumbex@gmail.com',
             'contact': '(938) 258-9971', 'location': 'New York, NY', 'interests': ['Music'], 'age': 21,
             'gender': 'Male'},
            {'username': 'qhumm2m', 'first_name': 'Quint', 'last_name': 'Humm', 'email': 'qhumm2m@gmail.com',
             'contact': '(646) 925-1359', 'location': 'New York, NY', 'interests': ['Music'], 'age': 37,
             'gender': 'Male'}
        ]
        }

        response = requests.get(self.url + "users", params=params, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), result)

    def test_find_user(self):
        response = requests.post(self.url + "users", json=self.user, headers=self.headers)
        self.assertEqual(response.status_code, 201)

        response = requests.get(self.url + "users/name/" + self.user["username"], headers=self.headers)
        self.assertEqual(response.status_code, 200)

        user_id = response.json()['id']
        result = requests.get(self.url + "users/id/" + user_id, headers=self.headers)
        self.assertEqual(result.status_code, 200)
        true_result = {
            'username': 'test',
            'first_name': 'Test First Name',
            'last_name': 'Test Last Name',
            'email': 'test@gmail.com',
            'contact': '(123) 456-7890',
            'location': 'New York, NY',
            'interests': ['Music', 'Travel', 'Food'],
            'age': 23,
            'gender': 'Male',
            'id': user_id,
            'friends': []
        }
        self.assertEqual(result.json(), true_result)

        result2 = requests.get(self.url + "users/email/" + 'test@gmail.com', headers=self.headers)
        self.assertEqual(result2.status_code, 200)
        self.assertEqual(result2.json(), true_result)

        deleted = requests.delete(self.url + "users/" + user_id, headers=self.headers)
        self.assertEqual(deleted.status_code, 200)

    def test_update_user(self):
        response = requests.post(self.url + "users", json=self.user, headers=self.headers)
        self.assertEqual(response.status_code, 201)

        response = requests.get(self.url + "users/name/" + self.user["username"], headers=self.headers)
        self.assertEqual(response.status_code, 200)

        user_id = response.json()['id']

        prompt = {
            'first_name': 'New First Name',
            'last_name': 'New Last Name',
            'age': 24
        }

        response = requests.put(self.url + "users/" + user_id + "/profile", json=prompt, headers=self.headers)
        self.assertEqual(response.status_code, 200)

        result = requests.get(self.url + "users/name/" + self.user["username"], headers=self.headers)
        self.assertEqual(result.status_code, 200)
        true_result = {
            'username': 'test',
            'first_name': 'New First Name',
            'last_name': 'New Last Name',
            'email': 'test@gmail.com',
            'contact': '(123) 456-7890',
            'location': 'New York, NY',
            'interests': ['Music', 'Travel', 'Food'],
            'age': 24,
            'gender': 'Male',
            'id': user_id,
            'friends': []
        }
        self.assertEqual(result.json(), true_result)

        deleted = requests.delete(self.url + "users/" + user_id, headers=self.headers)
        self.assertEqual(deleted.status_code, 200)

    def test_login(self):
        response = requests.post(self.url + "users", json=self.user, headers=self.headers)
        self.assertEqual(response.status_code, 201)

        response = requests.post(self.url + "token",
                                 data={'username': 'test', 'password': '12345678'})
        self.assertEqual(response.status_code, 200)

        response = requests.post(self.url + "token",
                                 data={'username': 'test', 'password': 'incorrect-password'})
        self.assertEqual(response.status_code, 401)

        response = requests.get(self.url + "users/name/" + self.user["username"], headers=self.headers)
        self.assertEqual(response.status_code, 200)

        user_id = response.json()['id']

        deleted = requests.delete(self.url + "users/" + user_id, headers=self.headers)
        self.assertEqual(deleted.status_code, 200)


if __name__ == '__main__':
    unittest.main()
