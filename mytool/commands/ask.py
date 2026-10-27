from __future__ import annotations

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

from mytool.config import create_client

system_prompt = """你是日志分析专家，能通过日志快速分析问题原因
"""


class AskClient:
    def __init__(self, help: str, question: str):
        self.client = create_client()

        self.messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"<help>\n{help}\n</help>\n<question>\n{question}\n</question>",
            },
        ]

    def chat(self):
        response = self.client.chat.completions.create(
            model="deepseek-flash", messages=self.messages, stream=False
        )

        answer = response.choices[0].message.content
        return answer


def ask(text: str, question: str) -> str | None:
    Client = AskClient(text, question)
    return Client.chat()


if __name__ == "__main__":
    raise NotImplementedError("hello,world")
