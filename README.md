# Chatbot - Dev Sanskriti Vishwavidyalaya

![Chatbot Icon](https://img.icons8.com/clouds/100/000000/chatbot.png)

## 🌟 Overview
This is a **fully functional domain-specific chatbot** developed for **Dev Sanskriti Vishwavidyalaya** using **OpenAI API**. The chatbot provides university-related information, integrates **Google Authentication**, and securely stores user credentials in a **MongoDB database**.

## 🚀 Features
- 🎯 **Domain-Specific Chatbot**: Trained for university-related queries.
- 🔑 **Google Authentication**: Users can log in securely using Google.
- 🔒 **MongoDB Integration**: Stores user authentication details.
- ⚡ **Fast & Responsive UI**: Built with **HTML, CSS, and JavaScript**.
- 🖥️ **Flask Backend**: Handles API requests and authentication.

## 🛠️ Tech Stack
- **Frontend**: HTML, CSS, JavaScript
- **Backend**: Flask (Python)
- **Database**: MongoDB
- **Authentication**: Google OAuth
- **AI API**: OpenAI GPT

## 📸 Screenshots
![Chatbot UI](https://via.placeholder.com/600x300?text=Chatbot+UI+Preview)

## 🏗️ Installation
1. **Clone the repository**:
   ```bash
   git clone https://github.com/YOUR_GITHUB_USERNAME/university-chatbot.git
   cd university-chatbot
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   Create a `.env` file and add:
   ```env
   OPENAI_API_KEY=your_openai_api_key
   GOOGLE_CLIENT_ID=your_google_client_id
   GOOGLE_CLIENT_SECRET=your_google_client_secret
   MONGO_URI=your_mongodb_connection_string
   ```

4. **Run the application**:
   ```bash
   python app.py
   ```

5. **Open in browser**:
   Visit `http://127.0.0.1:5000`

## 📜 API Endpoints
| Method | Endpoint          | Description                       |
|--------|------------------|-----------------------------------|
| GET    | `/`              | Home Page                        |
| POST   | `/chat`          | Handles chatbot queries          |
| GET    | `/login`         | Initiates Google Authentication  |
| GET    | `/logout`        | Logs out the user                |

## 🎯 Future Enhancements
- ✅ Add voice-based chatbot interaction
- ✅ Improve UI with a modern design framework
- ✅ Deploy on cloud (AWS/Heroku)

## 📜 License
This project is licensed under the **MIT License**.

## 🤝 Contributing
Feel free to contribute to this project! Fork the repository and submit a pull request.

---
🚀 Developed by **Yogesh Chauhan** | [LinkedIn](https://linkedin.com/in/your-profile) | [GitHub](https://github.com/YOUR_GITHUB_USERNAME)

