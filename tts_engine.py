import pyttsx3

engine = pyttsx3.init()

# Optional settings
engine.setProperty('rate', 170)
engine.setProperty('volume', 1)

def speak(text):
    """
    Convert text to speech
    """
    print(f"Assistant: {text}")
    engine.stop()           # stop previous speech
    engine.say(text)
    engine.runAndWait()

if __name__ == "__main__":
    speak("Hello, I am your voice assistant")