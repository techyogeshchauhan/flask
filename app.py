from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_mysqldb import MySQL
from google.oauth2 import id_token
from google.auth.transport import requests
import os

app = Flask(__name__)

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'Bot'
mysql = MySQL(app)

# Google OAuth2 Configuration
CLIENT_ID = "1058099786136-rduhgd2e6rnln5op6romet21vcshjrb3.apps.googleusercontent.com"
app.secret_key = os.urandom(24)  # Secret key for session management

@app.route('/')
def index():
    if 'user' in session:
        return render_template('dashboard.html', user=session['user'])
    return render_template('index.html')

@app.route('/signup', methods=['POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']  # Hash password in production
        email = request.form['email']

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s OR username = %s", (email, username))
        existing_user = cur.fetchone()

        if existing_user:
            flash("User with that email or username already exists.", "danger")
            return redirect(url_for('index'))

        cur.execute("INSERT INTO users(username, email, password) VALUES (%s, %s, %s)", (username, email, password))
        mysql.connection.commit()
        cur.close()

        flash("Signup successful! Please login.", "success")
        return redirect(url_for('index'))

    return redirect(url_for('index'))

@app.route('/login', methods=['POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s AND password = %s", (email, password))
        user = cur.fetchone()
        cur.close()

        if user:
            session['user'] = {'id': user[0], 'username': user[1], 'email': user[2]}
            return redirect(url_for('index'))
        else:
            flash("Invalid email or password", "danger")
            return redirect(url_for('index'))

    return redirect(url_for('index'))

@app.route('/google_login')
def google_login():
    return render_template('google_login.html', client_id=CLIENT_ID)

@app.route('/google_auth', methods=['POST'])
def google_auth():
    try:
        token = request.json['token']
        idinfo = id_token.verify_oauth2_token(token, requests.Request(), CLIENT_ID)

        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValueError('Wrong issuer.')

        user_email = idinfo['email']
        user_name = idinfo['name']

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s", (user_email,))
        user = cur.fetchone()

        if not user:
            cur.execute("INSERT INTO users (username, email) VALUES (%s, %s)", (user_name, user_email))
            mysql.connection.commit()
            cur.execute("SELECT * FROM users WHERE email = %s", (user_email,))
            user = cur.fetchone()

        session['user'] = {'id': user[0], 'username': user[1], 'email': user[2]}
        return jsonify({'status': 'success'}), 200

    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
