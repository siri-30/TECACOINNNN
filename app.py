from flask import Flask,render_template,request,redirect,url_for,flash
from flask_login import LoginManager,current_user,login_user,logout_user,UserMixin,login_required
from werkzeug.security import generate_password_hash,check_password_hash
from datetime import datetime
from models import db
from models import User,Wallet,Block,Transaction,PendingTransaction
import uuid
from flask_migrate import Migrate
from TECACoin import TecaCoin
import requests
from flask import jsonify

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///teca_coin.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = "khvac.kVVf.yiffugUIFUIUKJCVKKvckK;kuuvjjh5st,hgchccjy.j.uggc"
migrate = Migrate(app, db)
tc = TecaCoin()


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "Please login in or sign up to access this page!"
login_manager.login_message_category = "danger"

db.init_app(app)
with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


@app.route("/")
def home():
    return render_template("TECACoin_index.html")

@app.route("/get_started", methods=["GET","POST"])
def get_started():
    if current_user.is_authenticated:
        flash("You must log out before creating a new account.", "warning")
        return redirect(url_for("dashboard"))  

    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")


        if password != confirm_password:
            flash("Passwords do not Match!", "danger")
            return redirect(url_for('get_started'))
        
        user = User.query.filter_by(email=email).first()

        if user:
            flash(f"User {email} Already Exists", "warning")
            return redirect(url_for('get_started'))
        
        new_user = User(
            username = username,
            email=email,
            password_hash=generate_password_hash(password),
        )
        db.session.add(new_user)
        db.session.commit()
        db.session.refresh(new_user)
        new_wallet = Wallet(
            user_id=new_user.id)
        db.session.add(new_wallet)
        db.session.commit()

        flash("Registration Successful", "success")
        return redirect(url_for("login"))
    
    return render_template("TECACoin_getstarted.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash("Login Successful", "success")
            return redirect(url_for("dashboard"))
        
        flash("Incorrect Email or Password", "danger")
        return redirect(url_for("login"))
      
    return render_template("TECACoin_login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logout Successful", "success")
    return redirect(url_for('login'))

@app.route("/contact", methods=["GET", "POST"])
@login_required
def contact():
    if request.method == "POST":
        firstname = request.form.get("firstname")
        lastname = request.form.get("lastname")
        email = request.form.get("email")
        message = request.form.get("message")

        user = User.query.filter_by(email=email,firstname=firstname,lastname=lastname).first()

        if not user:
            flash("Sorry, user does not exist!", "danger")
            return redirect(url_for('get_started'))

        user.message = message
        db.session.commit()

        flash(f"{email}, we would get back to you soon", "success")


    return render_template("TECACoin_contact.html")

@app.route("/about")
def about():
    return render_template("TECACoin_about.html")

@app.route("/dashboard")
@login_required
def dashboard():
    user = User.query.filter_by(id=current_user.id).first()
    wallet = Wallet.query.filter_by(user_id=current_user.id).first()

    # Show all confirmed transactions for all users
    transactions = Transaction.query.order_by(Transaction.timestamp.desc()).all()
    for tx in transactions:
        tx.tx_type = "confirmed"

    # Show all pending transactions for all users
    pending_transactions = PendingTransaction.query.order_by(PendingTransaction.timestamp.desc()).all()
    for tx in pending_transactions:
        tx.tx_type = "pending"

    all_transactions = transactions + pending_transactions
    all_transactions.sort(key=lambda x: x.timestamp, reverse=True)

    chain_length = Block.query.count()
    return render_template("TECACoin_dashboard.html", user=user, wallet=wallet, transactions=all_transactions, chain_length=chain_length)


@app.route("/transfer", methods=["GET", "POST"])
@login_required
def transfer_TECA():
    wallet = Wallet.query.filter_by(user_id=current_user.id).first()

    if request.method == "POST":
        recipient_id = request.form.get("recipient_id")
        amount = float(request.form.get("amount"))

        if amount <= 0:
            flash("Amount must be greater than zero.", "danger")
            return redirect(url_for('transfer_TECA'))

        if amount > wallet.balance:
            flash("Insufficient balance.", "danger")
            return redirect(url_for('transfer_TECA'))

        recipient_wallet = Wallet.query.filter_by(id=recipient_id).first()
        if not recipient_wallet:
            flash("Recipient wallet not found.", "danger")
            return redirect(url_for('transfer_TECA'))
        if recipient_wallet.id == wallet.id:
            flash("You cannot transfer TECACoin to yourself.", "danger")
            return redirect(url_for('transfer_TECA'))
        
        tx_id = tc.create_transaction(
            sender_username=current_user.username,
            recipient_username=recipient_wallet.user.username,
            amount=amount
        )

        # wallet.balance -= amount
        # recipient_wallet.balance += amount

        # db.session.commit()

        flash(f"Transaction is awaiting approval.", "warning")
        return redirect(url_for('dashboard'))

    return render_template("transfer_TECACoin.html", wallet=wallet)

@app.route("/become_a_miner", methods=["POST"])
@login_required
def become_a_miner():
    user = User.query.filter_by(id=current_user.id).first()
    if user.is_a_miner:
        flash("You are already a miner.", "info")
        return redirect(url_for('dashboard'))

    user.is_a_miner = True
    db.session.commit()
    flash("You are now a miner! You can start mining blocks.", "success")
    return redirect(url_for('dashboard'))

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy_teca():
    wallet = Wallet.query.filter_by(user_id=current_user.id).first()

    if request.method == "POST":
        amount_str = request.form.get("amount")
        payment_method = request.form.get("payment_method")

        try:
            amount = float(amount_str)
        except ValueError:
            flash("Invalid amount entered!", "danger")
            return redirect(url_for("buy_teca"))

        if amount <= 0:
            flash("Amount must be greater than 0", "danger")
            return redirect(url_for("buy_teca"))


        dollar_cost = amount * 20

        # Enforce TECACoin max supply
        from TECACoin import TecaCoin
        tc = TecaCoin()
        current_supply = tc.get_circulating_supply()
        if current_supply + amount > tc.MAX_SUPPLY:
            flash(f"Cannot buy: TECACoin supply cap ({tc.MAX_SUPPLY}) would be exceeded!", "danger")
            return redirect(url_for("buy_teca"))

        if dollar_cost > wallet.usd_balance:
            flash("Insufficient USD balance!", "danger")
            return redirect(url_for("buy_teca"))

        wallet.usd_balance -= dollar_cost
        wallet.balance += amount

        # Get SYSTEM user (sender_id=None)
        recipient_user = User.query.filter_by(username=current_user.username).first()
        buy_txn = Transaction(
            id=str(uuid.uuid4()),
            sender_id=None,
            recipient_id=recipient_user.id,
            amount=amount
        )
        db.session.add(buy_txn)
        db.session.commit()

        flash("Buy transaction successful! Funds credited immediately.", "success")
        return redirect(url_for("dashboard"))

    return render_template("buy_TECACoin.html", wallet=wallet)

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell_teca():
    wallet = Wallet.query.filter_by(user_id=current_user.id).first()

    if request.method == "POST":
        amount_str = request.form.get("amount")

        try:
            amount = float(amount_str)
        except ValueError:
            flash("Invalid amount entered!", "danger")
            return redirect(url_for("sell_teca"))

        if amount <= 0:
            flash("Amount must be greater than 0", "danger")
            return redirect(url_for("sell_teca"))

        dollar_value = amount * 20

        if amount > wallet.balance:
            flash("Insufficient TECA balance!", "danger")
            return redirect(url_for("sell_teca"))

        wallet.balance -= amount
        wallet.usd_balance += dollar_value

        sender_user = User.query.filter_by(username=current_user.username).first()

        # Ensure SYSTEM user and wallet exist
        system_user = User.query.filter_by(username="SYSTEM").first()
        if not system_user:
            system_user = User(username="SYSTEM", email="system@teca.local", password_hash=generate_password_hash("system"))
            db.session.add(system_user)
            db.session.commit()
            db.session.refresh(system_user)
            system_wallet = Wallet(user_id=system_user.id)
            db.session.add(system_wallet)
            db.session.commit()
        else:
            system_wallet = Wallet.query.filter_by(user_id=system_user.id).first()
            if not system_wallet:
                system_wallet = Wallet(user_id=system_user.id)
                db.session.add(system_wallet)
                db.session.commit()

        # Credit sold TECACoin to SYSTEM wallet
        system_wallet.balance += amount
        db.session.commit()

        sell_txn = Transaction(
            id=str(uuid.uuid4()),
            sender_id=sender_user.id,
            recipient_id=system_user.id,
            amount=amount
        )
        db.session.add(sell_txn)
        db.session.commit()

        flash("Sell transaction successful! Funds credited immediately.", "success")
        return redirect(url_for("dashboard"))

    return render_template("sell_TECACoin.html", wallet=wallet)

@app.route("/show_transactions")
def show_transactions():
    user = User.query.filter_by(id=current_user.id).first()
    wallet = Wallet.query.filter_by(user_id=current_user.id).first()

    # Show all pending transactions for all users
    pending_transactions = PendingTransaction.query.order_by(PendingTransaction.timestamp.desc()).all()
    for tx in pending_transactions:
        tx.tx_type = "pending"
    return render_template("show_transactions.html", user=user, wallet=wallet, transactions=pending_transactions)

@app.route("/mine_single_block")
@login_required 
def mine_single_block():
    user = User.query.filter_by(id=current_user.id).first()
    if not user.is_a_miner:
        flash("You must be a miner to mine blocks. Please become a miner first.", "warning")
        return redirect(url_for('dashboard'))

    pending_txs = PendingTransaction.query.all()
    if not pending_txs:
        flash("No pending transactions to include in the block.", "info")
        return redirect(url_for('dashboard'))

    # Create a new block with pending transactions
    new_block = tc.mine_block(miner_username=user.username)

    if new_block:
        # Add the new block to the database
        db.session.add(new_block)
        db.session.commit()

        flash(f"Block mined successfully! Block ID: {new_block.id}", "success")
    else:
        flash("Failed to mine a new block. Please try again.", "danger")

    return redirect(url_for('dashboard'))

@app.route('/get_user_name/<wallet_id>')
def get_user_name(wallet_id):
    wallet = Wallet.query.filter_by(id=wallet_id).first()
    if wallet and wallet.user:
        return {'exists': True, 'name': wallet.user.username}
    return {'exists': False}

@app.route('/crypto-data')
def crypto_data():
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": "bitcoin,ethereum,binancecoin,cardano,solana",
        "vs_currencies": "usd",
        "include_market_cap": "true",
        "include_24hr_change": "true"
    }
    data = requests.get(url, params=params).json()
    return jsonify(data)


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0")