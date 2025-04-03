from datetime import datetime
import json
import os
from io import StringIO, BytesIO
import uuid
import csv
from functools import wraps
import numpy as np
import matplotlib.pyplot as plt


from dotenv import load_dotenv
from flask import Flask, Response, redirect, render_template, request, session, url_for, jsonify
from flask_bcrypt import Bcrypt
from openai import OpenAI
from peewee import IntegrityError
from peewee import *

from model import ChatHistory, User, DataOverview, DataTransaction, DataInvestment, create_tables, database
from simulation import simulate_retirement

create_tables()
load_dotenv()
client = OpenAI(
    base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY")
)
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")
bcrypt = Bcrypt(app)


def login_required(f):
    @wraps(f)
    def inner(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return inner


@app.route("/")
def welcome():
    return render_template("welcome.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        try:
            user = User.get(User.username == username)
            if not bcrypt.check_password_hash(user.password, password):
                return render_template("login.html", error="Invalid password")

            session["logged_in"] = True
            session["username"] = username
            return redirect(url_for("home"))
        except User.DoesNotExist:
            return render_template("login.html", error="User not found")

    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"].strip()
        if not username:
            return render_template("signup.html", error="Username cannot be empty")

        password = request.form["password"]
        result = User.select().where(User.username == username).exists()
        if result:
            return render_template("signup.html", error="User already exists")

        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")
        with database.atomic():
            User.create(username=username, password=hashed_password)
        return redirect(url_for("login"))
    return render_template("signup.html")


@app.route("/features")
@login_required
def features():
    return render_template("features.html")


@app.route("/more")
@login_required
def more():
    return render_template("more.html")  # Your existing More Options page


@app.route("/change_login_info")
@login_required
def change_login_info():
    return render_template("change_login_info.html")


@app.route("/change_username", methods=["GET", "POST"])
@login_required
def change_username():
    if request.method == "POST":
        new_username = request.form["new_username"].strip()
        if not new_username:
            return render_template(
                "change_username.html", error="Username cannot be empty"
            )

        if User.select().where(User.username == new_username).exists():
            return render_template(
                "change_username.html", error="Username already exists"
            )
        try:
            with database.atomic():
                user = User.get(User.username == session["username"])
                user.username = new_username
                user.save()
        except IntegrityError:
            return render_template(
                "change_username.html", error="Username already exists"
            )
        except Exception as e:
            print(e)
            return render_template(
                "change_username.html", error="An error occurred, please try again"
            )

        session["username"] = new_username
        return redirect(url_for("home"))
    return render_template("change_username.html")


@app.route("/change_password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        new_password = request.form["new_password"]

        with database.atomic():
            user = User.get(User.username == session["username"])
            user.password = bcrypt.generate_password_hash(new_password).decode("utf-8")
            user.save()
        return redirect(url_for("home"))
    return render_template("change_password.html")

@app.route("/logout")
@login_required
def logout():
    session.pop("logged_in", None)
    session.pop("user", None)
    session.pop("username", None)
    return redirect(url_for("welcome"))


@app.route("/run_simulation", methods=["POST"])
@login_required
def run_simulation():
    data = request.get_json()

    current_age = int(data.get("current_age", 30))
    retirement_age = int(data.get("retirement_age", 65))
    monthly_income = float(data.get("monthly_income", 5000))
    monthly_expenses = float(data.get("monthly_expenses", 3000))
    monthly_savings = float(data.get("monthly_savings", 1000))
    investment_strategy = data.get("investment_strategy", "balanced")
    retirement_investment_strategy = data.get("retirement_investment_strategy", "conservative")
    investment_increase = float(data.get("investment_increase", 0))
    career_switch_impact = float(data.get("career_switch_impact", 0))
    career_switch_age = int(data.get("career_switch_age", 0))
    purchase_amount = float(data.get("purchase_amount", 0))
    purchase_age = int(data.get("purchase_age", 0))

    results = simulate_retirement(
        current_age, 
        retirement_age, 
        monthly_income, 
        monthly_expenses, 
        monthly_savings, 
        investment_strategy, 
        investment_increase, 
        career_switch_impact, 
        purchase_amount,
        career_switch_age,
        purchase_age,
        retirement_investment_strategy
    )

    return jsonify(results)


@app.route("/scenario_simulation")
@login_required
def scenario_simulation():
    return render_template("scenario_simulation.html")


@app.route("/ai_generated_adjustments")
@login_required
def ai_generated_adjustments():
    return render_template("ai_generated_adjustments.html")


@app.route("/send_message", methods=["POST"])
@login_required
def send_message():
    if "chat_id" in request.form:
        chat_id = uuid.UUID(request.form["chat_id"])
        is_new_chat_id = False
    else:
        chat_id = uuid.uuid4()
        is_new_chat_id = True

    username = session["username"]
    message = request.form["message"]
    history = (
        ChatHistory.select()
        .where(
            (ChatHistory.user == username) & (ChatHistory.chat_id == chat_id)
        )
        .order_by(ChatHistory.message_id)
    )

    if not history:
        chat_title = message[:32]
    else:
        chat_title = history[0].chat_title

    ChatHistory.create(
        user=username,
        chat_id=chat_id,
        chat_title=chat_title,
        message=json.dumps({"role": "user", "content": message}),
        created_at=datetime.now(),
    )
    history = [json.loads(h.message) for h in history]
    history.append({"role": "user", "content": message})

    def generate():
        if is_new_chat_id:
            yield json.dumps({"event": "chat_id", "data": str(chat_id)}) + "\n"

        stream = client.chat.completions.create(
            extra_body={},
            model="deepseek/deepseek-chat:free",
            messages=history,
            stream=True,
        )

        assistant_response = ""
        for chunk in stream:
            content = chunk.choices[0].delta.content or ""
            assistant_response += content
            yield json.dumps({"event": "message", "data": content}) + "\n"

        ChatHistory.create(
            user=username,
            chat_id=chat_id,
            chat_title=chat_title,
            message=json.dumps({"role": "assistant", "content": assistant_response}),
            created_at=datetime.now(),
        )

    return Response(generate(), mimetype="text/event-stream")


@app.route("/new_chat")
@login_required
def new_chat():
    return redirect(url_for("ai_chatbot"))


@app.route("/ai_chatbot")
@login_required
def ai_chatbot():
    chats = (
        ChatHistory.select(
            ChatHistory.chat_id, ChatHistory.chat_title, ChatHistory.created_at
        )
        .where(ChatHistory.user == session["username"])
        .group_by(ChatHistory.chat_id)
        .order_by(ChatHistory.created_at.desc())
    )
    chats = [
        {"chat_id": chat.chat_id, "chat_title": chat.chat_title, "created_at": chat.created_at}
        for chat in chats
    ]

    chat_id = request.args.get("chat_id")
    if chat_id:
        chat_id = uuid.UUID(chat_id)
        messages = (
            ChatHistory.select()
            .where(
                (ChatHistory.user == session["username"])
                & (ChatHistory.chat_id == chat_id)
            )
            .order_by(ChatHistory.message_id)
        )

        if not messages:
            return redirect(url_for("ai_chatbot"))

        history = [json.loads(msg.message) for msg in messages]
    else:
        history = []

    return render_template("ai_chatbot.html", chats=chats, history=history)


@app.route("/homepage")
def home():
    if "username" in session:
        return render_template("homepage.html", username=session["username"])
    return redirect(url_for("welcome"))


@app.route("/dashboard")
def dashboard():
    data_invest = DataInvestment.select().where(DataInvestment.user == session['username'])
    data_overview = DataOverview.select().where(DataOverview.user == session['username'])
    timestamp1 = np.random.randint(1, 1000000)
    timestamp2 = np.random.randint(1, 1000000)
    invest_totals = {
        "Bonds": 0,
        "ETF": 0,
        "Mutual Fund": 0,
        "Stock": 0  
    }
    for invest in data_invest:
        invest_totals[invest.invest_type] += invest.amount
    
    return render_template("dashboard.html", investment=data_invest, invest_totals=invest_totals, overview=data_overview,timestamp1=timestamp1,timestamp2=timestamp2)

@app.route("/view_overview")
def view_overview():
    overview = DataOverview.select().where(DataOverview.user == session["username"])

    fig, ax = plt.subplots(figsize=(10, 6))
    
    bank_accounts={}
    for account in overview:
        if account.bank_name not in bank_accounts:
            bank_accounts[account.bank_name] = {}
            
        bank_accounts[account.bank_name][account.account_type] = account.balance


    index = np.arange(len(bank_accounts))
    bottom = np.zeros(len(bank_accounts))
    
    for i, (bank, data) in enumerate(bank_accounts.items()):
        for j, (account, balance) in enumerate(data.items()):
            ax.bar(index[i], balance, 0.8, bottom=bottom[i], label=f'{bank} Account', color=np.random.rand(3,))
            bottom[i] += float(balance)
            ax.text(
                index[i],
                bottom[i] - float(balance) / 2,
                f'{account}',
                ha='center',
                va='center',
                color='white',
                fontweight='bold'
            )
            
    ax.set_ylabel('Total Balance')
    ax.set_title('Bank Account Balances Stacked by Bank')
    ax.set_xticks(index)
    ax.set_xticklabels(list(bank_accounts.keys()))
    
    img = BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)

    response = Response(img, mimetype='image/png')
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response

@app.route("/view_invest")
def view_invest():
    username = session['username']
    
    data = DataInvestment.select().where(DataInvestment.user == username)
    invest_groups = {}
    for invest in data:
        invest_type = invest.invest_type
        amount = invest.amount
        if invest_type not in invest_groups:
            invest_groups[invest_type] = 0
        invest_groups[invest_type] += amount   
    plt.figure(figsize=(8,8))
    plt.pie(invest_groups.values(), labels=invest_groups.keys(), autopct='%1.1f%%', startangle=140)
    plt.title(f'{username} Investment Distribution')
    
    img = BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)

    response = Response(img, mimetype='image/png')
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response

@app.route("/account/<int:account_id>")
def account_details(account_id):
    account = DataTransaction.select().where((DataTransaction.user == session["username"]) & (DataTransaction.bank_account_id == account_id))
    return render_template("account_info.html", account=account)


@app.route("/data")
def data():
    return render_template("data.html")

@app.route("/data_overview", methods=['POST'])
def data_overview():
    #if 'overview' not in request.files:
        #return redirect(request.url)
    
    file = request.files['overview']
    
    if file:
        file_content = file.stream.read().decode("utf-8-sig")
        csv_file = StringIO(file_content)
        csvreader = csv.DictReader(csv_file, delimiter=",")
        
        for line in csvreader:
            balance = float(line['Balance'].replace(',', ''))
            existing = DataOverview.select().where(DataOverview.account_id == int(line['Account ID']), DataOverview.user == session["username"]).first()
            if existing:
                existing.balance = balance
                existing.save()
                print(f"Updated Account ID: {int(line['Account ID'])} with new balance: {balance}")
            else:
                DataOverview.create(
                    user=session["username"],
                    account_id=int(line['Account ID']),
                    bank_name=line['Bank Name'],
                    bank_name_short=line['Bank Name (Short)'],
                    account_type=line['Account Type'],
                    balance=balance
                )
            
    data_overviews = DataOverview.select().where(DataOverview.user == session['username'])

    if data_overviews.exists():
        for data in data_overviews:
            print(f"Account ID: {data.account_id}, Bank Name: {data.bank_name}, Balance: {data.balance}")
    else:
        print("No data available in DataOverview.")
    
    return 'CSV data has been uploaded and processed'

@app.route("/data_transaction", methods=['POST'])
def data_transaction():
    #if 'overview' not in request.files:
        #return redirect(request.url)
    
    file = request.files['transaction']
    
    if file:
        file_content = file.stream.read().decode("utf-8-sig")
        csv_file = StringIO(file_content)
        csvreader = csv.DictReader(csv_file, delimiter=",")
        
        print(f"CSV Headers: {csvreader.fieldnames}")
        
        for line in csvreader:
            try:
                bank_account = DataOverview.get(DataOverview.account_id == int(line['Bank Account ID']))
                print(bank_account)
                DataTransaction.create(
                user=session["username"],
                bank_account_id=bank_account,
                date=datetime.strptime(line['Date'], '%Y-%m-%d').date(),
                description=line['Description'],
                amount=float(line['Amount'].replace(',', '')),
            )
            except DataOverview.DoesNotExist:
                print(f"Account ID {line['Bank Account ID']} does not exist in DataOverview. Skipping transaction.")
                continue 
            
    transactions = DataTransaction.select().where(DataTransaction.user == session["username"])

        # Print out the records from the database
    print("Added Records in Database:")
    for transaction in transactions:
        print(f"Account ID: {transaction.bank_account_id.account_id}, Date: {transaction.date}, "
            f"Description: {transaction.description}, Amount: {transaction.amount}")

    
    return 'CSV data has been uploaded and processed'

@app.route("/data_invest", methods=['POST'])
def data_invest():
    #if 'overview' not in request.files:
        #return redirect(request.url)
    
    file = request.files['invest']
    
    if file:
        file_content = file.stream.read().decode("utf-8-sig")
        csv_file = StringIO(file_content)
        csvreader = csv.DictReader(csv_file, delimiter=",")
        
        print(f"CSV Headers: {csvreader.fieldnames}")
        
        for line in csvreader:
            amount = float(line['Amount Invested'].replace(',', ''))
            existing = DataInvestment.select().where(DataInvestment.name == line['Investment Name'], DataInvestment.user == session["username"]).first()
            if existing:
                existing.amount = amount
                existing.date = datetime.strptime(line['Investment Date'], '%Y-%m-%d').date()
                existing.save()
                print(f"Updated Investment Named: {line['Investment Name']} with new balance: {amount}")
            else:
                DataInvestment.create(
                    user=session["username"],
                    name=line['Investment Name'],
                    invest_type=line['Investment Type'],
                    amount=amount,
                    date=datetime.strptime(line['Investment Date'], '%Y-%m-%d').date(),
                )

            
    invest = DataInvestment.select().where(DataInvestment.user == session["username"])

        # Print out the records from the database
    print("Added Records in Database:")
    for investment in invest:
        print(f"Date: {investment.date}, "
            f"Name: {investment.name}, Amount: {investment.amount}")

    
    return 'CSV data has been uploaded and processed'

@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404

if __name__ == "__main__":
    app.run(debug=True)
