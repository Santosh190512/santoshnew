import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import time

app = Flask(__name__)
CORS(app)

# Groq API key
GROQ_API_KEY = "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"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

HEADERS = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json"
}

# User memory (simple in-memory storage)
USER_MEMORY = {}

def query_groq(user_id, message, model="deepseek-r1-distill-llama-70b", max_retries=3):
    """Query Groq API with message history."""
    if user_id not in USER_MEMORY:
        USER_MEMORY[user_id] = [
            {"role": "system", "content": "You are a helpful career advisor offering guidance on careers."}
        ]

    USER_MEMORY[user_id].append({"role": "user", "content": message})

    # Limit context to last 10 messages
    conversation_history = USER_MEMORY[user_id][-10:]

    print(f"[DEBUG] Sending conversation history: {conversation_history}")

    for attempt in range(max_retries):
        try:
            payload = {
                "model": model,
                "messages": conversation_history,
                "temperature": 0.7,
                "max_tokens": 1000,
                "top_p": 1,
                "stream": False
            }

            print(f"[DEBUG] Sending payload to Groq: {payload}")
            response = requests.post(GROQ_API_URL, headers=HEADERS, json=payload, timeout=30)

            print(f"[DEBUG] Attempt {attempt + 1} - Status Code: {response.status_code}")
            print(f"[DEBUG] Raw response: {response.text}")

            if response.status_code == 401:
                return "Error: Invalid API key. Please check your Groq API key."
            elif response.status_code != 200:
                print(f"[ERROR] Groq API error: {response.text}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return f"Error: Groq API returned {response.status_code}"

            response_json = response.json()
            print(f"[DEBUG] Parsed response: {response_json}")

            # Check choices
            choices = response_json.get("choices", [])
            if not choices:
                print("[ERROR] Groq response missing 'choices'")
                return "Error: No response from Groq."

            ai_response = choices[0]["message"]["content"].strip()

            # Store the response in memory
            USER_MEMORY[user_id].append({"role": "assistant", "content": ai_response})
            return ai_response

        except requests.exceptions.Timeout:
            print(f"[ERROR] Attempt {attempt + 1}: Request timed out.")
        except requests.exceptions.ConnectionError:
            print(f"[ERROR] Attempt {attempt + 1}: Connection error.")
        except Exception as e:
            print(f"[ERROR] Attempt {attempt + 1}: Unexpected error: {str(e)}")

        if attempt < max_retries - 1:
            time.sleep(2)  # Wait before retrying
        
    return "Error: The AI is not responding. Please try again later."

# Routes
@app.route("/", methods=["GET"])
def home():
    return "Server is running!"

@app.route("/chat", methods=["POST"])
def chat():
    """Handle chat messages and provide responses."""
    data = request.get_json()
    print(f"[DEBUG] Received request data: {data}")

    user_id = data.get("user_id", "default_user")  # Get the user ID or set default
    user_message = data.get("message", "")  # Get the user message

    if not user_message:
        return jsonify({"response": "Please ask something about your career!"})

    ai_response = query_groq(user_id, user_message)
    print(f"[DEBUG] AI Response: {ai_response}")

    return jsonify({"response": ai_response})

# Run the server
if __name__ == "__main__":
    print("[INFO] Starting Flask app at http://127.0.0.1:5000 ...")
    app.run(debug=True)
