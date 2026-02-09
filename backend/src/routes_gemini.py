"""
Gemini Chat API Routes
======================
Server-side endpoint that proxies chat requests to Gemini API.
Keeps API key secure on the backend.
"""

import os
import logging
from flask import Flask, request, jsonify

logger = logging.getLogger(__name__)

# System instruction for the TradeRisk assistant
SYSTEM_INSTRUCTION = """You are TradeRisk, a Canadian tariff risk assistant. ALWAYS give direct answers.

CURRENT DATA (use this - do NOT ask for more details):
• Iron & Steel: 92.6 risk score, 25% US tariff, $9.9B exports
• Vehicles: 91.3 risk score, 25% US tariff, $66.6B exports  
• Wood/Lumber: 69.1 risk score, 20% US tariff, $11.8B exports
• Aluminum: 57.8 risk score, 10% US tariff
• Furniture: 57.8 risk score, 15% US tariff, $4.5B exports
• Machinery: 10% US tariff
• Mineral Fuels: 10% US tariff

Risk scores: 0-100 (higher = more exposed to tariff damage)
Most affected provinces: Ontario (auto/steel), BC (lumber), Quebec (aluminum), Alberta (energy)
~75% of Canadian exports go to the US.

CRITICAL RULES:
1. NEVER ask clarifying questions. Answer with the data you have.
2. If asked "what sectors are at risk" → list the top sectors with their scores.
3. Be concise: 2-3 sentences or a short bullet list.
4. If you lack specific data, give a general answer using what you know."""


def register_gemini_routes(app: Flask) -> None:
    """Register Gemini chat routes on the Flask app."""
    
    @app.route("/api/chat", methods=["POST"])
    def chat():
        """
        Chat endpoint that proxies to Gemini API.
        
        Request body:
            {
                "messages": [
                    {"role": "user"|"assistant", "content": "string"},
                    ...
                ]
            }
        
        Response:
            {"reply": "string"}
        """
        # Validate request
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body required"}), 400
        
        messages = data.get("messages")
        if not messages or not isinstance(messages, list):
            return jsonify({"error": "messages array required"}), 400
        
        if len(messages) == 0:
            return jsonify({"error": "messages cannot be empty"}), 400
        
        # Validate message format
        for i, msg in enumerate(messages):
            if not isinstance(msg, dict):
                return jsonify({"error": f"messages[{i}] must be an object"}), 400
            if "role" not in msg or "content" not in msg:
                return jsonify({"error": f"messages[{i}] must have 'role' and 'content'"}), 400
            if msg["role"] not in ("user", "assistant"):
                return jsonify({"error": f"messages[{i}].role must be 'user' or 'assistant'"}), 400
        
        # Get API key
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            logger.error("GEMINI_API_KEY not set in environment")
            return jsonify({"error": "Chat service not configured"}), 503
        
        try:
            import google.generativeai as genai
            
            # Configure the SDK
            genai.configure(api_key=api_key)
            
            # Create the model with system instruction
            model = genai.GenerativeModel(
                model_name="gemini-2.0-flash",
                system_instruction=SYSTEM_INSTRUCTION
            )
            
            # Convert messages to Gemini format
            # Gemini expects alternating user/model messages
            history = []
            for msg in messages[:-1]:  # All but the last message go to history
                role = "user" if msg["role"] == "user" else "model"
                history.append({
                    "role": role,
                    "parts": [msg["content"]]
                })
            
            # Start chat with history
            chat_session = model.start_chat(history=history)
            
            # Send the last message
            last_message = messages[-1]["content"]
            response = chat_session.send_message(last_message)
            
            reply = response.text
            
            return jsonify({"reply": reply})
            
        except ImportError:
            logger.error("google-generativeai package not installed")
            return jsonify({"error": "Chat service not available"}), 503
        except Exception as e:
            logger.error(f"Gemini API error: {type(e).__name__}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return jsonify({"error": f"AI error: {str(e)}"}), 500
