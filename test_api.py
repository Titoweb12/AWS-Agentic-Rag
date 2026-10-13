import os
from dotenv import load_dotenv
import anthropic

load_dotenv()
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

message = client.messages.create(
    model="claude-haiku-5-5",
    max_tokens=50,
    messages=[{"role": "user", "content": "Dis bonjour en une phrase."}],
)
print(message.content[0].text)