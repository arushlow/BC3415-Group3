import random
import time
import os

from locust import HttpUser, TaskSet, between, task


class UserBehavior(TaskSet):
    def on_start(self):
        self.login()
        self.account_ids = []
        self.chat_ids = []
        
    def login(self):
        username = f"test_user_{random.randint(1000, 9999)}"
        password = "password123"
        
        self.client.post("/signup", {
            "username": username,
            "password": password
        })
        
        response = self.client.post("/login", {
            "username": username,
            "password": password
        })
        
        if response.status_code != 200:
            self.username = "3"
            self.client.post("/login", {
                "username": self.username,
                "password": "3"
            })
        else:
            self.username = username

    @task(1)
    def visit_welcome(self):
        self.client.get("/")

    @task(5)
    def visit_homepage(self):
        self.client.get("/homepage")
    
    @task(3)
    def visit_features(self):
        self.client.get("/features")
    
    @task(3)
    def visit_more(self):
        self.client.get("/more")
    
    @task(2)
    def visit_change_login_info(self):
        self.client.get("/change_login_info")
    
    @task(1)
    def change_username(self):
        new_username = f"changed_user_{random.randint(10000, 19999)}"
        self.client.post("/change_username", {
            "new_username": new_username
        })
        self.username = new_username
    
    @task(1)
    def change_password(self):
        self.client.post("/change_password", {
            "new_password": "newpassword123"
        })
    
    @task(3)
    def run_simulation(self):
        simulation_data = {
            "current_age": random.randint(25, 45),
            "retirement_age": random.randint(55, 70),
            "monthly_income": random.randint(3000, 8000),
            "monthly_expenses": random.randint(1500, 5000),
            "monthly_savings": random.randint(500, 2000),
            "investment_strategy": random.choice(["conservative", "balanced", "aggressive"]),
            "retirement_investment_strategy": random.choice(["conservative", "balanced", "aggressive"]),
            "investment_increase": random.uniform(0, 0.05),
            "career_switch_impact": random.uniform(-0.2, 0.3),
            "career_switch_age": random.randint(30, 50),
            "purchase_amount": random.randint(0, 100000),
            "purchase_age": random.randint(30, 50)
        }
        
        self.client.post("/run_simulation", 
                        json=simulation_data,
                        headers={"Content-Type": "application/json"})
    
    @task(3)
    def visit_scenario_simulation(self):
        self.client.get("/scenario_simulation")
    
    @task(2)
    def test_ai_adjustments(self):
        adjustment_data = {
            "income": random.randint(3000, 10000),
            "expenses": random.randint(1500, 5000),
            "savings": random.randint(500, 3000),
            "investments": random.randint(10000, 100000),
            "debt": random.randint(0, 50000),
            "risk_tolerance": random.choice(["low", "medium", "high"])
        }
        
        self.client.post("/ai_generated_adjustments", 
                        json=adjustment_data,
                        headers={"Content-Type": "application/json"})
    
    @task(2)
    def visit_ai_generated_adjustments(self):
        self.client.get("/ai_generated_adjustments")
    
    @task(1)
    def new_chat(self):
        self.client.get("/new_chat")
    
    @task(2)
    def clear_chat_history(self):
        self.client.post("/clear_chat_history")
        self.chat_ids = []
    
    @task(4)
    def visit_dashboard(self):
        self.client.get("/dashboard")
    
    @task(2)
    def view_overview(self):
        self.client.get("/view_overview")
    
    @task(2)
    def view_invest(self):
        self.client.get("/view_invest")
    
    @task(2)
    def visit_account_details(self):
        if self.account_ids:
            account_id = random.choice(self.account_ids)
            self.client.get(f"/account/{account_id}")
    
    @task(1)
    def visit_data_page(self):
        self.client.get("/data")
    
    @task(2)
    def upload_overview_data(self):
        csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                           'User Banking Data Overview - Test.csv')
        
        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                csv_content = f.read()
            
            files = {'overview': ('overview.csv', csv_content, 'text/csv')}
            self.client.post("/data_overview", files=files)
        except Exception as e:
            print(f"Error uploading overview data: {e}")
    
    @task(2)
    def upload_transaction_data(self):
        if self.account_ids:
            csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           'User Banking Data Breakdown - Test.csv')

            try:
                with open(csv_path, 'r', encoding='utf-8-sig') as f:
                    csv_content = f.read()
                files = {'transaction': ('transaction.csv', csv_content, 'text/csv')}
                self.client.post("/data_transaction", files=files)
            except Exception as e:
                print(f"Error uploading transaction data: {e}")
    
    @task(2)
    def upload_investment_data(self):
        csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           'User Investment Data - Test.csv')
        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                csv_content = f.read()
            files = {'invest': ('investment.csv', csv_content, 'text/csv')}
            self.client.post("/data_invest", files=files)
        except Exception as e:
            print(f"Error uploading investment data: {e}")
    
    @task(2)
    def logout(self):
        self.client.get("/logout")
        time.sleep(1)
        self.login()

class FinanceAppUser(HttpUser):
    tasks = [UserBehavior]
    host = "http://127.0.0.1:8000"
    wait_time = between(3, 7)
