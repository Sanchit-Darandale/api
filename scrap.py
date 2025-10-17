import os
from flask import Flask, request, jsonify, send_from_directory
from pymongo import MongoClient
import openai

app = Flask(__name__, static_folder='.')

# ======[ Environment Variables ]====== #
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MONGO_URI = os.getenv("MONGO_URI")

# ======[ Global variables ]====== #
bots = {}

# ======[ Persistent MongoDB client ]====== #
mongo_client = None
db = None
memory_col = None
history_col = None
try:
    if MONGO_URI:
        mongo_client = MongoClient(MONGO_URI)
        db = mongo_client["chatbot_db"]
        memory_col = db["memory"]
        history_col = db["history"]
except Exception as e:
    print("MongoDB connection failed:", e)

# ======[ Chatbot Class ]====== #
class ChatbotWithMongoMemory:
    def __init__(self, user_id: str, system_prompt: str = None):
        self.user_id = user_id
        self.client = openai.OpenAI(api_key=OPENAI_API_KEY)
        self.system_prompt = (
            "You are a helpful AI assistant made by Sanchit. "
            "Do not mention Google or any company names in your responses."
        )
        if system_prompt:
            self.system_prompt += " " + system_prompt
        self.memory = {}
        self._load_memory()

    def _load_memory(self):
        if memory_col:
            doc = memory_col.find_one({"user_id": self.user_id})
            self.memory = doc["data"] if doc else {}

    def _save_memory(self):
        if memory_col:
            memory_col.update_one(
                {"user_id": self.user_id},
                {"$set": {"data": self.memory}},
                upsert=True
            )

    def _save_history(self, role, text):
        if history_col:
            history_col.insert_one({"user_id": self.user_id, "role": role, "text": text})

    def _get_history_messages(self):
        messages = [{"role": "system", "content": self.system_prompt}]
        if history_col:
            msgs = list(history_col.find({"user_id": self.user_id}))
            for m in msgs:
                messages.append({"role": m['role'], "content": m['text']})
        return messages

    def chat(self, user_input: str):
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
@app.route('/ai', methods=['POST'])
def ai_query():
    try:
        data = request.json
        query = data.get('query')
        user_id = data.get('id')
        system_prompt = data.get('system_prompt', None)

        if not query or not user_id:
            return jsonify({"error": "Missing parameters: query or id"}), 400

        if user_id not in bots:
            bots[user_id] = ChatbotWithMongoMemory(user_id, system_prompt)

        response = bots[user_id].chat(query)
        return jsonify({"response": response, "Developer": "Sanchit"})
    except Exception as e:
        print("Error:", e)
        return jsonify({"error": str(e), "Contact": "Sanchit"}), 500

@app.route('/')
def index():
    return "Helo Words"

