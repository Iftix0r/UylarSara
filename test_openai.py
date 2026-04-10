import os
import openai
from dotenv import load_dotenv

load_dotenv()
try:
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"), timeout=2.5)
    prompt = "Test prompt"
    # test
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=20,
        temperature=0.8,
    )
    print("Success:", response.choices[0].message.content)
except Exception as e:
    print("Error:", repr(e))
