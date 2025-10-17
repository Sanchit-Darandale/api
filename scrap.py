import os, random
from flask import Flask, request, jsonify, send_from_directory
from pymongo import MongoClient
import google.generativeai as genai
import openai

app = Flask(__name__, static_folder='.')

# ======[ Environment Variables ]====== #
GEMINI_API_KEY = [
    os.getenv("GEMINI_API_KEY_1"),
    os.getenv("GEMINI_API_KEY_2"),
    os.getenv("GEMINI_API_KEY_3")
]
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MONGO_URI = os.getenv("MONGO_URI")

# ======[ Global variables ]====== #
bots = {}
last_key = None  

# ======[ Persistent MongoDB client ]====== #
mongo_client = MongoClient(MONGO_URI) if MONGO_URI else None
db = mongo_client["chatbot_db"] if mongo_client else None
memory_col = db["memory"] if db else None
history_col = db["history"] if db else None

# ======[ Function to rotate Gemini API keys ]====== #
def get_random_key():
    global last_key
    available_keys = [k for k in GEMINI_API_KEY if k and k != last_key]
    key = random.choice(available_keys) if available_keys else None
    last_key = key
    return key

# ======[ Chatbot Class ]====== #
class ChatbotWithMongoMemory:
    def __init__(self, user_id: str, model: str, system_prompt: str = None):
        self.user_id = user_id
        self.model_type = model.lower()
        self.system_prompt = (
            f"You are a helpful AI assistant made by sanchit. "
            f"Do not mention Google or any company names in your responses."
        )
        if system_prompt:
            self.system_prompt += " " + system_prompt

        if self.model_type == "gemini":
            key = get_random_key()
            if not key:
                raise ValueError("No Gemini API key available")
            genai.configure(api_key=key)
            self.model = genai.GenerativeModel("gemini-2.5-flash", system_instruction=self.system_prompt)
        elif self.model_type == "gpt":
            self.client = openai.OpenAI(api_key=OPENAI_API_KEY)
        else:
            raise ValueError("Invalid model. Choose 'gemini' or 'gpt'.")

        self.memory = {}
        self._load_memory()

    # ======[ Load user memory ]====== #
    def _load_memory(self):
        if memory_col:
            doc = memory_col.find_one({"user_id": self.user_id})
            self.memory = doc["data"] if doc else {}

    # ======[ Save memory ]====== #
    def _save_memory(self):
        if memory_col:
            memory_col.update_one(
                {"user_id": self.user_id},
                {"$set": {"data": self.memory}},
                upsert=True
            )

    # ======[ Save history message ]====== #
    def _save_history(self, role, text):
        if history_col:
            history_col.insert_one({"user_id": self.user_id, "role": role, "text": text})

    # ======[ Get chat history for GPT messages ]====== #
    def _get_history_messages(self):
        messages = [{"role": "system", "content": self.system_prompt}]
        if history_col:
            msgs = list(history_col.find({"user_id": self.user_id}))
            for m in msgs:
                messages.append({"role": m['role'], "content": m['text']})
        return messages

    # ======[ Chat main method ]====== #
    def chat(self, user_input: str):
        if self.model_type == "gemini":
            return self._chat_gemini(user_input)
        else:
            return self._chat_gpt(user_input)

    # ======[ Gemini chat ]====== #
    def _chat_gemini(self, user_input: str):
        memory_context = ""
        if self.memory:
            memory_context = "Known facts: " + ", ".join(f"{k}: {v}" for k, v in self.memory.items())

        prompt = f"{memory_context}\n\nUser: {user_input}\nAssistant:"
        response = self.model.generate_content(prompt)
        answer = response.text.strip()

        self._save_history("user", user_input)
        self._save_history("assistant", answer)
        return answer

    # ======[ GPT chat ]====== #
    def _chat_gpt(self, user_input: str):
        messages = self._get_history_messages()
        messages.append({"role": "user", "content": user_input})
        if self.memory:
            memory_context = "Known facts: " + ", ".join(f"{k}: {v}" for k, v in self.memory.items())
            messages[0]["content"] += f"\n\n{memory_context}"

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
    try:
        query = request.args.get('query')
        user_id = request.args.get('id')
        model = request.args.get('model')
        system_prompt = request.args.get('system_prompt')

        if not query or not user_id or not model:
            return jsonify({"error": "Missing parameters: query, id, model"}), 400
        if model.lower() not in ["gemini", "gpt"]:
            return jsonify({"error": "Invalid model. Choose gemini or gpt"}), 400

        bot_key = f"{user_id}_{model.lower()}"
        if bot_key not in bots:
            bots[bot_key] = ChatbotWithMongoMemory(user_id, model, system_prompt)

        response = bots[bot_key].chat(query)
        return jsonify({"response": response, "Developer": "Sanchit"})
    except Exception as e:
        return jsonify({"error": str(e), "Contact": "Sanchit"}), 500
