#!/usr/bin/env python3
from __future__ import annotations
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam
from mytool.config import create_client
from mytool.cache import lookup, save


system_prompt = "给我翻译成中文"

class TransClient:
    def __init__(self, help : str):
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
            reasoning_effort="high",
            extra_body={"thinking": {"type": "enabled"}},
            messages=self.messages,
            stream=False
        )
            
        answer = response.choices[0].message.content
        return answer
        
def translate(text: str, refresh: bool = False) -> str | None:
    if not refresh:
        cached = lookup(text)
        if cached is not None:
            return cached

    answer = TransClient(text).chat()
    if answer is not None:
        save(text, answer)
    return answer
    
if __name__ == '__main__':
    assert("hello,world")
