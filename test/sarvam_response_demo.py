"""
Sarvam AI response demo (text-in → text-out).

Prereqs:
- pip install sarvamai
- set env var SARVAM_API_KEY in `.env`

Run:
    python -m test.sarvam_response_demo
"""

import os
from dotenv import load_dotenv


def main():
    load_dotenv()
    key = os.getenv("SARVAM_API_KEY", "").strip()
    if not key:
        print("Missing SARVAM_API_KEY in environment.")
        return

    try:
        from sarvamai import SarvamAI
    except Exception as e:
        print("sarvamai not installed:", e)
        return

    client = SarvamAI(api_subscription_key=key)

    print("Sarvam demo. Type a prompt and press Enter (blank to exit).")
    while True:
        prompt = input("> ").strip()
        if not prompt:
            break

        # The sarvamai SDK surface can differ by version; try common entrypoints.
        try:
            if hasattr(client, "chat") and hasattr(client.chat, "completions"):
                resp = client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model=getattr(client, "default_model", None) or "sarvam",
                )
                text = str(resp)
            elif hasattr(client, "text") and hasattr(client.text, "generate"):
                resp = client.text.generate(input=prompt)
                text = getattr(resp, "output", None) or str(resp)
            elif hasattr(client, "text") and hasattr(client.text, "translate"):
                resp = client.text.translate(
                    input=prompt,
                    source_language_code="auto",
                    target_language_code="en-IN",
                    speaker_gender="Male",
                )
                text = str(resp)
            else:
                text = "Sarvam SDK method not found in this version."
        except Exception as e:
            text = f"Error: {e}"

        print(text)


if __name__ == "__main__":
    main()

