from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_mysqldb import MySQL
from google.oauth2 import id_token
from google.auth.transport import requests
import os
import hashlib
from datetime import datetime
from functools import wraps
import openai  # Import OpenAI library

app = Flask(__name__)

# Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'Bot'
app.secret_key = os.urandom(24)

# Initialize MySQL
mysql = MySQL(app)

# Google OAuth2 Configuration
CLIENT_ID = "1058099786136-rduhgd2e6rnln5op6romet21vcshjrb3.apps.googleusercontent.com"

# OpenAI API Key
openai.api_key = 'AIzaSyDKRimFNnEy0tXt1T6kY_9B9BNqFshszKs'  # Replace with your OpenAI API key

# Helper Functions
def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('Please login first.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def init_db():
    """Initialize database tables"""
    cur = mysql.connection.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) NOT NULL,
            email VARCHAR(100) NOT NULL UNIQUE,
            password VARCHAR(255),
            google_id VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    mysql.connection.commit()
    cur.close()

# Initialize database when app starts
with app.app_context():
    init_db()

# OpenAI Chatbot Function
def ask_openai(prompt):
    """Send a prompt to OpenAI and get a response"""
    try:
        response = openai.Completion.create(
            engine="text-davinci-003",  # Use "gpt-3.5-turbo" for newer models
            prompt=prompt,
            max_tokens=150,  # Adjust based on the length of responses you want
            n=1,  # Number of responses to generate
            stop=None,  # Stop sequence (optional)
            temperature=0.7,  # Controls randomness (0 = deterministic, 1 = creative)
        )
        return response.choices[0].text.strip()
    except Exception as e:
        print(f"OpenAI API error: {str(e)}")
        return "Sorry, I encountered an error while processing your request."

# Routes
@app.route('/')
def index():
    """Home page route"""
    return render_template('index.html', user=session.get('user'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Dashboard page route"""
    return render_template('dashboard.html', user=session.get('user'))

@app.route('/chatbot', methods=['GET', 'POST'])
@login_required
def chatbot():
    """Chatbot interaction route"""
    if request.method == 'POST':
        user_input = request.form['user_input']
        response = ask_openai(user_input)
        return jsonify({'response': response})
    return render_template('chatbot.html', user=session.get('user'))

@app.route('/signup', methods=['POST'])
def signup():
    """Handle user signup"""
    if request.method == 'POST':
        try:
            # Get form data
            username = request.form['username']
            password = hash_password(request.form['password'])
            email = request.form['email']
            
            cur = mysql.connection.cursor()
            
            # Check for existing user
            cur.execute("SELECT * FROM users WHERE email = %s", (email,))
            existing_user = cur.fetchone()
            
            if existing_user:
                cur.close()
                flash("User with that email already exists.", "danger")
                return redirect(url_for('index'))
            
            # Insert new user
            cur.execute("""
                INSERT INTO users (username, email, password, created_at) 
                VALUES (%s, %s, %s, %s)
            """, (username, email, password, datetime.now()))
            
            mysql.connection.commit()
            cur.close()
            
            flash("Signup successful! Please login.", "success")
            return redirect(url_for('index'))
            
        except Exception as e:
            print(f"Signup error: {str(e)}")
            mysql.connection.rollback()
            flash(f"An error occurred during signup: {str(e)}", "danger")
            return redirect(url_for('index'))

@app.route('/login', methods=['POST'])
def login():
    """Handle user login"""
    if request.method == 'POST':
        try:
            email = request.form['email']
            password = hash_password(request.form['password'])
            
            cur = mysql.connection.cursor()
            cur.execute("SELECT * FROM users WHERE email = %s AND password = %s", (email, password))
            user = cur.fetchone()
            cur.close()
            
            if user:
                session['user'] = {
                    'id': user[0],
                    'username': user[1],
                    'email': user[2],
                    'created_at': user[5]
                }
                flash("Login successful!", "success")
                return redirect(url_for('dashboard'))
            else:
                flash("Invalid email or password", "danger")
                return redirect(url_for('index'))
                
        except Exception as e:
            print(f"Login error: {str(e)}")
            flash(f"An error occurred during login: {str(e)}", "danger")
            return redirect(url_for('index'))

@app.route('/google_auth', methods=['POST'])
def google_auth():
    """Handle Google OAuth authentication"""
    try:
        token = request.json['token']
        idinfo = id_token.verify_oauth2_token(token, requests.Request(), CLIENT_ID)

        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValueError('Wrong issuer.')

        google_id = idinfo['sub']
        user_email = idinfo['email']
        user_name = idinfo.get('name', user_email.split('@')[0])

        cur = mysql.connection.cursor()
        
        # Check if user exists
        cur.execute("SELECT * FROM users WHERE google_id = %s OR email = %s", (google_id, user_email))
        user = cur.fetchone()

        if not user:
            # Create new Google user
            cur.execute("""
                INSERT INTO users (username, email, google_id, created_at) 
                VALUES (%s, %s, %s, %s)
            """, (user_name, user_email, google_id, datetime.now()))
            mysql.connection.commit()
            
            # Get the newly created user
            cur.execute("SELECT * FROM users WHERE google_id = %s", (google_id,))
            user = cur.fetchone()

        session['user'] = {
            'id': user[0],
            'username': user[1],
            'email': user[2],
            'created_at': user[5]
        }
        
        cur.close()
        return jsonify({'status': 'success', 'redirect': url_for('dashboard')}), 200

    except Exception as e:
        print(f"Google auth error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/logout')
def logout():
    """Handle user logout"""
    session.pop('user', None)
    flash("Logged out successfully!", "success")
    return redirect(url_for('index'))

@app.route('/profile')
@login_required
def profile():
    """User profile page route"""
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE id = %s", (session['user']['id'],))
        user_data = cur.fetchone()
        cur.close()
        
        if user_data:
            user_info = {
                'id': user_data[0],
                'username': user_data[1],
                'email': user_data[2],
                'created_at': user_data[5],
                'is_google_user': bool(user_data[4])  # Check if google_id exists
            }
            return render_template('profile.html', user=user_info)
        else:
            flash("User not found.", "danger")
            return redirect(url_for('index'))
            
    except Exception as e:
        print(f"Profile error: {str(e)}")
        flash("An error occurred while loading profile.", "danger")
        return redirect(url_for('dashboard'))

@app.route('/settings')
@login_required
def settings():
    """Settings page route"""
    return render_template('settings.html', user=session.get('user'))

@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    """Handle profile updates"""
    try:
        username = request.form['username']
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        
        cur = mysql.connection.cursor()
        
        if new_password:
            # Verify current password
            cur.execute("SELECT password FROM users WHERE id = %s", (session['user']['id'],))
            stored_password = cur.fetchone()[0]
            
            if stored_password != hash_password(current_password):
                cur.close()
                flash("Current password is incorrect.", "danger")
                return redirect(url_for('profile'))
            
            # Update username and password
            cur.execute("""
                UPDATE users 
                SET username = %s, password = %s 
                WHERE id = %s
            """, (username, hash_password(new_password), session['user']['id']))
        else:
            # Update username only
            cur.execute("""
                UPDATE users 
                SET username = %s 
                WHERE id = %s
            """, (username, session['user']['id']))
        
        mysql.connection.commit()
        cur.close()
        
        # Update session
        session['user']['username'] = username
        flash("Profile updated successfully!", "success")
        return redirect(url_for('profile'))
        
    except Exception as e:
        print(f"Update profile error: {str(e)}")
        flash("An error occurred while updating profile.", "danger")
        return redirect(url_for('profile'))

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    mysql.connection.rollback()
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(debug=True)