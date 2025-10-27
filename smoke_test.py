"""Simple smoke test for the Fitness_App Flask API.
This script uses Flask's test client to exercise register -> login -> create -> list flows.
Run with: python smoke_test.py
"""
import sys
from app import app, db

TEST_REG = "SMOKE_RN_001"
TEST_PASSWORD = "smokepass"


def run():
    with app.app_context():
        # Ensure tables exist
        db.create_all()

    client = app.test_client()

    # 1) Register (ignore 409 if it already exists)
    resp = client.post('/register', json={
        'name': 'SmokeTester',
        'reg_number': TEST_REG,
        'password': TEST_PASSWORD,
    })
    print('register:', resp.status_code, resp.get_json())
    if resp.status_code not in (201, 409):
        print('Register failed unexpectedly')
        return 2

    # 2) Login
    resp = client.post('/login', json={'reg_number': TEST_REG, 'password': TEST_PASSWORD})
    print('login:', resp.status_code, resp.get_json())
    if resp.status_code != 200:
        print('Login failed')
        return 3

    token = resp.get_json().get('access_token')
    if not token:
        print('No access token returned')
        return 4

    headers = {'Authorization': f'Bearer {token}'}

    # 3) Create fitness item
    resp = client.post('/fitness', json={'title': 'Test Run', 'description': '3km'}, headers=headers)
    print('create fitness:', resp.status_code, resp.get_json())
    if resp.status_code != 201:
        print('Create fitness failed')
        return 5

    # 4) List fitness items
    resp = client.get('/fitness', headers=headers)
    print('list fitness:', resp.status_code, resp.get_json())
    if resp.status_code != 200:
        print('List fitness failed')
        return 6

    items = resp.get_json().get('items', [])
    if not isinstance(items, list) or len(items) < 1:
        print('Unexpected items list')
        return 7

    print('SMOKE TEST PASSED')
    return 0


if __name__ == '__main__':
    rc = run()
    sys.exit(rc)
