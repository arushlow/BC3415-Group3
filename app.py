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
    return render_template('more.html')

@app.route('/update_account', methods=['GET', 'POST'])
def update_account():
    if 'username' not in session:
        return redirect(url_for('login'))  # Redirect if not logged in
    
    if request.method == 'POST':
        new_username = request.form.get('new_username')
        new_password = request.form.get('new_password')
        # Add logic to update user info in the database
        session['username'] = new_username  # Update session with new username
        return redirect(url_for('home'))  # Redirect back to homepage

    return render_template('update_account.html')

@app.route('/logout')
def logout():
    session.pop('username', None)  # Clear session
    return redirect(url_for('welcome'))

if __name__ == '__main__':
    app.run(debug=True)
