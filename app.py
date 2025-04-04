import asyncio
import atexit
import json
import logging
import os
import threading
import uuid
from datetime import datetime
from functools import wraps

from dotenv import load_dotenv
from flask import (
    Flask,
    Response,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_bcrypt import Bcrypt
from openai import OpenAI
from peewee import IntegrityError

from mcp_server.client import MCPClient
from model import ChatHistory, User, create_tables, database
from simulation import simulate_retirement

create_tables()
load_dotenv()
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

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
        print("MCP client initialized successfully")
    except Exception as e:
        print(f"Failed to initialize MCP client: {e}")

threading.Timer(1.0, init_mcp_client).start()

@atexit.register
def cleanup_resources():
    if mcp_client:
        print("Cleaning up MCP client...")
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
            print(f"Error during cleanup: {e}")

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
        print(f"Error getting tools: {e}")
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
                    print(f"Error calling tool {tool_name}: {e}")
                    
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
                print(f"Invalid tool arguments for {tool_name}: {je}")
                
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
                    print(f"Error processing tool result: {e}")
            
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


@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404

if __name__ == "__main__":
    app.run(debug=True)

