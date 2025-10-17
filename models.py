from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import uuid

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now())
    is_a_miner = db.Column(db.Boolean, default=False)

    wallet = db.relationship("Wallet", back_populates="user", uselist=False)
    transactions_sent = db.relationship("Transaction", foreign_keys="Transaction.sender_id", back_populates="sender")
    transactions_received = db.relationship("Transaction", foreign_keys="Transaction.recipient_id", back_populates="recipient")

    def __repr__(self):
        return f"<User {self.username}>"

class Wallet(db.Model):
    __tablename__ = 'wallets'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    balance = db.Column(db.Float, default=0.0)
    usd_balance = db.Column(db.Float, default=0.0)

    user = db.relationship("User", back_populates="wallet")

    def __repr__(self):
        return f"<Wallet {self.user.username} Balance={self.balance}>"

class Transaction(db.Model):
    __tablename__ = 'transactions'
    id = db.Column(db.String(64), primary_key=True)  # tx_id (sha256 hash from your TecaCoin class)
    sender_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)  # NETWORK rewards will be NULL
    recipient_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    amount = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now())
    block_id = db.Column(db.String(36), db.ForeignKey('blocks.id'), nullable=True)  # links to mined block
    tx_type = db.Column(db.String(20), nullable=False, default="transfer")
    status = db.Column(db.String(20), nullable=False, default="pending")

    sender = db.relationship("User", foreign_keys=[sender_id], back_populates="transactions_sent")
    recipient = db.relationship("User", foreign_keys=[recipient_id], back_populates="transactions_received")
    block = db.relationship("Block", back_populates="transactions")

    def __repr__(self):
        return f"<Transaction {self.id} {self.amount}>"

class Block(db.Model):
    __tablename__ = 'blocks'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    index = db.Column(db.Integer, nullable=False)
    prev_hash = db.Column(db.String(64), nullable=False)
    hash = db.Column(db.String(64), nullable=False)
    nonce = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now())

    transactions = db.relationship("Transaction", back_populates="block")

    def __repr__(self):
        return f"<Block {self.index} Hash={self.hash[:10]}>"

class PendingTransaction(db.Model):
    __tablename__ = 'pending_transactions'
    id = db.Column(db.String(64), primary_key=True)  # same tx_id
    sender = db.Column(db.String(80), nullable=True)  # for quick lookup
    recipient = db.Column(db.String(80), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now())

    def __repr__(self):
        return f"<PendingTransaction {self.id} {self.amount}>"
