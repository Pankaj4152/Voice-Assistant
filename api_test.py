from google import genai

client = genai.Client(api_key="AIzaSyDJE5ppVHpUV0jz0jcFpBt6aafqFEf3ju4")

resp = client.models.generate_content(
    model="gemini-2.0-flash",
    contents="Hello"
)

print(resp.text)