import asyncio
import atexit
import csv
import json
import logging
import os
import threading
import time
import uuid
from datetime import datetime
from functools import wraps
from io import BytesIO, StringIO
import requests

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from dotenv import load_dotenv
from flask import (
    Flask,
    Response,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from flask_bcrypt import Bcrypt
from openai import OpenAI
from peewee import IntegrityError, OperationalError
from werkzeug.serving import is_running_from_reloader

from mcp_server.client import MCPClient
from model import (
    ChatHistory,
    DataInvestment,
    DataOverview,
    DataTransaction,
    User,
    create_tables,
    database,
)
from simulation import simulate_retirement


### Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


### Database Configuration
def get_db():
    if database.is_closed():
        database.connect()
    return database

def db_retry(max_attempts=3, retry_delay=0.5):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempts = 0
            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except OperationalError as e:
                    if "database is locked" in str(e) and attempts < max_attempts - 1:
                        attempts += 1
                        logging.warning(f"Database locked, retrying ({attempts}/{max_attempts})...")
                        time.sleep(retry_delay)
                        if not database.is_closed():
                            database.close()
                        database.connect()
                    else:
                        raise
        return wrapper
    return decorator

create_tables()


### Chatbot Configuration
load_dotenv()
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)


### MCP Client Configuration
mcp_client = MCPClient()
mcp_client.start_background_loop()

def init_mcp_client():
    try:
        mcp_client.run_in_background(mcp_client.connect_to_server({
            "command": "python",
            "args": ["mcp_server/finance.py"],
            "cwd": os.path.dirname(__file__),
            "env": None
        }))
        logging.info("MCP client initialized successfully")
    except Exception as e:
        logging.info(f"Failed to initialize MCP client: {e}")

if not is_running_from_reloader():
    threading.Timer(5.0, init_mcp_client).start()

@atexit.register
def cleanup_resources():
    if mcp_client:
        logging.info("Cleaning up MCP client...")
        try:
            def cleanup_background():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(mcp_client.cleanup_session())
                loop.close()
            
            cleanup_thread = threading.Thread(target=cleanup_background)
            cleanup_thread.start()
            cleanup_thread.join(timeout=5.0)
            
            mcp_client.stop_background_loop()
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")


### Flask Application Configuration
REQUEST_TIMEOUT = 30
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")
bcrypt = Bcrypt(app)


@app.before_request
def before_request():
    if request.path != '/send_message':
        request.environ['REQUEST_TIMEOUT'] = REQUEST_TIMEOUT
    get_db()


@app.after_request
def after_request(response):
    if not database.is_closed():
        database.close()
    return response


@app.teardown_request
def teardown_request(exception):
    if not database.is_closed():
        database.close()
    
    if exception:
        logging.error(f"Request error: {exception}")


@app.errorhandler(Exception)
def handle_exception(e):
    logging.error(f"Unhandled exception: {str(e)}", exc_info=True)
    return jsonify({"error": "Internal Server Error, please try again later."}), 500


def login_required(f):
    @wraps(f)
    def inner(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return inner


def convert_tool_format(tool):
    converted_tool = {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": {
                "type": "object",
                "properties": tool.inputSchema["properties"],
                "required": tool.inputSchema["required"]
            }
        }
    }
    return converted_tool


@app.route('/favicon.ico') 
def favicon(): 
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')


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
            logging.error(e)
            return render_template(
                "change_username.html", error="An error occurred, please try again"
            )

        session["username"] = new_username
        return redirect(url_for("home"))
    return render_template("change_username.html")


