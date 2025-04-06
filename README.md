# BC3415-Group3

## Usage

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
cmd /c app_daemon.bat

# MacOS
chmod +x ./app_daemon.sh
./app_daemon.sh

# Linux
chmod +x ./app_daemon.sh
bash ./app_daemon.sh
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
cmd /c app_daemon.bat waitress

# MacOS
chmod +x ./app_daemon.sh
./app_daemon.sh waitress

# Linux
chmod +x ./app_daemon.sh
bash ./app_daemon.sh waitress
```
