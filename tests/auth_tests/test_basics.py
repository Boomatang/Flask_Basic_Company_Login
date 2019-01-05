import pytest
from flask import current_app, url_for

from app import db
from app.auth_models import User, Company

paths = ['main.index', 'auth.login', 'auth.register']


def test_app_exists(client):
    assert client is not None


def test_app_is_testing(client):
    assert current_app.config['TESTING']


@pytest.mark.single_thread
@pytest.mark.parametrize('path', paths)
def test_main_nav_paths(client, path):

    assert client.get(url_for(path)).status_code == 200


users = [{'email': 'pass1@example.com', 'password': 'cat'},
         {'email': 'pass2@example.com', 'password': 'cat'}]


@pytest.mark.parametrize('user', users)
def test_user_login_redirects_to_index(client, user):
    u = User()
    u.email = user['email']
    u.password = user['password']
    u.confirmed = True
    db.session.add(u)
    db.session.commit()
    data = {'email': user['email'],
            'password': user['password']}
    response = client.post(url_for('auth.login'),
                           data=data, follow_redirects=True)

    assert b'<h1>Page Header</h1>' in response.data


users = [{'email': 'fail1@example.com', 'password': 'fake'}]


@pytest.mark.parametrize('user', users)
def test_user_login_fails(client, user):
    data = {'email': user['email'],
            'password': user['password']}
    response = client.post(url_for('auth.login'),
                           data=data, follow_redirects=True)

    assert b'Invalid E-mail or Password' in response.data


users = [{'company': 'Boring Company', 'username': 'jim', 'email': 'jim@test.com', 'password': 'cat', 'password2': 'cat'}]


@pytest.mark.parametrize('user', users)
def test_user_register_complete(clean_db, client, user):
    data = {'company': user['company'],
            'username': user['username'],
            'email': user['email'],
            'password': user['password'],
            'password2': user['password2']}

    response = client.post(url_for('auth.register'),
                           data=data)
    db_user = User.query.filter_by(email=user['email']).first()

    assert response.status_code == 302
    assert db_user.username == user['username']
    assert db_user.company.owner.email == user['email']


users = [{'company': 'Boring Company', 'username': 'jim fitz', 'email': 'test@test.com', 'password': 'cat',
          'password2': 'cat', 'massage': b'must have only letters'},
         {'company': 'The Fast Company', 'username': 'jim', 'email': 'jim@test', 'password': 'cat', 'password2': 'cat',
          'massage': b'Invalid email address'},
         {'company': 'Bad Company', 'username': 'jim', 'email': 'jim@test.com', 'password': 'cat', 'password2': 'dog',
          'massage': b'Passwords must match'}]


@pytest.mark.parametrize('user', users)
def test_user_register_fails(clean_db, client, user):
    data = {'company': user['company'],
            'username': user['username'],
            'email': user['email'],
            'password': user['password'],
            'password2': user['password2']}

    response = client.post(url_for('auth.register'),
                           data=data)

    assert user['massage'] in response.data


paths = ['main.test', 'auth.change_password', 'auth.password_reset_request',
         'auth.change_email_request']


@pytest.mark.single_thread
@pytest.mark.parametrize('path', paths)
def test_login_required(clean_db, client, path):
    u = User()
    u.password = 'cat'
    u.email = 'test@test.test'
    u.confirmed = True

    response = client.post(url_for('auth.login'),
                           data={
                               'email': 'test@test.com',
                               'password': 'cat'},
                           follow_redirects=True)

    assert client.get(url_for(path), follow_redirects=True).status_code == 200


def create_company():
    user1 = User(email='user1@example.com', password='cat', confirmed=True)
    user2 = User(email='user2@example.com', password='cat', confirmed=True)

    company = Company(name='Example.com')

    db.session.add(user1)
    db.session.add(user2)
    db.session.add(company)

    company.add_user(user1)
    company.add_user(user2)
    company.set_company_owner(user1)

    db.session.commit()


def login_user(user, client):
    data = {'email': user['email'],
            'password': user['password']}
    response = client.post(url_for('auth.login'),
                           data=data, follow_redirects=True)

    return response


users = [{'email': 'user1@example.com', 'password': 'cat', 'response': True},
         {'email': 'user2@example.com', 'password': 'cat', 'response': False}]


@pytest.mark.parametrize('user', users)
def test_menu_for_company_settings_link(client, clean_db, user):
    """Test if the user can see the company settings"""

    check_string = b'Company Settings'

    create_company()
    response = login_user(user, client)

    answer = check_string in response.data

    assert answer == user['response']