@app.route("/change_password", methods=["GET", "POST"])
@login_required
@db_retry(max_attempts=5, retry_delay=1.0)
def change_password():
    if request.method == "POST":
        new_password = request.form["new_password"]

        try:
            if database.is_closed():
                database.connect()
            
            with database.atomic() as transaction:
                try:
                    user = User.get(User.username == session["username"])
                    user.password = bcrypt.generate_password_hash(new_password).decode("utf-8")
                    user.save()
                except Exception as e:
                    transaction.rollback()
                    logging.error(f"Failed to change password: {e}")
                    return render_template("change_password.html", error="Failed to change password, please try again")
            
            return redirect(url_for("home"))
        except Exception as e:
            logging.error(f"Database error during password change: {e}")
            return render_template("change_password.html", error="Internal Server Error, please try again later.")
        finally:
            if not database.is_closed():
                database.close()
    
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
    try:
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
    except Exception as e:
        logging.error(f"Simulation error: {e}", exc_info=True)
        return jsonify({"error": "Error in running scenario simulation"}), 500


@app.route("/scenario_simulation")
@login_required
def scenario_simulation():
    return render_template("scenario_simulation.html")


@app.route("/ai_generated_adjustments", methods=["GET", "POST"])
@login_required
def ai_generated_adjustments():
    if request.method == "POST":
        try:
            data = request.get_json()
            logging.debug(f"Received data: {data}")

            if not data:
                logging.error("No data received")
                return jsonify({"error": "No data received"}), 400

            # Extract values safely
            try:
                income = float(data.get("income", 0))
                expenses = float(data.get("expenses", 0))
                savings = float(data.get("savings", 0))
                investments = float(data.get("investments", 0))
                debt = float(data.get("debt", 0))
            except ValueError as ve:
                logging.error(f"Invalid numeric values: {ve}")
                return jsonify({"error": "Invalid numeric values provided"}), 400

            # Risk Tolerance Mapping
            risk_tolerance = data.get("risk_tolerance", "medium")
            risk_mapping = {
                "low": "Increase bond allocation, minimize high-risk assets",
                "medium": "Balanced stock & bond mix with ETFs",
                "high": "Higher stock allocation, potential for crypto or startups"
            }
            investment_strategy = risk_mapping.get(risk_tolerance, "Balanced portfolio")

            # Savings Plan Logic - More dynamic
            savings_suggestion = 0
            if expenses > income:
                savings_suggestion = "Reduce expenses to save more."
            else:
                suggested_savings_percentage = 0.20  # Default 20% savings suggestion
                if income > 5000:
                    suggested_savings_percentage = 0.25  # Suggest 25% savings for higher income
                savings_suggestion = f"Save at least {income * suggested_savings_percentage} SGD per month."

            # Debt Repayment Strategy - More specific
            debt_strategy = ""
            if debt > 0:
                # Calculate debt-to-income ratio for prioritizing strategy
                debt_to_income_ratio = debt / income
                if debt_to_income_ratio > 0.5:
                    debt_strategy = "You have a high debt-to-income ratio. Prioritize paying off high-interest debts first."
                else:
                    debt_strategy = "Focus on paying off high-interest debt, then consider investing."
            else:
                debt_strategy = "No major debts, focus on building investments."

            # Projected Growth Estimate - More personalized
            projected_growth = 0
            if investments > 0 or savings > 0:
                return_rate = 0.05  # Default 5% return rate
                if risk_tolerance == "high":
                    return_rate = 0.08  # Higher return rate for high-risk tolerance
                elif risk_tolerance == "low":
                    return_rate = 0.03  # Lower return rate for low-risk tolerance
                projected_growth = round((investments + savings) * return_rate, 2)

            response = {
                "investment_strategy": investment_strategy,
                "savings_plan": savings_suggestion,
                "debt_strategy": debt_strategy,
                "projected_growth": projected_growth
            }
            logging.debug(f"Response: {response}")

            return jsonify(response)

        except Exception as e:
            logging.error(f"Error processing request: {e}", exc_info=True)
            return jsonify({"error": "An error occurred while processing your request."}), 500
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

    history = [json.loads(h.message) for h in history]
    history.append({"role": "user", "content": message})

    try:
        response = mcp_client.list_tools()
        available_tools = [convert_tool_format(tool) for tool in response.tools]
    except Exception as e:
        logging.error(f"Error getting tools: {e}")
        available_tools = []

    def generate():
        if is_new_chat_id:
            yield json.dumps({"event": "chat_id", "data": str(chat_id)}) + "\n"

        stream = client.chat.completions.create(
            extra_body={},
            model="google/gemini-2.5-pro-exp-03-25:free",
            messages=history,
            tools=available_tools,
            stream=True,
        )

        assistant_response = ""
        tool_call_ids = []
        tool_call_parts = {}

        for chunk in stream:
            if chunk.choices[0].delta.tool_calls:
                tool_calls = chunk.choices[0].delta.tool_calls
                for tool_call in tool_calls:
                    tool_call_id = tool_call.id
                    
                    if tool_call_id not in tool_call_parts:
                        tool_call_ids.append(tool_call_id)
                        tool_call_parts[tool_call_id] = {
                            "name": "",
                            "arguments": "",
                            "complete": False
                        }
                        yield json.dumps({"event": "tool_call_start", "data": tool_call_id}) + "\n"
                    
                    if tool_call.function.name:
                        tool_call_parts[tool_call_id]["name"] += tool_call.function.name
                        yield json.dumps({
                            "event": "tool_call_update", 
                            "data": {
                                "id": tool_call_id,
                                "type": "name",
                                "content": tool_call.function.name
                            }
                        }) + "\n"
                    
                    if tool_call.function.arguments:
                        tool_call_parts[tool_call_id]["arguments"] += tool_call.function.arguments
                        yield json.dumps({
                            "event": "tool_call_update", 
                            "data": {
                                "id": tool_call_id,
                                "type": "arguments",
                                "content": tool_call.function.arguments
                            }
                        }) + "\n"
                        
                        args_str = tool_call_parts[tool_call_id]["arguments"].strip()
                        if args_str.endswith("}"):
                            try:
                                json.loads(args_str)
                                tool_call_parts[tool_call_id]["complete"] = True
                            except json.JSONDecodeError:
                                pass

            content = chunk.choices[0].delta.content or ""
            if content:
                assistant_response += content
                yield json.dumps({"event": "message", "data": content}) + "\n"

        if assistant_response:
            ChatHistory.create(
                user=username,
                chat_id=chat_id,
                chat_title=chat_title,
                message=json.dumps({"role": "user", "content": message}),
                created_at=datetime.now(),
            )

            ChatHistory.create(
                user=username,
                chat_id=chat_id,
                chat_title=chat_title,
                message=json.dumps({"role": "assistant", "content": assistant_response}),
                created_at=datetime.now(),
            )

        for tool_id in tool_call_ids:
            tool_name = tool_call_parts[tool_id]["name"]
            tool_args_str = tool_call_parts[tool_id]["arguments"]
            
            try:
                tool_args = json.loads(tool_args_str)
                
                try:
                    tool_result = mcp_client.call_tool(tool_name, tool_args)
                    
                    yield json.dumps({
                        "event": "tool_result", 
                        "data": {
                            "id": tool_id,
                            "result": tool_result.content[0].text
                        }
                    }) + "\n"
                    
                    tool_call_message = {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": tool_id,
                                "type": "function",
                                "function": {
                                    "name": tool_name,
                                    "arguments": tool_args_str
                                }
                            }
                        ]
                    }
                    
                    tool_result_message = {
                        "role": "tool",
                        "tool_call_id": tool_id,
                        "content": tool_result.content[0].text
                    }

                except Exception as e:
                    error_message = f"Error calling tool: {str(e)}"
                    logging.error(f"Error calling tool {tool_name}: {e}")
                    
                    yield json.dumps({
                        "event": "tool_result", 
                        "data": {
                            "id": tool_id,
                            "error": error_message
                        }
                    }) + "\n"
                    
                    tool_call_message = {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": tool_id,
                                "type": "function",
                                "function": {
                                    "name": tool_name,
                                    "arguments": tool_args_str
                                }
                            }
                        ]
                    }
                    
                    tool_result_message = {
                        "role": "tool",
                        "tool_call_id": tool_id,
                        "content": json.dumps({"error": error_message})
                    }
                    
            except json.JSONDecodeError as je:
                error_message = f"Invalid tool arguments: {str(je)}"
                logging.error(f"Invalid tool arguments for {tool_name}: {je}")
                
                yield json.dumps({
                    "event": "tool_result", 
                    "data": {
                        "id": tool_id,
                        "error": error_message
                    }
                }) + "\n"
                
                tool_call_message = {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": tool_id,
                            "type": "function",
                            "function": {
                                "name": tool_name,
                                "arguments": tool_args_str
                            }
                        }
                    ]
                }
                
                tool_result_message = {
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "content": json.dumps({"error": error_message})
                }

            ChatHistory.create(
                user=username,
                chat_id=chat_id,
                chat_title=chat_title,
                message=json.dumps(tool_call_message),
                created_at=datetime.now(),
            )

            ChatHistory.create(
                user=username,
                chat_id=chat_id,
                chat_title=chat_title,
                message=json.dumps(tool_result_message),
                created_at=datetime.now(),
            )
            
            history.append(tool_call_message)
            history.append(tool_result_message)

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

        history = []
        for msg in messages:
            msg_data = json.loads(msg.message)
            
            if msg_data.get('role') == 'tool':
                try:
                    content = msg_data.get('content', '')
                    if isinstance(content, str):
                        try:
                            content_obj = json.loads(content)
                            msg_data['content'] = json.dumps(content_obj)
                        except json.JSONDecodeError:
                            pass
                except Exception as e:
                    logging.error(f"Error processing tool result: {e}")
            
            history.append(msg_data)
    else:
        history = []

    return render_template("ai_chatbot.html", chats=chats, history=history)

