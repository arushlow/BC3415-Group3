from flask import Flask, render_template, redirect, url_for, request, session

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Set a secret key for session management

@app.route('/')
def welcome():
    return render_template('welcome.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Implement your login logic here
        username = request.form['username']
        password = request.form['password']
        # Assuming login is successful, set session
        session['username'] = username
        return redirect(url_for('home'))
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # Implement your signup logic here
        username = request.form['username']
        password = request.form['password']
        # Assuming signup is successful, set session
        session['username'] = username
        return redirect(url_for('home'))
    return render_template('signup.html')

@app.route('/homepage')
def home():
    if 'username' in session:
        return render_template('homepage.html', username=session['username'])
    return redirect(url_for('welcome'))

@app.route('/features')
def features():
    return render_template('features.html')

@app.route('/more')
def more():
    return render_template('more.html')  # Your existing More Options page

@app.route('/change_login_info')
def change_login_info():
    return render_template('change_login_info.html')

@app.route('/change_username', methods=['GET', 'POST'])
def change_username():
    if request.method == 'POST':
        # Logic to change the username
        new_username = request.form['new_username']
        # Update the username in your database
        return redirect(url_for('home'))  # Redirect after changing username
    return render_template('change_username.html')  # Create a change_username.html

@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if request.method == 'POST':
        # Logic to change the password
        new_password = request.form['new_password']
        # Update the password in your database
        return redirect(url_for('home'))  # Redirect after changing password
    return render_template('change_password.html')  # Create a change_password.html


@app.route('/logout')
def logout():
    session.pop('username', None)  # Clear session
    return redirect(url_for('welcome'))

if __name__ == '__main__':
    app.run(debug=True)


