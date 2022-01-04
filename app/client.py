import requests


def create_user():
    response = requests.post(
        'http://127.0.0.1:8088/users',
        json={'username': 'vanya1', 'email': 'vany2@vanya.ru', 'password': 'Ivan123', }
    )
    print(response.text)


def get_user():
    response = requests.get('http://127.0.0.1:8088/users/1')
    # data = response.text()
    print(response.text)


def get_ad():
    response = requests.get('http://127.0.0.1:8088/ads/3')
    print(response.text)


def create_ad():
    response = requests.post(
        'http://127.0.0.1:8088/ads',
        json={'title': 'van1', 'description': 'varya', 'creator_id': 1, }
    )
    print(response.text)


def delete_ad():
    response = requests.delete(f'http://127.0.0.1:8088/ads/1')
    print(response.text)


