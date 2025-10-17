import os, random
from flask import Flask, request, jsonify
from pymongo import MongoClient
from pymongo.errors import ConfigurationError
import google.generativeai as genai
import openai

app = Flask(__name__)

# ======[ Environment Variables ]====== #
GEMINI_API_KEY = [
    os.getenv("GEMINI_API_KEY_1"),
    os.getenv("GEMINI_API_KEY_2"),
    os.getenv("GEMINI_API_KEY_3")
]
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MONGO_URI = os.getenv("MONGO_URI")

# ======[ Global variables ]====== #
last_key = None
mongo_client = None
db = None
memory_col = None
history_col = None

# ======[ MongoDB Initialization ]====== #
if MONGO_URI:
    try:
        mongo_client = MongoClient(MONGO_URI)
        db = mongo_client["chatbot_db"]
        memory_col = db["memory"]
        history_col = db["history"]
    except ConfigurationError as e:
        print(f"MongoDB Configuration Error: {e}")
        # Allow the app to run without a database connection,
        # but features relying on it will be disabled.
        pass

# ======[ Function to rotate Gemini API keys ]====== #
def get_random_key():
    global last_key
    available_keys = [k for k in GEMINI_API_KEY if k and k != last_key]
    if not available_keys:
        return None
    key = random.choice(available_keys)
    last_key = key
    return key

# ======[ Chatbot Class ]====== #
class ChatbotWithMongoMemory:
    def __init__(self, user_id: str, model: str, system_prompt: str = None):
        self.user_id = user_id
        self.model_type = model.lower()
        self.system_prompt = (
            "You are a helpful AI assistant made by sanchit. "
            "Do not mention Google or any company names in your responses."
        )
        if system_prompt:
            self.system_prompt += " " + system_prompt

        if self.model_type == "gemini":
            gemini_key = get_random_key()
            if not gemini_key:
                raise ValueError("Missing GEMINI_API_KEY environment variable.")
            genai.configure(api_key=gemini_key)
            self.model = genai.GenerativeModel(
                "gemini-1.5-flash",
                system_instruction=self.system_prompt
            )
            # Start a chat session to load history
            self.chat_session = self.model.start_chat(
                history=self._get_history_messages(is_gemini=True)
            )
        elif self.model_type == "gpt":
            if not OPENAI_API_KEY:
                raise ValueError("Missing OPENAI_API_KEY environment variable.")
            self.client = openai.OpenAI(api_key=OPENAI_API_KEY)
        else:
            raise ValueError("Invalid model. Choose 'gemini' or 'gpt'.")

        self.memory = {}
        self._load_memory()

    def _load_memory(self):
        if memory_col:
            doc = memory_col.find_one({"user_id": self.user_id})
            self.memory = doc.get("data", {}) if doc else {}

    def _save_history(self, role, text):
        if history_col:
            history_col.insert_one({"user_id": self.user_id, "role": role, "text": text})

    def _get_history_messages(self, is_gemini=False):
        messages = []
        if is_gemini:
            # Gemini uses a different format
            if history_col:
                msgs = list(history_col.find({"user_id": self.user_id}))
                for m in msgs:
                    # Gemini expects "user" and "model" roles
                    role = "user" if m["role"] == "user" else "model"
                    messages.append({"role": role, "parts": [{"text": m["text"]}]})
        else:
            # Standard OpenAI format
            messages.append({"role": "system", "content": self.system_prompt})
            if history_col:
                msgs = list(history_col.find({"user_id": self.user_id}))
                for m in msgs:
                    messages.append({"role": m["role"], "content": m["text"]})
        return messages

    def chat(self, user_input: str):
        if self.model_type == "gemini":
            return self._chat_gemini(user_input)
        else:
            return self._chat_gpt(user_input)

    def _chat_gemini(self, user_input: str):
        memory_context = ""
        if self.memory:
            memory_context = "Known facts: " + ", ".join(f"{k}: {v}" for k, v in self.memory.items())

        prompt = f"{memory_context}\n\nUser: {user_input}\nAssistant:"

        # Send message through the chat session to maintain history
        response = self.chat_session.send_message(prompt)
        answer = response.text.strip()

        self._save_history("user", user_input)
        self._save_history("model", answer)
        return answer

    def _chat_gpt(self, user_input: str):
        messages = self._get_history_messages()
        if self.memory:
            memory_context = "Known facts: " + ", ".join(f"{k}: {v}" for k, v in self.memory.items())
            messages[0]["content"] += f"\n\n{memory_context}"

        messages.append({"role": "user", "content": user_input})

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=150,
            temperature=0.7
        )
        answer = response.choices[0].message.content.strip()

        self._save_history("user", user_input)
        self._save_history("assistant", answer)
        return answer

# ======[ Routes ]====== #
@app.route('/')
def index():
    return "Working"

@app.route('/ai', methods=['GET'])
def ai_query():
    # Check for essential environment variables first
    if not MONGO_URI:
        return jsonify({
            "error": "The server is not configured correctly. Missing MONGO_URI. "
                     "Please set it in your Vercel deployment environment."
        }), 500

    if not any(GEMINI_API_KEY) and not OPENAI_API_KEY:
        return jsonify({
            "error": "The server is not configured correctly. Missing API keys. "
                     "Please set GEMINI_API_KEY or OPENAI_API_KEY in your Vercel deployment environment."
        }), 500

    try:
        query = request.args.get('query')
        user_id = request.args.get('id')
        model = request.args.get('model')
        system_prompt = request.args.get('system_prompt')

        if not all([query, user_id, model]):
            return jsonify({"error": "Missing required parameters: query, id, model"}), 400
        if model.lower() not in ["gemini", "gpt"]:
            return jsonify({"error": "Invalid model. Choose 'gemini' or 'gpt'."}), 400

        # Create a new bot instance for each request to be stateless
        bot = ChatbotWithMongoMemory(user_id, model, system_prompt)
        response = bot.chat(query)

        return jsonify({"response": response, "Developer": "Sanchit"})
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        # Log the full error for debugging
        print(f"An unexpected error occurred: {e}")
        return jsonify({"error": "An internal server error occurred.", "Contact": "Sanchit"}), 500