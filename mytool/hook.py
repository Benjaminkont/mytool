import os
import re


def hook_fetch() -> str | None:
    """读取钩子提供的命令，提取简单管道的左侧；获取不到时返回 None。"""
    pipeline = os.getenv("MYTOOL_PIPELINE")
    if not pipeline:
        return None

    match = re.match(r"^([^|]+)\|", pipeline)
    if match is None:
        return None

    source = match.group(1).strip()
    return source or None


if __name__ == "__main__":
    source = hook_fetch()
    if source is None:
        print("未获取到命令")
    else:
        print(source)
