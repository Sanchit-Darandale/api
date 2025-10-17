# ======[ Import necessary modules. ]====== #
import os, random
import google.generativeai as genai
import openai
from flask import Flask, request, jsonify, send_from_directory
from pymongo import MongoClient

app = Flask(__name__, static_folder='.')

# ======[ Global variables ]====== #
GEMINI_API_KEY = ["AIzaSyCQuTar_2bLWkRCq6dNRdCgCo4J0Khd41g", "AIzaSyA3JariBIkf6YFcWKNtazIzmOU5H3kpIGY", "AIzaSyAz0qDdrSQhqM-Q9fknLQi0gCjqR9yqfds"]
OPENAI_API_KEY = "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"  # Replace with actual OpenAI API key
MONGO_URI = "mongodb+srv://sanchit:sanchit@cluster0.tirgmqi.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# ======[ Dictionary to store chatbot instances for multiple users and Variable to track the last used API key for rotation ]====== #
bots = {}
last_key = None  

# ======[ Function to select a random API key, avoiding the last used one ]====== #
def get_random_key():
    global last_key
    available_keys = [b for b in GEMINI_API_KEY if b != last_key]
    key = random.choice(available_keys)
    last_key = key
    return key


class ChatbotWithMongoMemory:

    # ======[ Initialize the chatbot with user ID, model, and optional system prompt ]====== #
    def __init__(self, user_id: str, model: str, system_prompt: str = None):
        self.user_id = user_id
        self.model_type = model.lower()

        if system_prompt is None:
            self.system_prompt = "You are a helpful AI assistant made by sanchit. Do not mention Google or any company names in your responses."
        else:
            self.system_prompt = f"You are a helpful AI assistant made by sanchit. Do not mention Google or any company names in your responses. {system_prompt}"

        if self.model_type == 'gemini':
            # Configure Gemini API with a random key
            genai.configure(api_key=get_random_key())
            # Create Gemini model with system instruction
            self.model = genai.GenerativeModel("gemini-2.5-flash", system_instruction=self.system_prompt)
        elif self.model_type == 'gpt':
            # Configure OpenAI API
            self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY") or OPENAI_API_KEY)
        else:
            raise ValueError("Invalid model. Choose 'gemini' or 'gpt'.")

        # Establish MongoDB connection and set up collections
        try:
            self.mongo = MongoClient(os.getenv("MONGO_URI") or MONGO_URI)
            self.db = self.mongo["chatbot_db"]
            self.memory_col = self.db["memory"]
            self.history_col = self.db["history"]
        except Exception as e:
            print(f"MongoDB connection error: {e}. Continuing without MongoDB (memory and history will not be persisted).")
            self.mongo = None
            self.memory = {}
            self.memory_col = None
            self.history_col = None

        # Load persistent memory for the user
        self._load_memory()

    # ======[ Private method to load memory from MongoDB ]====== #
    def _load_memory(self):
        if self.memory_col is not None:
            doc = self.memory_col.find_one({"user_id": self.user_id})
            self.memory = doc["data"] if doc else {}

    # ======[ Private method to save memory to MongoDB ]====== #
    def _save_memory(self):
        """Save memory to MongoDB."""
        if self.memory_col is not None:
            self.memory_col.update_one(
                {"user_id": self.user_id},
                {"$set": {"data": self.memory}},
                upsert=True
            )

    # ======[ Private method to save message to history collection ]====== #
    def _save_history(self, role: str, text: str):
        if self.history_col is not None:
            self.history_col.insert_one({
                "user_id": self.user_id,
                "role": role,
                "text": text
            })

    # ======[ Private method to get chat history as formatted text ]====== #
    def _get_history_text(self):
        if self.history_col is not None:
            msgs = list(self.history_col.find({"user_id": self.user_id}))
            return "\n".join([f"{m['role'].capitalize()}: {m['text']}" for m in msgs])
        return ""

    # ======[ Private method to get chat history as list of messages for GPT ]====== #
    def _get_history_messages(self):
        messages = [{"role": "system", "content": self.system_prompt}]
        if self.history_col is not None:
            msgs = list(self.history_col.find({"user_id": self.user_id}))
            for m in msgs:
                messages.append({"role": m['role'], "content": m['text']})
        return messages

    # ======[ Main chat method to process user input and generate response ]====== #
    def chat(self, user_input: str):
        if self.model_type == 'gemini':
            return self._chat_gemini(user_input)
        elif self.model_type == 'gpt':
            return self._chat_gpt(user_input)
        else:
            raise ValueError("Invalid model type.")

    # ======[ Private method to handle chat with Gemini ]====== #
    def _chat_gemini(self, user_input: str):
        memory_context = ""
        if self.memory:
            memory_context = "Known facts: " + ", ".join(f"{k}: {v}" for k, v in self.memory.items())

        # Construct prompt with memory, history, and user input
        prompt = f"""
        {memory_context}

        Chat history:
        {self._get_history_text()}

        User: {user_input}
        Assistant:
        """

        # Generate response using Gemini model
        response = self.model.generate_content(prompt)
        answer = response.text.strip()

        # Save user input and assistant response to history
        self._save_history("user", user_input)
        self._save_history("assistant", answer)

        return answer

    # ======[ Private method to handle chat with GPT ]====== #
    def _chat_gpt(self, user_input: str):
        # Build messages list
        messages = self._get_history_messages()
        messages.append({"role": "user", "content": user_input})

        # Add memory context if available
        if self.memory:
            memory_context = "Known facts: " + ", ".join(f"{k}: {v}" for k, v in self.memory.items())
            messages[0]["content"] += f"\n\n{memory_context}"

        # Generate response using OpenAI
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",  # or gpt-4 if available
            messages=messages,
            max_tokens=150,
            temperature=0.7
        )
        answer = response.choices[0].message.content.strip()

        # Save user input and assistant response to history
        self._save_history("user", user_input)
        self._save_history("assistant", answer)

        return answer

# ======[ Route to serve the main HTML page ]====== #
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

# ======[ Route to serve the documentation page ]====== #
@app.route('/docs')
def docs():
    return send_from_directory('.', 'docs.html')

# ======[ Route to handle AI queries via GET request ]====== #
@app.route('/ai', methods=['GET'])
def ai_query():
    query = request.args.get('query')
    user_id = request.args.get('id')
    model = request.args.get('model')
    system_prompt = request.args.get('system_prompt')

    if not query or not user_id or not model:
        return jsonify({"error": "Missing required parameters: query, id, and model"}), 400

    if model.lower() not in ['gemini', 'gpt']:
        return jsonify({"error": "Invalid model. Choose 'gemini' or 'gpt'"}), 400

    # Get or create bot for the user
    bot_key = f"{user_id}_{model.lower()}"
    if bot_key not in bots:
        bots[bot_key] = ChatbotWithMongoMemory(
            user_id=user_id,
            model=model,
            system_prompt=system_prompt
        )

    try:
        response = bots[bot_key].chat(query)
        return jsonify({"response": response, "Developer": "Sanchit"})
    except Exception as e:
        return jsonify({"error": str(e), "Contact": "Sanchit"}), 500

# ======[ Run the Flask app in debug mode if executed directly ]====== #
if __name__ == '__main__':
    app.run()
