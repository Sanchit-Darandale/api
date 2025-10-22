# DS API Platform Usage Guide

This guide provides comprehensive examples and best practices for integrating with the DS API Platform, a unified chatbot API powered by OpenAI GPT and Google Gemini models with MongoDB memory persistence.

## Table of Contents
- [Getting Started](#getting-started)
- [API Endpoint](#api-endpoint)
- [User ID Management](#user-id-management)
- [Request Examples](#request-examples)
- [Code Integration Examples](#code-integration-examples)
- [Full Chat Interface Example](#full-chat-interface-example)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Getting Started

### Prerequisites
- Basic knowledge of HTTP requests (GET/POST)
- Familiarity with JSON data format
- For web integrations: JavaScript and localStorage API

### Base URL
```
https://ds-chatbot-api-platform.onrender.com/ai
```

## API Endpoint

### Endpoint Details
- **URL**: `/ai`
- **Methods**: GET, POST
- **Content-Type**: `application/json` (for POST requests)

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | Yes | User input or question for the chatbot |
| `id` | string | Yes | Unique user ID for storing chat history in MongoDB |
| `model` | string | Yes | AI model to use: `"gpt"` or `"gemini"` |
| `system_prompt` | string | No | Custom system prompt for AI behavior |

### Response Format
```json
{
  "response": "AI-generated response text",
  "Developer": "Sanchit"
}
```

## User ID Management

### Why User IDs Matter
User IDs enable persistent chat memory across sessions. Each unique ID maintains its own conversation history in MongoDB.

### Storing User ID in localStorage

#### JavaScript Example
```javascript
// Generate and store user ID
let userId = localStorage.getItem('chatbot_user_id');
if (!userId) {
    userId = 'user_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    localStorage.setItem('chatbot_user_id', userId);
    console.log('New user ID generated:', userId);
} else {
    console.log('Existing user ID retrieved:', userId);
}

// Use the userId in your API calls
console.log('Ready to use userId:', userId);
```

#### Key Points
- **Persistence**: localStorage survives browser sessions
- **Uniqueness**: Combine timestamp and random string for uniqueness
- **Fallback**: Always check if ID exists before generating new one
- **Security**: User IDs are not sensitive; they're just identifiers

### Alternative Storage Methods

#### Session Storage (temporary)
```javascript
// Session storage - clears when tab closes
let userId = sessionStorage.getItem('chatbot_user_id');
if (!userId) {
    userId = 'session_' + Date.now();
    sessionStorage.setItem('chatbot_user_id', userId);
}
```

#### Cookies (cross-domain)
```javascript
// Set cookie that expires in 30 days
function setUserIdCookie(userId) {
    const expires = new Date();
    expires.setTime(expires.getTime() + (30 * 24 * 60 * 60 * 1000)); // 30 days
    document.cookie = `chatbot_user_id=${userId};expires=${expires.toUTCString()};path=/`;
}

// Get cookie
function getUserIdCookie() {
    const name = 'chatbot_user_id=';
    const decodedCookie = decodeURIComponent(document.cookie);
    const cookies = decodedCookie.split(';');
    for (let cookie of cookies) {
        cookie = cookie.trim();
        if (cookie.indexOf(name) === 0) {
            return cookie.substring(name.length);
        }
    }
    return null;
}
```

## Request Examples

### GET Request
```bash
curl "https://ds-chatbot-api-platform.onrender.com/ai?query=Hello&model=gpt&id=user123"
```

### POST Request
```bash
curl -X POST "https://ds-chatbot-api-platform.onrender.com/ai" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "Explain neural networks in simple terms.",
       "model": "gemini",
       "id": "user456",
       "system_prompt": "Answer in a concise technical format."
     }'
```

## Code Integration Examples

### Python
```python
import requests

def chat_with_ai(query, user_id, model='gpt', system_prompt=None):
    url = 'https://ds-chatbot-api-platform.onrender.com/ai'
    data = {
        'query': query,
        'model': model,
        'id': user_id
    }
    if system_prompt:
        data['system_prompt'] = system_prompt

    response = requests.post(url, json=data)
    return response.json()

# Usage
result = chat_with_ai("What is machine learning?", "user789")
print(result['response'])
```

### JavaScript (Browser)
```javascript
async function sendMessageToAI(message, userId, model = 'gpt') {
    const url = 'https://ds-chatbot-api-platform.onrender.com/ai';
    const data = {
        query: message,
        model: model,
        id: userId
    };

    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const result = await response.json();
        return result.response;
    } catch (error) {
        console.error('Error:', error);
        return 'Sorry, there was an error processing your request.';
    }
}

// Usage with localStorage user ID
let userId = localStorage.getItem('chatbot_user_id');
if (!userId) {
    userId = 'user_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    localStorage.setItem('chatbot_user_id', userId);
}

sendMessageToAI("Hello!", userId).then(response => {
    console.log('AI Response:', response);
});
```

### Java
```java
import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.net.http.HttpRequest.BodyPublishers;
import java.net.http.HttpResponse.BodyHandlers;

public class ChatbotClient {
    private static final String API_URL = "https://ds-chatbot-api-platform.onrender.com/ai";

    public static String sendMessage(String query, String userId, String model) throws IOException, InterruptedException {
        String json = String.format("""
            {
                "query": "%s",
                "model": "%s",
                "id": "%s"
            }
            """, query, model, userId);

        HttpClient client = HttpClient.newHttpClient();
        HttpRequest request = HttpRequest.newBuilder()
            .uri(URI.create(API_URL))
            .header("Content-Type", "application/json")
            .POST(BodyPublishers.ofString(json))
            .build();

        HttpResponse<String> response = client.send(request, BodyHandlers.ofString());
        return response.body();
    }

    public static void main(String[] args) {
        try {
            String response = sendMessage("What is machine learning?", "user789", "gpt");
            System.out.println(response);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
```

### C++
```cpp
#include <iostream>
#include <curl/curl.h>
#include <string>

size_t WriteCallback(void* contents, size_t size, size_t nmemb, void* userp) {
    ((std::string*)userp)->append((char*)contents, size * nmemb);
    return size * nmemb;
}

std::string sendChatMessage(const std::string& query, const std::string& userId, const std::string& model) {
    CURL* curl;
    CURLcode res;
    std::string readBuffer;

    curl = curl_easy_init();
    if(curl) {
        std::string jsonData = "{\"query\":\"" + query + "\",\"model\":\"" + model + "\",\"id\":\"" + userId + "\"}";

        curl_easy_setopt(curl, CURLOPT_URL, "https://ds-chatbot-api-platform.onrender.com/ai");
        curl_easy_setopt(curl, CURLOPT_POSTFIELDS, jsonData.c_str());
        curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, WriteCallback);
        curl_easy_setopt(curl, CURLOPT_WRITEDATA, &readBuffer);

        struct curl_slist *headers = NULL;
        headers = curl_slist_append(headers, "Content-Type: application/json");
        curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);

        res = curl_easy_perform(curl);
        if(res != CURLE_OK) {
            std::cerr << "curl_easy_perform() failed: " << curl_easy_strerror(res) << std::endl;
        }

        curl_slist_free_all(headers);
        curl_easy_cleanup(curl);
    }
    return readBuffer;
}

int main() {
    std::string response = sendChatMessage("What is machine learning?", "user789", "gpt");
    std::cout << response << std::endl;
    return 0;
}
```

## Full Chat Interface Example

Here's a complete HTML/JavaScript chat interface that demonstrates user ID management, message sending, and response handling:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DS API Chatbot Interface</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        #chatContainer {
            border: 1px solid #ccc;
            height: 400px;
            overflow-y: auto;
            padding: 10px;
            background-color: white;
            border-radius: 5px;
            margin-bottom: 10px;
        }
        .message {
            margin-bottom: 10px;
            padding: 8px;
            border-radius: 5px;
        }
        .user-message {
            background-color: #007bff;
            color: white;
            text-align: right;
        }
        .bot-message {
            background-color: #e9ecef;
            color: #333;
        }
        #messageInput {
            width: 70%;
            padding: 10px;
            border: 1px solid #ccc;
            border-radius: 5px;
        }
        button {
            padding: 10px 20px;
            background-color: #28a745;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
        }
        button:hover {
            background-color: #218838;
        }
        #modelSelect {
            margin-left: 10px;
            padding: 5px;
        }
        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid #f3f3f3;
            border-top: 3px solid #3498db;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <h1>DS API Chatbot</h1>
    <div id="chatContainer"></div>
    <input type="text" id="messageInput" placeholder="Type your message...">
    <select id="modelSelect">
        <option value="gpt">GPT</option>
        <option value="gemini">Gemini</option>
    </select>
    <button onclick="sendMessage()">Send</button>

    <script>
        // User ID Management
        let userId = localStorage.getItem('chatbot_user_id');
        if (!userId) {
            userId = 'user_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('chatbot_user_id', userId);
            console.log('New user ID generated and stored:', userId);
        } else {
            console.log('Existing user ID loaded:', userId);
        }

        // Display user ID info
        const infoDiv = document.createElement('div');
        infoDiv.style.fontSize = '12px';
        infoDiv.style.color = '#666';
        infoDiv.style.marginBottom = '10px';
        infoDiv.textContent = `Your User ID: ${userId}`;
        document.body.insertBefore(infoDiv, document.getElementById('chatContainer'));

        async function sendMessage() {
            const message = document.getElementById('messageInput').value.trim();
            const model = document.getElementById('modelSelect').value;

            if (!message) return;

            // Add user message to chat
            addMessage(message, true);
            document.getElementById('messageInput').value = '';

            // Show loading indicator
            const loadingDiv = addMessage('Thinking...', false);
            loadingDiv.innerHTML = '<div class="loading"></div> Thinking...';

            try {
                // Send to API
                const response = await sendMessageToAPI(message, model);
                loadingDiv.remove();
                addMessage(response, false);
            } catch (error) {
                loadingDiv.remove();
                addMessage('Error: ' + error.message, false);
            }
        }

        async function sendMessageToAPI(message, model) {
            const url = 'https://ds-chatbot-api-platform.onrender.com/ai';
            const data = {
                query: message,
                model: model,
                id: userId
            };

            const response = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            return result.response || 'No response received';
        }

        function addMessage(message, isUser) {
            const chatContainer = document.getElementById('chatContainer');
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message ' + (isUser ? 'user-message' : 'bot-message');
            messageDiv.textContent = message;
            chatContainer.appendChild(messageDiv);
            chatContainer.scrollTop = chatContainer.scrollHeight;
            return messageDiv;
        }

        // Allow sending message on Enter key
        document.getElementById('messageInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });

        // Initialize with welcome message
        addMessage('Hello! I\'m your AI assistant. How can I help you today?', false);
    </script>
</body>
</html>
```

## Best Practices

### User ID Management
- **Generate unique IDs**: Use timestamp + random string for uniqueness
- **Persist across sessions**: Use localStorage for web apps
- **Handle missing IDs**: Always check and generate if needed
- **User privacy**: IDs are anonymous; no personal data required

### API Usage
- **Rate limiting**: Implement delays between requests if needed
- **Error handling**: Always wrap API calls in try-catch blocks
- **Model selection**: Let users choose between GPT and Gemini
- **System prompts**: Use custom prompts for specialized behavior

### Performance
- **Caching**: Cache responses for frequently asked questions
- **Batch requests**: Group multiple queries if possible
- **Connection pooling**: Reuse HTTP connections in server environments

### Security
- **Input validation**: Sanitize user inputs before sending
- **HTTPS only**: Always use HTTPS for API calls
- **API keys**: Never expose sensitive credentials in client-side code

## Troubleshooting

### Common Issues

#### "Invalid user ID" error
- Ensure the `id` parameter is a non-empty string
- Check for special characters that might cause encoding issues

#### "Model not found" error
- Verify the `model` parameter is either "gpt" or "gemini" (case-sensitive)

#### CORS errors in browser
- The API supports CORS for web applications
- If issues persist, consider using a proxy server

#### Memory not persisting
- Each user ID maintains separate conversation history
- Verify you're using the same ID across requests
- Check MongoDB connection if self-hosting

#### Rate limiting
- Implement exponential backoff for retries
- Space out requests in high-traffic applications

### Debug Tips
- Use browser developer tools to inspect network requests
- Log user IDs and API responses for debugging
- Test with simple queries first before complex integrations

### Getting Help
- Check the API documentation at `docs.html`
- Review the examples in this guide
- Test endpoints using the built-in playground in the documentation

---

**Developer**: Sanchit  
**Last Updated**: 2025  
**API Version**: 1.0
