import random, os, httpx, uvicorn
import google.generativeai as genai
from openai import OpenAI
from pymongo import MongoClient
from fastapi import FastAPI, Request
from fastapi_utils.tasks import repeat_every
from fastapi.responses import JSONResponse, FileResponse

app = FastAPI()

GEMINI_API_KEYS = os.getenv("GEMINI_API_KEYS", "").split(" ")  
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "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") 
MONGO_URI = os.getenv("MONGO_URI", "")  
PORT = int(os.getenv("PORT", 8000)) 

bots = {}
last_gemini_key = None


def get_random_gemini_key():
    global last_gemini_key
    keys = [k for k in GEMINI_API_KEYS if k != last_gemini_key]
    key = random.choice(keys)
    last_gemini_key = key
    return key


class Chatbot:
    BASE_PROMPT = "You are a helpful AI assistant made by Sanchit. Avoid mentioning Google or OpenAI company names in responses."

    def __init__(self, user_id, model, system_prompt=None):
        self.user_id = user_id
        self.model_type = model.lower()
        self.custom_prompt = system_prompt.strip() if system_prompt else ""
        self.system_prompt = f"{self.BASE_PROMPT} {self.custom_prompt}" if self.custom_prompt else self.BASE_PROMPT

        if self.model_type == "gemini":
            genai.configure(api_key=get_random_gemini_key())
            self.model = genai.GenerativeModel("gemini-2.0-flash", system_instruction=self.system_prompt)
        elif self.model_type == "gpt":
            self.client = OpenAI(api_key=OPENAI_API_KEY)

        self.mongo = MongoClient(MONGO_URI)
        db = self.mongo["chatbot_db"]
        self.history_col = db["history"]

    def _save_history(self, role, text):
        self.history_col.insert_one({"user_id": self.user_id, "role": role, "text": text})

    def _get_history(self):
        return list(self.history_col.find({"user_id": self.user_id}))

    def chat(self, user_input):
        if self.model_type == "gemini":
            history_text = "\n".join([f"{m['role']}: {m['text']}" for m in self._get_history()])
            prompt = f"{self.system_prompt}\n{history_text}\nUser: {user_input}\nAssistant:"
            reply = self.model.generate_content(prompt).text.strip()
        else:
            messages = [{"role": "system", "content": self.system_prompt}]
            for m in self._get_history():
                messages.append({"role": m["role"], "content": m["text"]})
            messages.append({"role": "user", "content": user_input})
            response = self.client.chat.completions.create(model="gpt-4o-mini", messages=messages)
            reply = response.choices[0].message.content.strip()

        self._save_history("user", user_input)
        self._save_history("assistant", reply)
        return reply


@app.get("/ping")
async def ping():
    return JSONResponse({"status": "alive"})

# ===== Self-ping to keep the app awake =====
@app.on_event("startup")
@repeat_every(seconds=300)  # every 5 minutes
async def self_ping_task():
    try:
        url = "https://ds-chatbot-api-platform.onrender.com/ping"  # replace with your Render deployment URL
        async with httpx.AsyncClient() as client:
            await client.get(url)
        print("Self-ping successful")
    except Exception as e:
        print(f"Self-ping failed: {e}")


@app.get("/")
def index():
    return FileResponse("docs.html")

@app.api_route("/ai", methods=["GET", "POST"])
async def ai(request: Request):
    if request.method == "GET":
        query = request.query_params.get("query")
        user_id = request.query_params.get("id")
        model = request.query_params.get("model")
        system_prompt = request.query_params.get("system_prompt", "")
    else:  # POST
        data = await request.json()
        query = data.get("query")
        user_id = data.get("id")
        model = data.get("model")
        system_prompt = data.get("system_prompt", "")

    if not query or not user_id or not model:
        return JSONResponse({"error": "Missing parameters"}, status_code=400)

    bot_key = f"{user_id}_{model}"
    recreate = bot_key not in bots or bots[bot_key].custom_prompt != system_prompt
    if recreate:
        bots[bot_key] = Chatbot(user_id, model, system_prompt)

    try:
        answer = bots[bot_key].chat(query)
        return {"response": answer, "developer": "Sanchit"}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

if __name__ == "__main__":
    uvicorn.run("ds_api:app", host="0.0.0.0", port=port, reload=True)
