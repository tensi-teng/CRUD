"""Cleanup script to remove smoke-test data created by `smoke_test.py`.
Removes the user with reg_number 'SMOKE_RN_001' and their fitness items.
Run with: python clean_smoke_data.py
"""
from app import app, db, User, FitnessItem

TEST_REG = 'SMOKE_RN_001'


def run():
    with app.app_context():
        user = User.query.filter_by(reg_number=TEST_REG).first()
        if not user:
            print('No smoke-test user found.')
            return 0

        # Delete fitness items explicitly (relationship cascade also covers this)
        items = FitnessItem.query.filter_by(user_id=user.id).all()
        for it in items:
            db.session.delete(it)
        db.session.delete(user)
        db.session.commit()
        print(f'Removed user {TEST_REG} and {len(items)} fitness items.')
        return 0


if __name__ == '__main__':
    rc = run()
    exit(rc)
