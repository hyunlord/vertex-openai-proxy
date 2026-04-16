from openai import OpenAI


client = OpenAI(
    base_url="http://127.0.0.1:8080/v1",
    api_key="replace-with-a-random-token",
)

response = client.chat.completions.create(
    model="google/gemini-2.5-flash",
    messages=[
        {"role": "system", "content": "You are a careful assistant."},
        {
            "role": "user",
            "content": "What is the weather in Seoul? Use the provided tool if needed.",
        },
    ],
    tools=[
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get the current weather for a city.",
            },
        }
    ],
    tool_choice="auto",
)

message = response.choices[0].message
print(message)
