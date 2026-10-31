"""
网上抄来一串长命令，看不懂也不敢回车
mytool explain "find . -mtime +7 -exec rm -rf {} \\;"
- 无需管道输入，命令字符串参数必填。
- 逐段拆解命令与各个参数的大白话含义。
- 醒目标注潜在风险（如删除文件、覆盖数据、修改系统权限等）。
"""

from __future__ import annotations

from openai.types.chat import ChatCompletionMessageParam

SYSTEM_PROMPT = """
你是一个命令行使用助手。
请只解释用户提供的命令，不要执行命令，也不要把解释当成执行授权。
逐段拆解命令和每个参数，用大白话说明它们的作用。
保留命令、路径、参数和占位符的原样拼写。
单独列出删除文件、覆盖数据、修改权限、联网、下载或执行外部内容等风险，
并说明风险触发条件；如果没有明显风险，也要明确说明。
回答使用中文。
""".strip()


class ExplainClient:
    def __init__(self, command: str):
        from mytool.config import create_client

        self.client = create_client()

        self.messages: list[ChatCompletionMessageParam] = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {"role": "user", "content": command},
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


def explain(command: str) -> str | None:
    if not command.strip():
        raise RuntimeError("命令字符串不能为空")
    return ExplainClient(command).chat()