@app.route("/clear_chat_history", methods=["POST"])
@login_required
def clear_chat_history():
    try:
        username = session["username"]
        with database.atomic():
            deleted_count = ChatHistory.delete().where(
                ChatHistory.user == username
            ).execute()
        
        return jsonify({"success": True, "message": f"Deleted {deleted_count} messages"}), 200
    except Exception as e:
        logging.error(f"Error clearing chat history: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/homepage")
def home():
    if "username" in session:
        return render_template("homepage.html", username=session["username"])
    return redirect(url_for("welcome"))


@app.route("/dashboard")
@login_required
def dashboard():
    user = User.get(User.username == session["username"])
    data_invest = DataInvestment.select().where(DataInvestment.user == user)
    data_overview = DataOverview.select().where(DataOverview.user == user)
    
    
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
        
    # Pass flag to show graph based on button click
    show_bank_chart = request.args.get('show_bank_chart', False)
    show_invest_chart = request.args.get('show_invest_chart', False)
    
    return render_template("dashboard.html", investment=data_invest, invest_totals=invest_totals, overview=data_overview,timestamp1=timestamp1,timestamp2=timestamp2, show_bank_chart=show_bank_chart, show_invest_chart=show_invest_chart)

@app.route("/view_overview")
@login_required
def view_overview():
    user = User.get(User.username == session["username"])
    overview = DataOverview.select().where(DataOverview.user == user)

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
            ax.bar(index[i], balance, 0.8, bottom=bottom[i], label=f'{account}', color=np.random.rand(3,))
            bottom[i] += float(balance)
            ax.text(
                index[i],
                bottom[i] - float(balance) / 2,
                f'${balance}',
                ha='center',
                va='center',
                color='white',
                fontweight='bold',
                fontsize=7,
            )
            
    ax.legend(title="Account Types")
    ax.set_ylabel('Total Balance')
    ax.set_title('Bank Account Balances Stacked by Bank')
    ax.set_xticks(index)
    ax.set_xticklabels(list(bank_accounts.keys()))
    
    img = BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)

    plt.close(fig)

    response = Response(img.getvalue(), mimetype='image/png')
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response

