"""根据命令帮助文本或当前系统环境回答命令行使用问题。"""

from __future__ import annotations

import os
import platform

from openai.types.chat import ChatCompletionMessageParam


SYSTEM_PROMPT = """
你是一个命令行使用助手。

请根据用户提供的命令帮助文本或当前系统环境回答问题。
优先给出可以直接复制执行的命令，并用一句话解释用途。
不要编造帮助文本中不存在的参数。
如果信息不足，请明确说明。
回答使用中文。
""".strip()


def build_user_prompt(
    help_text: str | None,
    question: str,
    command: str | None,
) -> str:
    if help_text is None:
        system = platform.system() or "未知系统"
        release = platform.release() or "未知版本"
        shell = os.environ.get("SHELL", "未知 Shell")
        return (
            f"当前系统：{system} {release}\n"
            f"当前 Shell：{shell}\n\n"
            f"用户问题：\n{question}"
        )

    return (
        f"来源命令：{command or '未知'}\n\n"
        f"命令帮助文本：\n---\n{help_text}\n---\n\n"
        f"用户问题：\n{question}"
    )


class HowClient:
    def __init__(
        self,
        help_text: str | None,
        question: str,
        command: str | None,
    ) -> None:
        from mytool.config import create_client

        self.client = create_client()
        self.messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": build_user_prompt(help_text, question, command),
            },
        ]

    def chat(self) -> str | None:
        response = self.client.chat.completions.create(
            model="deepseek-flash",
            reasoning_effort="high",
            extra_body={"thinking": {"type": "enabled"}},
            messages=self.messages,
            stream=False,
        )
        return response.choices[0].message.content


def how(
    help_text: str | None,
    question: str,
    *,
    command: str | None = None,
) -> str | None:
    return HowClient(help_text, question, command).chat()
