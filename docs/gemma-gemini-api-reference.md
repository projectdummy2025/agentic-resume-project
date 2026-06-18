# How to use Gemma 4 with the Gemini API

Reference: [How to use Gemma 4 with the Gemini API and Google AI Studio](https://www.philschmid.de/gemma-4-gemini-api)

Google's Gemma 4 family of open models is available through the Gemini API and Google AI Studio. These models bring advanced reasoning, native function calling, multimodal understanding, and 256K context windows to an open, Apache 2.0-licensed package.

Two models are available through the Gemini API today:
- `gemma-4-26b-a4b-it`
- `gemma-4-31b-it`

## Getting Started

Install the Python SDK:
```bash
pip install google-genai
```

Set your API key as an environment variable:
```bash
export GEMINI_API_KEY="your-api-key"
```

## Text Generation

Generate text with Gemma 4:
```python
from google import genai

client = genai.Client()

response = client.models.generate_content(
    model="gemma-4-26b-a4b-it",
    contents="Compare ramen and udon in 3 bullet points: broth, noodle texture, and best season to eat."
)
print(response.text)
```

Pass a system instruction to set the model's behavior:
```python
from google import genai
from google.genai import types

client = genai.Client()

response = client.models.generate_content(
    model="gemma-4-31b-it",
    config=types.GenerateContentConfig(
        system_instruction="You are a wise Kyoto tea master. Speak calmly and poetically, using nature metaphors. Keep answers under 3 sentences."
    ),
    contents="What is the purpose of the tea ceremony?"
)
print(response.text)
```

## Multi-turn Conversations

The SDK provides a chat interface that tracks conversation history automatically:
```python
from google import genai

client = genai.Client()
chat = client.chats.create(model="gemma-4-26b-a4b-it")

response = chat.send_message("What are the three most famous castles in Japan?")
print(response.text)

response = chat.send_message("Which one should I visit in spring for cherry blossoms?")
print(response.text)
```

## Image Understanding

Pass an image alongside your text prompt:
```python
from google import genai
from google.genai import types

client = genai.Client()

with open("path/to/image.png", "rb") as f:
    image_bytes = f.read()

response = client.models.generate_content(
    model="gemma-4-26b-a4b-it",
    contents=[
        types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
        "Describe this image in 2-3 sentences as if writing a caption for a Japanese travel magazine."
    ]
)
print(response.text)
```

## Function Calling

Define tools as function declarations. The model decides when to call them:
```python
from google import genai
from google.genai import types

# Define the function declaration
get_weather = {
    "name": "get_weather",
    "description": "Get current weather for a given location.",
    "parameters": {
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "City and state, e.g. 'San Francisco, CA'",
            },
        },
        "required": ["location"],
    },
}

client = genai.Client()
tools = types.Tool(function_declarations=[get_weather])
config = types.GenerateContentConfig(tools=[tools])

response = client.models.generate_content(
    model="gemma-4-26b-a4b-it",
    contents="Should I bring an umbrella to Kyoto today?",
    config=config,
)

# The model returns a function call instead of text
if response.candidates[0].content.parts[0].function_call:
    fc = response.candidates[0].content.parts[0].function_call
    print(f"Function: {fc.name}")
    print(f"Arguments: {fc.args}")
```

## Google Search

Ground Gemma 4 responses in real-time web data with Google Search:
```python
from google import genai
from google.genai import types

client = genai.Client()

response = client.models.generate_content(
    model="gemma-4-26b-a4b-it",
    contents="What are the dates for cherry blossom season in Tokyo this year?",
    config=types.GenerateContentConfig(
        tools=[{"google_search":{}}]
    ),
)

print(response.text)

# Access grounding metadata for citations
for chunk in response.candidates[0].grounding_metadata.grounding_chunks:
    print(f"Source: {chunk.web.title} — {chunk.web.uri}")
```