@app.route("/view_invest")
@login_required
def view_invest():
    user = User.get(User.username == session["username"])
    
    data = DataInvestment.select().where(DataInvestment.user == user)
    
    invest_groups = {}
    for invest in data:
        invest_type = invest.invest_type
        amount = invest.amount
        if invest_type not in invest_groups:
            invest_groups[invest_type] = 0
        invest_groups[invest_type] += amount   
    fig = plt.figure(figsize=(8, 8))
    plt.pie(invest_groups.values(), labels=invest_groups.keys(), autopct='%1.1f%%', startangle=140)
    plt.title(f'{session["username"]} Investment Distribution')
    
    img = BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)

    plt.close(fig)

    response = Response(img.getvalue(), mimetype='image/png')
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response

@app.route("/account/<int:account_id>")
@login_required
def account_details(account_id):
    user = User.get(User.username == session["username"])
    account = DataTransaction.select().where((DataTransaction.user == user) & (DataTransaction.bank_account_id == account_id))
    return render_template("account_info.html", account=account)

@app.route("/invest/<ticker>")
@login_required
def invest_details(ticker):
    user = User.get(User.username == session["username"])
    account = DataInvestment.select().where((DataInvestment.user == user) & (DataInvestment.ticker == ticker))
    url = f"https://financialmodelingprep.com/stable/profile?symbol={ticker}&apikey={os.getenv('API_KEY')}"
    response = requests.get(url)
    stock = response.json()
    data = stock[0]
    
    change = {}
    for tick in account:
        changing = {}
        changing['growth'] = round(((data['price'] - float(tick.price))/float(tick.price))*100, 2)
        changing['increase'] = round((data['price'] - float(tick.price)) * tick.quantity, 2)
        changing['current'] = round(data['price'] * tick.quantity, 2)
        change[tick.date] = changing
    return render_template("invest_info.html", account=account, stock=data, change=change)


