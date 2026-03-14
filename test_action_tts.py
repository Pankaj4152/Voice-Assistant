from tts_engine import speak

result = {
    "success": True,
    "response_text": "Opening browser"
}

if result.get("response_text") and isinstance(result["response_text"], str):
    speak(result["response_text"])