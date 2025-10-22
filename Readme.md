# AI Chatbot API

This is a Flask-based API for an AI chatbot that uses Google's Gemini AI model with MongoDB for storing chat history and user memory.

## Features

- Conversational AI using Gemini 2.5 Flash model
- Persistent chat history per user
- User memory (remembers facts like names)
- Customizable system prompts
- Web interface included


## API Usage

### Endpoint: `/ai`

**Method:** GET

**Parameters:**
- `query` (required): The user's message
- `id` (required): Unique user identifier for storing history
- `system_prompt` (optional): Custom system prompt for the AI

**Example Request:**
```
GET /ai?query=Hello&system_prompt=You+are+a+helpful+assistant&id=user123
```

**Response:**
```json
{
  "response": "Hello! How can I help you today?"
}
```

**Error Response:**
```json
{
  "error": "Missing required parameters: query and id"
}
```

## Integrating into Your Website

### 1. Generate User ID

To maintain chat history, each user needs a unique ID. Use localStorage to store and retrieve the user ID:

```javascript
// Generate or retrieve user ID
let userId = localStorage.getItem('chatbot_user_id');
if (!userId) {
    userId = 'user_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    localStorage.setItem('chatbot_user_id', userId);
}
```

### 2. Send Messages to API

Use fetch API to send messages:

```javascript
async function sendMessage(message, systemPrompt = '') {
    const url = `/ai?query=${encodeURIComponent(message)}&id=${encodeURIComponent(userId)}${systemPrompt ? '&system_prompt=' + encodeURIComponent(systemPrompt) : ''}`;

    try {
        const response = await fetch(url);
        const data = await response.json();

        if (data.response) {
            return data.response;
        } else {
            throw new Error(data.error || 'Unknown error call developer (Sanchit)');
        }
    } catch (error) {
        console.error('Error:', error);
        return 'Sorry, there was an error processing your request.';
    }
}
```

### 3. Example HTML Structure

```html
<div id="chatContainer">
    <!-- Messages will appear here -->
</div>
<input type="text" id="userInput" placeholder="Type your message...">
<button onclick="sendMessage(document.getElementById('userInput').value)">Send</button>

<script>
    let userId = localStorage.getItem('chatbot_user_id');
    if (!userId) {
        userId = 'user_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        localStorage.setItem('chatbot_user_id', userId);
    }

    async function sendMessage(message) {
        // Add user message to chat
        addMessage(message, true);

        // Get AI response
        const response = await sendMessageToAPI(message);
        addMessage(response, false);
    }

    function addMessage(message, isUser) {
        const chatContainer = document.getElementById('chatContainer');
        const messageDiv = document.createElement('div');
        messageDiv.className = isUser ? 'user-message' : 'bot-message';
        messageDiv.textContent = message;
        chatContainer.appendChild(messageDiv);
    }
</script>
```

## Method 1: Username as User ID (Simple)

If you want to use the username directly as the user ID:

```javascript
// After successful login
const userId = username; // Use username directly
localStorage.setItem('chatbot_user_id', userId);

// Then use in API calls
const response = await fetch(`/ai?query=${message}&id=${userId}`);
```

## Method 2: Hashed Username + Password (Recommended)

Generate a consistent hash from username and password combination:

```javascript
function generateUserId(username, password) {
    // Simple hash for demo - use crypto libraries in production
    const combined = username + password + "your_salt_here";
    let hash = 0;
    for (let i = 0; i < combined.length; i++) {
        const char = combined.charCodeAt(i);
        hash = ((hash << 5) - hash) + char;
        hash = hash & hash;
    }
    return 'user_' + Math.abs(hash).toString(36);
}

// Usage after login
const userId = generateUserId(username, password);
localStorage.setItem('chatbot_user_id', userId);
```


### 3. API Calls with User ID

```javascript
async function sendMessage(message, userId, systemPrompt = '') {
    const params = new URLSearchParams({
        query: message,
        id: userId
    });

    if (systemPrompt) {
        params.append('system_prompt', systemPrompt);
    }

    const response = await fetch(`/ai?${params}`);
    const data = await response.json();

    if (data.error) {
        throw new Error(data.error);
    }

    return data.response;
}
```

## Complete Example

Here's a complete login and chat integration:

```html
<!DOCTYPE html>
<html>
<head>
    <title>Login & Chat</title>
</head>
<body>
    <div id="loginForm">
        <input type="text" id="username" placeholder="Username">
        <input type="password" id="password" placeholder="Password">
        <button onclick="login()">Login</button>
    </div>

    <div id="chatInterface" style="display: none;">
        <div id="chatMessages"></div>
        <input type="text" id="messageInput" placeholder="Type message...">
        <button onclick="sendMessage()">Send</button>
    </div>

    <script>
        function generateUserId(username, password) {
            const combined = username + password + "chatbot_salt_2024";
            let hash = 0;
            for (let i = 0; i < combined.length; i++) {
                hash = ((hash << 5) - hash) + combined.charCodeAt(i);
                hash = hash & hash;
            }
            return 'user_' + Math.abs(hash).toString(36);
        }

        function login() {
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;

            if (!username || !password) {
                alert('Please enter username and password');
                return;
            }

            // Generate and store user ID
            const userId = generateUserId(username, password);
            localStorage.setItem('chatbot_user_id', userId);
            localStorage.setItem('chatbot_username', username);

            // Show chat interface
            document.getElementById('loginForm').style.display = 'none';
            document.getElementById('chatInterface').style.display = 'block';
        }

        async function sendMessage() {
            const messageInput = document.getElementById('messageInput');
            const message = messageInput.value.trim();
            const userId = localStorage.getItem('chatbot_user_id');

            if (!message || !userId) return;

            // Add user message to chat
            addMessage(message, 'user');
            messageInput.value = '';

            try {
                const response = await fetch(`/ai?query=${encodeURIComponent(message)}&id=${userId}`);
                const data = await response.json();

                if (data.response) {
                    addMessage(data.response, 'bot');
                } else {
                    addMessage('Error: ' + data.error, 'error');
                }
            } catch (error) {
                addMessage('Network error: ' + error.message, 'error');
            }
        }

        function addMessage(text, type) {
            const messagesDiv = document.getElementById('chatMessages');
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${type}`;
            messageDiv.textContent = text;
            messagesDiv.appendChild(messageDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }

        // Check if already logged in
        window.onload = function() {
            const userId = localStorage.getItem('chatbot_user_id');
            const username = localStorage.getItem('chatbot_username');

            if (userId && username) {
                document.getElementById('username').value = username;
                document.getElementById('loginForm').style.display = 'none';
                document.getElementById('chatInterface').style.display = 'block';
            }
        }
    </script>
</body>
</html>
```