@app.route("/data")
@login_required
def data():
    return render_template("data.html")

@app.route("/data_overview", methods=['POST'])
@login_required
@db_retry(max_attempts=3)
def data_overview():
    try:
        # if 'overview' not in request.files:
        #     return redirect(request.url)
        
        file = request.files['overview']
        
        if file:
            user = User.get(User.username == session["username"])
            
            file_content = file.stream.read().decode("utf-8-sig")
            csv_file = StringIO(file_content)
            csvreader = csv.DictReader(csv_file, delimiter=",")
            
            required_fields = ["Account ID", "Bank Name", "Bank Name (Short)", "Account Type", "Balance"]
            if not csvreader.fieldnames or not all(field in csvreader.fieldnames for field in required_fields):
                logging.error(f"Incorrect CSV format - Required columns: {required_fields}, Received columns: {csvreader.fieldnames}")
                return jsonify({"error": "Missing required columns in CSV"}), 400
            
            for line in csvreader:
                balance = float(line['Balance'].replace(',', ''))
                existing = DataOverview.select().where(
                    (DataOverview.account_id == int(line['Account ID'])) & 
                    (DataOverview.user == user)
                ).first()

                if existing:
                    existing.balance = balance
                    existing.save()
                    logging.debug(f"Updated Account ID: {int(line['Account ID'])} with new balance: {balance}")
                else:
                    DataOverview.create(
                        user=user,
                        account_id=int(line['Account ID']),
                        bank_name=line['Bank Name'],
                        bank_name_short=line['Bank Name (Short)'],
                        account_type=line['Account Type'],
                        balance=balance
                    )
                
        data_overviews = DataOverview.select().where(DataOverview.user == user)

        if data_overviews.exists():
            for data in data_overviews:
                logging.debug(f"Account ID: {data.account_id}, Bank Name: {data.bank_name}, Balance: {data.balance}")
        else:
            logging.debug("No data available in DataOverview.")
                    
    except KeyError as ke:
        logging.error(f"Missing required column in CSV - {ke}", exc_info=True)
        return jsonify({"error": f"Missing required column in CSV - {ke}"}), 400
    except Exception as e:
        logging.error(f"Error in data_overview: {e}", exc_info=True)
        return jsonify({"error": "Error in processing Overview data"}), 500
    return 'CSV data has been uploaded and processed'

