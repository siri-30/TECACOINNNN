import hashlib
import json
from datetime import datetime
from uuid import uuid4
from flask import current_app
from models import db
from models import Block, Transaction, PendingTransaction, Wallet, User 

class TecaCoin:
    def __init__(self):
        self.REWARD = 5  # block reward
        self.MAX_SUPPLY = 100_000  # maximum TECACoin in circulation


    def get_circulating_supply(self):
        """Return the total TECACoin circulating in all wallets."""
        from models import Wallet
        return sum(w.balance for w in Wallet.query.all())


    # ------------------ TRANSACTIONS ------------------ #
    def create_transaction(self, sender_username, recipient_username, amount):
        """
        Create a transaction and store it as pending until mined.
        sender_username can be "NETWORK" (for mining reward)
        """
        transaction = {
            "sender": sender_username,
            "recipient": recipient_username,
            "amount": amount,
            "timestamp": str(datetime.now())
        }
        tx_id = hashlib.sha256(json.dumps(transaction, sort_keys=True).encode()).hexdigest()

        pending_tx = PendingTransaction(
            id=tx_id,
            sender=sender_username,
            recipient=recipient_username,
            amount=amount
        )
        db.session.add(pending_tx)
        db.session.commit()

        return tx_id

    def get_pending_transactions(self):
        return PendingTransaction.query.all()

    def clear_pending_transactions(self):
        PendingTransaction.query.delete()
        db.session.commit()

    # ------------------ PROOF OF WORK ------------------ #
    def proof_of_work(self, prev_hash, transactions):
        nonce = 0
        while True:
            block_data = {
                "index": Block.query.count() + 1,
                "nonce": nonce,
                "prev_hash": prev_hash,
                "transactions": [t.id for t in transactions],
                "timestamp": str(datetime.now())
            }
            encoded_block = json.dumps(block_data, sort_keys=True).encode()
            new_hash = hashlib.sha256(encoded_block).hexdigest()
            if new_hash[:4] == "0000":  # difficulty = 4 leading zeros
                block_data["hash"] = new_hash
                return block_data
            nonce += 1

    # ------------------ MINING ------------------ #
    def mine_block(self, miner_username):
        """ Mines a block with pending transactions and rewards the miner, respecting max supply. """

        # 1️⃣ Only give mining reward if supply < MAX_SUPPLY
        current_supply = self.get_circulating_supply()
        if current_supply + self.REWARD <= self.MAX_SUPPLY:
            self.create_transaction("NETWORK", miner_username, self.REWARD)
        else:
            # No reward if cap reached
            pass

        # 2️⃣ Get all pending transactions
        pending_transactions = self.get_pending_transactions()
        if not pending_transactions:
            return None  # nothing to mine

        # 3️⃣ Get previous block hash
        last_block = Block.query.order_by(Block.index.desc()).first()
        prev_hash = last_block.hash if last_block else "0000000"

        # 4️⃣ Find valid proof (POW)
        block_data = self.proof_of_work(prev_hash, pending_transactions)

        # 5️⃣ Save block to DB
        new_block = Block(
            id=str(uuid4()),
            index=block_data["index"],
            prev_hash=block_data["prev_hash"],
            hash=block_data["hash"],
            nonce=block_data["nonce"],
            timestamp=datetime.now()
        )
        db.session.add(new_block)
        db.session.flush()  # get block.id before using

        # 6️⃣ Move transactions from pending → confirmed
        for ptx in pending_transactions:
            sender_user = User.query.filter_by(username=ptx.sender).first() if ptx.sender != "NETWORK" else None
            recipient_user = User.query.filter_by(username=ptx.recipient).first()

            tx = Transaction(
                id=ptx.id,
                sender=sender_user,
                recipient=recipient_user,
                amount=ptx.amount,
                block=new_block
            )
            db.session.add(tx)

            # update wallet balances
            if sender_user:
                sender_user.wallet.balance -= ptx.amount
            if recipient_user:
                recipient_user.wallet.balance += ptx.amount

            db.session.delete(ptx)

        db.session.commit()
        return new_block

    # ------------------ BLOCKCHAIN VIEW ------------------ #
    def get_chain(self):
        """ Return full blockchain as list of dicts (for API or debug) """
        blocks = Block.query.order_by(Block.index.asc()).all()
        chain_data = []
        for b in blocks:
            chain_data.append({
                "index": b.index,
                "prev_hash": b.prev_hash,
                "hash": b.hash,
                "nonce": b.nonce,
                "timestamp": b.timestamp.isoformat(),
                "transactions": [
                    {
                        "tx_id": tx.id,
                        "sender": tx.sender.username if tx.sender else "NETWORK",
                        "recipient": tx.recipient.username if tx.recipient else None,
                        "amount": tx.amount,
                        "timestamp": tx.timestamp.isoformat()
                    } for tx in b.transactions
                ]
            })
        return chain_data

    def get_balance(self, username):
        """ Get user's wallet balance """
        user = User.query.filter_by(username=username).first()
        return user.wallet.balance if user and user.wallet else 0.0
