# import google.generativeai as genai

# genai.configure(api_key="AIzaSyBNbzuPRz5QeOf8JqJd0KLHlyeO5dc69Lc")

# # List available models
# models = genai.list_models()
# for model in models:
#     print(model.name)



from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, Response
from pymongo import MongoClient
from google.oauth2 import id_token
from google.auth.transport import requests
import os
import hashlib
from datetime import datetime
from functools import wraps
import google.generativeai as genai  # Import Gemini API
from bson.objectid import ObjectId

app = Flask(__name__, template_folder='templates')

# Configuration
app.secret_key = os.urandom(24)

# MongoDB Configuration
client = MongoClient('localhost', 27017)
db = client['python_chatbot_db']
users_collection = db['users']
chat_history_collection = db['chat_history']

# Google OAuth2 Configuration
CLIENT_ID = "1058099786136-rduhgd2e6rnln5op6romet21vcshjrb3.apps.googleusercontent.com"

# Gemini API Configuration
genai.configure(api_key='AIzaSyBNbzuPRz5QeOf8JqJd0KLHlyeO5dc69Lc')  # Replace with your Gemini API key

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
    """Initialize database collections"""
    if 'users' not in db.list_collection_names():
        db.create_collection('users')
    if 'chat_history' not in db.list_collection_names():
        db.create_collection('chat_history')

# Initialize database when app starts
with app.app_context():
    init_db()

# Gemini Chatbot Function
def ask_gemini(prompt):
    """Send a prompt to Gemini and get a structured response"""
    try:
        model = genai.GenerativeModel('gemini-1.5-pro')  # Use the Gemini Pro model
        # Add instructions for structured output
        structured_prompt = f"""
        Please provide a structured response to the following query:
        - Use headings (e.g., "### Heading") for main points.
        - Use bullet points or numbered lists for details.
        - Ensure proper formatting for code (use ``` for code blocks).
        - Use paragraphs for explanations.

        Query: {prompt}
        """
        response = model.generate_content(structured_prompt)
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
        chat_history_collection.insert_one({
            'user_id': session['user']['id'],
            'user_input': user_input,
            'bot_response': response,
            'created_at': datetime.now()
        })
        
        return jsonify({'response': response})
    
    # Fetch chat history for the user
    chat_history = list(chat_history_collection.find(
        {'user_id': session['user']['id']},
        {'_id': 1, 'user_input': 1, 'bot_response': 1, 'created_at': 1}
    ).sort('created_at', -1))

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
    chat_history_collection.insert_one({
        'user_id': session['user']['id'],
        'user_input': user_input,
        'bot_response': response,
        'created_at': datetime.now()
    })

    return jsonify({
        'response': response,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'chat_id': chat_id if chat_id else None,
        'chat_title': user_input[:50]  # Use the first 50 characters as the chat title
    })

@app.route('/load_chat/<string:chat_id>', methods=['GET'])
@login_required
def load_chat(chat_id):
    messages = list(chat_history_collection.find(
        {'_id': ObjectId(chat_id), 'user_id': session['user']['id']},
        {'user_input': 1, 'bot_response': 1, 'created_at': 1}
    ).sort('created_at', 1))

    chat_data = {
        'title': messages[0]['user_input'][:50] if messages else 'Chat',
        'messages': [{'role': 'user' if i % 2 == 0 else 'assistant', 'content': msg['user_input'] if i % 2 == 0 else msg['bot_response'], 'timestamp': msg['created_at'].strftime('%Y-%m-%d %H:%M:%S')} for i, msg in enumerate(messages)]
    }

    return jsonify(chat_data)

@app.route('/clear_history', methods=['POST'])
@login_required
def clear_history():
    chat_history_collection.delete_many({'user_id': session['user']['id']})
    return jsonify({'status': 'success'})

@app.route('/delete_chat/<string:chat_id>', methods=['DELETE'])
@login_required
def delete_chat(chat_id):
    """Delete a specific chat by its ID"""
    try:
        # Delete the chat from the database
        result = chat_history_collection.delete_one({'_id': ObjectId(chat_id), 'user_id': session['user']['id']})
        if result.deleted_count > 0:
            return jsonify({'status': 'success', 'message': 'Chat deleted successfully.'})
        else:
            return jsonify({'status': 'error', 'message': 'Chat not found or already deleted.'}), 404
    except Exception as e:
        print(f"Error deleting chat: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/export_chat/<string:chat_id>', methods=['GET'])
@login_required
def export_chat(chat_id):
    messages = list(chat_history_collection.find(
        {'_id': ObjectId(chat_id), 'user_id': session['user']['id']},
        {'user_input': 1, 'bot_response': 1, 'created_at': 1}
    ).sort('created_at', 1))

    chat_text = "\n".join([f"{msg['created_at'].strftime('%Y-%m-%d %H:%M:%S')}: {msg['user_input']}\n{msg['created_at'].strftime('%Y-%m-%d %H:%M:%S')}: {msg['bot_response']}" for msg in messages])

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
            
            # Check for existing user
            existing_user = users_collection.find_one({'email': email})
            
            if existing_user:
                flash("User with that email already exists.", "danger")
                return redirect(url_for('index'))
            
            # Insert new user
            users_collection.insert_one({
                'username': username,
                'email': email,
                'password': password,
                'created_at': datetime.now()
            })
            
            flash("Signup successful! Please login.", "success")
            return redirect(url_for('index'))
            
        except Exception as e:
            print(f"Signup error: {str(e)}")
            flash(f"An error occurred during signup: {str(e)}", "danger")
            return redirect(url_for('index'))

@app.route('/login', methods=['POST'])
def login():
    """Handle user login"""
    if request.method == 'POST':
        try:
            email = request.form['email']
            password = hash_password(request.form['password'])
            
            user = users_collection.find_one({'email': email, 'password': password})
            
            if user:
                session['user'] = {
                    'id': str(user['_id']),
                    'username': user['username'],
                    'email': user['email'],
                    'created_at': user['created_at']
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