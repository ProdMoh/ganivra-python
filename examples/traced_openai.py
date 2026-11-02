"""Group multiple direct OpenAI calls into one observable execution."""

import os

import ganivra
from openai import OpenAI

ganivra.init(
    api_key=os.environ["GANIVRA_API_KEY"],
    environment="development",
)
client = OpenAI()

with ganivra.trace(
    workflow="support_answer",
    feature="support_chatbot",
    customer_id="acme",
):
    response = client.responses.create(
        model="gpt-6.1-sol",
        input="Explain how to reset a password in one short paragraph.",
    )

print(response.output_text)
ganivra.flush()
