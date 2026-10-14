#!/usr/bin/env python3
from __future__ import annotations
from openai.types.chat import ChatCompletionMessageParam

from mytool.config import create_client


system_prompt = """总结提供的内容
"""

class SummaryClient:
    def __init__(self,help : str):
        self.client = create_client()
        self.messages : list[ChatCompletionMessageParam] = [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": help
            }
        ]
        
    def chat(self):
        response = self.client.chat.completions.create(
            model="deepseek-flash",
            messages=self.messages,
            stream=False
        )
            
        answer = response.choices[0].message.content
        return answer
        
def summary(text : str) -> str | None:
    Client = SummaryClient(text)
    return Client.chat()
    
if __name__ == '__main__':
    assert("hello,world")
