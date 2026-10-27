from __future__ import annotations

import argparse
import sys

from openai import APIError

from mytool.commands.ask import ask
from mytool.commands.find import find
from mytool.commands.init import init, reinit
from mytool.commands.summary import summary
from mytool.commands.trans import translate
from mytool.hook import hook_fetch

COMMANDS = {
    "trans": "把管道传入的文本翻译成中文，带本机缓存（--refresh 跳过缓存）",
    "find": '根据管道传入的命令帮助回答用法问题，例: docker --help | mytool find "问题"',
    "sum": "总结管道传入的文本",
    "ask": '根据管道传入的文本（如日志）回答问题，例: cat app.log | mytool ask "问题"',
    "init": "创建配置文件、翻译数据库，并在 ~/.zshrc 中安装钩子",
    "reinit": "清空翻译缓存，保留已有 API 配置",
    "help": "打印这条帮助信息",
}


def log(level: str, message: str) -> None:
    stream = sys.stderr if level == "ERROR" else sys.stdout
    print(f"[{level}] {message}", file=stream)


def print_commands(level: str) -> None:
    width = max(len(name) for name in COMMANDS)
    log(level, "可用命令:")
    for name, desc in COMMANDS.items():
        log(level, f"    {name:<{width}} - {desc}")


def verify(text: str) -> bool:
    return len(text.strip()) == 0


def main() -> None:
    argv = sys.argv[1:]

    if not argv:
        print_commands("ERROR")
        log("ERROR", "没有提供命令")
        sys.exit(1)

    if argv[0] in ("help", "-h", "--help"):
        print_commands("INFO")
        return

    if argv[0] not in COMMANDS:
        print_commands("ERROR")
        log("ERROR", f"未知命令 `{argv[0]}`")
        sys.exit(1)

    parser = argparse.ArgumentParser(prog="mytool", description="一个个人工具箱")

    sub_parser = parser.add_subparsers(dest="command", required=True)

    trans_parser = sub_parser.add_parser("trans")
    trans_parser.set_defaults(func=translate)
    trans_parser.add_argument(
        "--refresh",
        action="store_true",
        help="跳过缓存并重新翻译",
    )

    find_parser = sub_parser.add_parser("find")
    find_parser.set_defaults(func=find)
    find_parser.add_argument("question")

    summary_parser = sub_parser.add_parser("sum")
    summary_parser.set_defaults(func=summary)

    ask_parser = sub_parser.add_parser("ask")
    ask_parser.set_defaults(func=ask)
    ask_parser.add_argument("question")

    init_parser = sub_parser.add_parser("init")
    init_parser.set_defaults(func=init)

    reinit_parser = sub_parser.add_parser(
        "reinit",
        help="清空翻译缓存，保留已有 API 配置",
    )
    reinit_parser.set_defaults(func=reinit)

    args = parser.parse_args(argv)

    if args.command == "init" or args.command == "reinit":
        args.func()
        return

    cmd = hook_fetch()

    text = sys.stdin.read()
    if verify(text):
        parser.error("标准输入文本长度为零")

    result = ""

    try:
        if args.command == "trans":
            result = args.func(cmd, text, refresh=args.refresh)

        elif args.command == "sum":
            result = args.func(text)

        elif args.command == "find" or args.command == "ask":
            result = args.func(text, args.question)

    except RuntimeError as error:
        parser.exit(1, f"mytool: {error}\n")

    except APIError as error:
        parser.exit(1, f"mytool: API 请求失败（{type(error).__name__}）\n")

    if result is None:
        parser.exit(1, "mytool: 模型没有返回文本\n")

    print(result)


if __name__ == "__main__":
    main()
