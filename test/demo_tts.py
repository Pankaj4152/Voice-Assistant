"""
Minimal TTS demo.

Run:
    python -m test.demo_tts
"""

def main():
    text = "TTS demo is working. Intent and actions can now speak responses."
    try:
        import pyttsx3
        tts = pyttsx3.init()
        tts.say(text)
        tts.runAndWait()
        print("Spoke:", text)
    except Exception as e:
        print("TTS unavailable:", e)
        print("Text:", text)


if __name__ == "__main__":
    main()

