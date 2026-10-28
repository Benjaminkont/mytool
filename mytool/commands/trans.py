"""
看不懂英文输出，需通读中文全文
命令 | mytool trans
命令 | mytool trans --refresh	- 必须有管道输入。

- 提示词约束：忠实翻译为中文，保留命令名、子命令名、参数选项（如 -v、--help）原样不乱译，保持原有缩进排版。
- 命中本地缓存时瞬间输出；未命中时流式打印并在完成后写入缓存。
"""

from __future__ import annotations

from openai.types.chat import ChatCompletionMessageParam

from mytool.cache import lookup, save
from mytool.console import console

system_prompt = "给我翻译成中文"


class TransClient:
    def __init__(self, help: str):
        from mytool.config import create_client

        self.client = create_client()

        self.messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": help},
        ]

    def chat(self):
        response = self.client.chat.completions.create(
            model="deepseek-flash",
            reasoning_effort="high",
            extra_body={"thinking": {"type": "enabled"}},
            messages=self.messages,
            stream=False,
        )

        answer = response.choices[0].message.content
        return answer


def translate(cmd: str, text: str, refresh: bool = False) -> str | None:
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


if __name__ == "__main__":
    raise NotImplementedError("hello world")
