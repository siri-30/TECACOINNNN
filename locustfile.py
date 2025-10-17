from locust import HttpUser, task, between, SequentialTaskSet
from faker import Faker

fake = Faker()

class UserBehavior(SequentialTaskSet):
    def on_start(self):
        # Runs when a simulated user starts
        self.username = fake.user_name() + str(fake.random_number(digits=5))
        self.email = f"{self.username}@example.test"
        self.password = "TestPass123!"
        self.confirm_password = "TestPass123!"
        
        # 1️⃣ Register a new user
        self.client.post("/get_started", json={
            "username": self.username,
            "email": self.email,
            "password": self.password,
            "confirm_password": self.confirm_password

        })
        
        # 2️⃣ Log in
        resp = self.client.post("/login", json={
            "email": self.email, "password": self.password
        })

        # 3️⃣ Save the login token (if any)
        if resp.status_code == 200 and "token" in resp.json():
            self.token = resp.json()["token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.token = None
            self.headers = {}

    # @task(3)
    # def create_transaction(self):
    #     # Create a random transaction
    #     payload = {
    #         "to_address": fake.uuid4(),
    #         "amount": 0.5,
    #         "currency": "TECA"
    #     }
    #     self.client.post("/api/transactions", json=payload, headers=self.headers)

    # @task(1)
    # def get_balance(self):
    #     # Check account balance
    #     self.client.get("/api/balance", headers=self.headers)


class WebsiteUser(HttpUser):
    tasks = [UserBehavior]
    wait_time = between(1, 3)
