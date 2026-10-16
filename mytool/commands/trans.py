#!/usr/bin/env python3
from __future__ import annotations
from openai.types.chat import ChatCompletionMessageParam
from mytool.console import console
from mytool.cache import lookup, save


system_prompt = "给我翻译成中文"

class TransClient:
    def __init__(self, help : str):
        from mytool.config import create_client
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
        
def translate(cmd : str, text: str, refresh: bool = False) -> str | None:
    if not refresh:
        cached = lookup(cmd, text)
        if cached is not None:
            console.print("缓存命中成功", style="bold green")
            return cached

    console.print("缓存命中失败，翻译中", style="bold white on red")
    answer = TransClient(text).chat()
    if answer is not None:
        save(cmd, text, answer)
    return answer
    
if __name__ == '__main__':
    assert("hello,world")
