from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, Response
from flask_mysqldb import MySQL
from google.oauth2 import id_token
from google.auth.transport import requests
import os
import hashlib
from datetime import datetime
from functools import wraps
import google.generativeai as genai  # Import Gemini API

app = Flask(__name__, template_folder='templates')

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

# Gemini API Configuration
genai.configure(api_key='AIzaSyCpxJBVGRH2WWlxKEQ-kMC-vP9u5-Ckw_k')  # Replace with your Gemini API key

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
    cur.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            user_input TEXT NOT NULL,
            bot_response TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    mysql.connection.commit()
    cur.close()

# Initialize database when app starts
with app.app_context():
    init_db()

# Gemini Chatbot Function
def ask_gemini(prompt):
    """Send a prompt to Gemini and get a response"""
    try:
        model = genai.GenerativeModel('gemini-pro')  # Use the Gemini Pro model
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Gemini API error: {str(e)}")
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
        response = ask_gemini(user_input)  # Use Gemini API here
        
        # Save chat history
        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO chat_history (user_id, user_input, bot_response)
            VALUES (%s, %s, %s)
        """, (session['user']['id'], user_input, response))
        mysql.connection.commit()
        cur.close()
        
        return jsonify({'response': response})
    
    # Fetch chat history for the user
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT id, user_input, bot_response, created_at 
        FROM chat_history 
        WHERE user_id = %s 
        ORDER BY created_at DESC
    """, (session['user']['id'],))
    chat_history = cur.fetchall()
    cur.close()

    # Debug: Print chat history to the console
    print("Chat History:", chat_history)
    
    return render_template('chatbot.html', user=session.get('user'), chat_history=chat_history)     

@app.route('/get_response', methods=['POST'])
@login_required
def get_response():
    data = request.json
    user_input = data.get('message')
    chat_id = data.get('chat_id')

    # Get response from Gemini
    response = ask_gemini(user_input)

    # Save chat history
    cur = mysql.connection.cursor()
    cur.execute("""
        INSERT INTO chat_history (user_id, user_input, bot_response)
        VALUES (%s, %s, %s)
    """, (session['user']['id'], user_input, response))
    mysql.connection.commit()
    cur.close()

    return jsonify({
        'response': response,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'chat_id': chat_id if chat_id else None,
        'chat_title': user_input[:50]  # Use the first 50 characters as the chat title
    })

@app.route('/load_chat/<int:chat_id>', methods=['GET'])
@login_required
def load_chat(chat_id):
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT user_input, bot_response, created_at 
        FROM chat_history 
        WHERE id = %s AND user_id = %s
        ORDER BY created_at ASC
    """, (chat_id, session['user']['id']))
    messages = cur.fetchall()
    cur.close()

    chat_data = {
        'title': messages[0][0][:50] if messages else 'Chat',
        'messages': [{'role': 'user' if i % 2 == 0 else 'assistant', 'content': msg[0] if i % 2 == 0 else msg[1], 'timestamp': msg[2].strftime('%Y-%m-%d %H:%M:%S')} for i, msg in enumerate(messages)]
    }

    return jsonify(chat_data)

@app.route('/clear_history', methods=['POST'])
@login_required
def clear_history():
    cur = mysql.connection.cursor()
    cur.execute("""
        DELETE FROM chat_history 
        WHERE user_id = %s
    """, (session['user']['id'],))
    mysql.connection.commit()
    cur.close()

    return jsonify({'status': 'success'})

@app.route('/export_chat/<int:chat_id>', methods=['GET'])
@login_required
def export_chat(chat_id):
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT user_input, bot_response, created_at 
        FROM chat_history 
        WHERE id = %s AND user_id = %s
        ORDER BY created_at ASC
    """, (chat_id, session['user']['id']))
    messages = cur.fetchall()
    cur.close()

    chat_text = "\n".join([f"{msg[2]}: {msg[0]}\n{msg[2]}: {msg[1]}" for msg in messages])

    return Response(
        chat_text,
        mimetype="text/plain",
        headers={"Content-Disposition": f"attachment;filename=chat_{chat_id}.txt"}
    )

# Other routes (signup, login, logout, etc.) remain unchanged...
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
                return redirect(url_for('dashboard'))  # Redirect to dashboard
            else:
                flash("Invalid email or password", "danger")
                return redirect(url_for('index'))
                
        except Exception as e:
            print(f"Login error: {str(e)}")
            flash(f"An error occurred during login: {str(e)}", "danger")
            return redirect(url_for('index'))
@app.route('/logout')
def logout():
    """Handle user logout"""
    session.pop('user', None)
    flash("Logged out successfully!", "success")
    return redirect(url_for('index'))
@app.route('/settings')
@login_required
def settings():
    """Settings page route"""
    return render_template('settings.html', user=session.get('user'))

if __name__ == '__main__':
    app.run(debug=True)