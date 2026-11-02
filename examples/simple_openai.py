"""Existing OpenAI usage with two-line Ganivra initialization."""

import os

import ganivra

ganivra.init(
    api_key=os.environ["GANIVRA_API_KEY"],
    environment="development",
)

from openai import OpenAI

client = OpenAI()
response = client.responses.create(model="gpt-6.1-sol", input="Hello")
print(response.output_text)
ganivra.flush()
