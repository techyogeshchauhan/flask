# app.py
from flask import Flask, render_template, request, jsonify, session
from datetime import datetime
import sqlite3
import uuid

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Replace with a secure secret key

# Database initialization
def init_db():
    conn = sqlite3.connect('chatbot.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS conversations
                 (id TEXT, user_id TEXT, role TEXT, content TEXT, timestamp DATETIME)''')
    conn.commit()
    conn.close()

def store_message(user_id, role, content):
    conn = sqlite3.connect('chatbot.db')
    c = conn.cursor()
    c.execute('INSERT INTO conversations (id, user_id, role, content, timestamp) VALUES (?, ?, ?, ?, ?)',
              (str(uuid.uuid4()), user_id, role, content, datetime.now()))
    conn.commit()
    conn.close()

def get_chat_history(user_id):
    conn = sqlite3.connect('chatbot.db')
    c = conn.cursor()
    c.execute('SELECT role, content FROM conversations WHERE user_id = ? ORDER BY timestamp ASC', (user_id,))
    messages = c.fetchall()
    conn.close()
    return [{'role': msg[0], 'content': msg[1]} for msg in messages]

# Initialize database at startup
with app.app_context():
    init_db()

@app.before_request
def before_request():
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())

# Simple response logic - expand this with your chatbot logic
def get_bot_response(message):
    responses = {
        "hello": "Hello! How can I assist you with university-related questions?",
        "courses": "We offer various courses across different departments. Which faculty interests you?",
        "admission": "For admission inquiries, you'll need to submit an application. Would you like more information?",
        "fees": "Tuition fees vary by program. Would you like specific program fee information?",
    }
    
    message = message.lower()
    for key in responses:
        if key in message:
            return responses[key]
    return "I'm here to help with university-related questions. Could you please rephrase your question?"

@app.route('/')
def home():
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    chat_history = get_chat_history(session['user_id'])
    return render_template('bot.html', chat_history=chat_history)

@app.route('/get_response', methods=['POST'])
def get_response():
    user_message = request.json['message']
    user_id = session['user_id']
    
    # Store user message
    store_message(user_id, 'user', user_message)
    
    # Get and store bot response
    bot_response = get_bot_response(user_message)
    store_message(user_id, 'assistant', bot_response)
    
    return jsonify({
        'response': bot_response,
        'timestamp': datetime.now().strftime('%H:%M')
    })

@app.route('/clear_history', methods=['POST'])
def clear_history():
    conn = sqlite3.connect('chatbot.db')
    c = conn.cursor()
    c.execute('DELETE FROM conversations WHERE user_id = ?', (session['user_id'],))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run(debug=True)