# BC3415-Group3

## Usage

### Secret Key
To run the app and use the `ai_chatbot` and `dashboard` features, you need to create a `.env` file in the root directory of the project and fill it with the following:
```bash
# .env
FLASK_SECRET_KEY=<your_random_flask_session_secret_key>
GEMINI_API_KEY=<your_google_ai_studio_api_key>
API_KEY=<your_financial_modeling_prep_api_key>
```

Replace `<your_random_flask_session_secret_key>` with a random string of your choice. You can generate a random hex string using the following command in Python:
```python
import secrets

random_bytes = secrets.token_bytes(24)
print(random_bytes.hex())
```

Replace `<your_google_ai_studio_api_key>` with your Google AI Studio API key. Follow the "Get API Key" button at https://aistudio.google.com/apikey to create this API key.

Replace `<your_financial_modeling_prep_api_key>` with your Financial Modeling Prep API key. Sign up and select the Free plan at https://site.financialmodelingprep.com/ before creating this API key.

### Installation
Install the required packages of the Flask app itself by running the following command:
```bash
pip install -r requirements.txt
```

### Development
To run the Flask app in development mode, use the following command:
```bash
flask run
```

### Load Testing
To run the load test, you need to first install the required packages for the load test:

```bash
# Windows
pip install uvicorn locust

# MacOS
pip3 install uvicorn locust

# Linux
pip install gunicorn locust
```

Then, start up **TWO** different terminals, one for the Flask app and one for the load test.

In the first terminal, run the Flask app using the following command:
```bash
# Windows
cmd /c app_daemon_windows.bat

# MacOS
chmod +x ./app_daemon_mac.sh
./app_daemon_mac.sh

# Linux
chmod +x ./app_daemon_linux.sh
bash ./app_daemon_linux.sh
```

In the second terminal, run the load test using the following command:
```bash
locust -f locustfile.py
```
This will start the Locust web interface at `http://localhost:8089`, where you can configure the number of users and the hatch rate.

In case you find any errors while running the flask app, you can try running it using `waitress` instead:
```bash
pip install waitress
```

Then, run the app using the following command:
```bash
# Windows
cmd /c app_daemon_windows.bat waitress

# MacOS
chmod +x ./app_daemon_mac.sh
./app_daemon_mac.sh waitress

# Linux
chmod +x ./app_daemon_linux.sh
bash ./app_daemon_linux.sh waitress
```
