from models import db, User, Wallet
from app import app
def update_user_balance(email, new_balance):
    user = User.query.filter_by(email=email).first()
    if not user:
        raise ValueError(f"User '{email}' not found.")
    if not user.wallet:
        raise ValueError(f"Wallet for user '{email}' not found.")
    user.wallet.usd_balance = new_balance
    db.session.commit()
    print(f"Updated {email}'s balance to {new_balance}.")

if __name__ == "__main__":
    with app.app_context():
        update_user_balance('wisdomosirichukwuemeka@gmail.com', 50.0)