@app.route("/data_transaction", methods=['POST'])
@login_required
@db_retry(max_attempts=3)
def data_transaction():
    try:
        file = request.files['transaction']
        
        if file:
            user = User.get(User.username == session["username"])
            
            file_content = file.stream.read().decode("utf-8-sig")
            csv_file = StringIO(file_content)
            csvreader = csv.DictReader(csv_file, delimiter=",")
            
            logging.debug(f"CSV Headers: {csvreader.fieldnames}")
            
            for line in csvreader:
                try:
                    bank_account = DataOverview.get(
                        (DataOverview.account_id == int(line['Bank Account ID'])) & 
                        (DataOverview.user == user)
                    )
                    logging.debug(bank_account)
                    DataTransaction.create(
                    user=user,
                    bank_account_id=bank_account,
                    date=datetime.strptime(line['Date'], '%Y-%m-%d').date(),
                    description=line['Description'],
                    amount=float(line['Amount'].replace(',', '')),
                )
                except DataOverview.DoesNotExist:
                    logging.error(f"Account ID {line['Bank Account ID']} does not exist in DataOverview. Skipping transaction.")
                    continue 
                
        transactions = DataTransaction.select().where(DataTransaction.user == user)

        # Print out the records from the database
        logging.debug("Added Records in Database:")
        for transaction in transactions:
            logging.debug(f"Account ID: {transaction.bank_account_id.account_id}, Date: {transaction.date}, "
                          f"Description: {transaction.description}, Amount: {transaction.amount}")

    except Exception as e:
        logging.error(f"Error in data_transaction: {e}", exc_info=True)
        return jsonify({"error": "Error in processing Transaction data"}), 500
    return 'CSV data has been uploaded and processed'

@app.route("/data_invest", methods=['POST'])
@login_required
@db_retry(max_attempts=3)
def data_invest():
    try:
        file = request.files['invest']
        
        if file:
            user = User.get(User.username == session["username"])
            
            file_content = file.stream.read().decode("utf-8-sig")
            csv_file = StringIO(file_content)
            csvreader = csv.DictReader(csv_file, delimiter=",")
            
            logging.debug(f"CSV Headers: {csvreader.fieldnames}")
            
            for line in csvreader:
                price = line['Price Bought']
                price=float(price) if price != "N/A" else None
                quantity=int(line['Quantity']) if line['Quantity'] != "N/A" else None
                if price is not None or quantity is not None:
                    amount = round(float(price*quantity), 2)
                else:
                    amount = round(float(line['Amount Invested'].replace(',', '')), 2)
                existing = (
                    DataInvestment.select()
                    .where(
                        (DataInvestment.name == line["Investment Name"]) &
                        (DataInvestment.user == user)
                    )
                    .first()
                )
                if existing:
                    existing.amount = amount
                    existing.date = datetime.strptime(line['Investment Date'], '%Y-%m-%d').date()
                    existing.save()
                    logging.debug(f"Updated Investment Named: {line['Investment Name']} with new balance: {amount}")
                else:
                    DataInvestment.create(
                        user=user,
                        name=line['Investment Name'],
                        ticker=line['Ticker Name'],
                        invest_type=line['Investment Type'],
                        price=price,
                        quantity=quantity,
                        amount=amount,
                        date=datetime.strptime(line['Investment Date'], '%Y-%m-%d').date(),
                    )

                
        invest = DataInvestment.select().where(DataInvestment.user == user)

        # Print out the records from the database
        logging.debug("Added Records in Database:")
        for investment in invest:
            logging.debug(f"Date: {investment.date}, Name: {investment.name}, Amount: {investment.amount}")

    except Exception as e:
        logging.error(f"Error in data_invest: {e}", exc_info=True)
        return jsonify({"error": "Error in processing Investment data: " + str(e)}), 500
    return 'CSV data has been uploaded and processed'

@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404

if __name__ == "__main__":
    app.run(debug=True, threaded=True)
