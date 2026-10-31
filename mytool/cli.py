from __future__ import annotations

import argparse
import sys
from typing import NoReturn

from openai import APIError

from mytool.commands.explain import explain
from mytool.commands.how import how
from mytool.commands.init import init, reinit
from mytool.commands.log import log
from mytool.commands.trans import translate
from mytool.commands.woman import woman
from mytool.hook import hook_fetch


class MytoolParser(argparse.ArgumentParser):
    # 格式化错误信息
    def error(self, message: str) -> NoReturn:
        sys.stderr.write(f"error: {message}\n\n")
        self.print_help(sys.stderr)
        self.exit(2)


# 添加子命令
def add_command(
    sub_parser,
    name: str,
    help: str,
    description: str,
    epilog: str,
) -> MytoolParser:
    return sub_parser.add_parser(
        name,
        help=help,
        description=description,
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )


# 启动！
def build_parser() -> tuple[MytoolParser, dict[str, MytoolParser]]:
    parser = MytoolParser(
        prog="mytool",
        usage="mytool <命令> [<参数>]",
        description="把终端里的文本通过管道交给 DeepSeek，进行翻译、总结或问答。",
        epilog=(
            "首次使用请先运行 mytool init。\n"
            "运行 'mytool help <命令>' 或 'mytool <命令> -h' 查看某个命令的用法。"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    sub_parser = parser.add_subparsers(
        dest="command", title="可用命令", metavar="<命令>", prog="mytool"
    )

    trans_parser = add_command(
        sub_parser,
        "trans",
        help="把输入的文本翻译成中文",
        description="把通过管道传入的文本翻译成中文。译文会缓存在本机，再次执行同一条命令时直接复用。",
        epilog="示例:\n  docker --help | mytool trans\n  docker --help | mytool trans --refresh",
    )
    trans_parser.set_defaults(func=translate)
    trans_parser.add_argument(
        "--refresh",
        action="store_true",
        help="跳过缓存并重新翻译",
    )

    init_parser = add_command(
        sub_parser,
        "init",
        help="创建配置文件、翻译数据库并安装 Zsh 钩子",
        description=(
            "在 ~/.config/mytool/ 下创建 .env 配置模板和翻译数据库，"
            "并在 ~/.zshrc 中加入钩子。已存在的配置不会被覆盖。"
        ),
        epilog="示例:\n  mytool init",
    )
    init_parser.set_defaults(func=init)

    reinit_parser = add_command(
        sub_parser,
        "reinit",
        help="清空翻译缓存，保留已有 API 配置",
        description="重新执行 init 的准备工作，然后清空翻译缓存。已有的 API 配置会保留。",
        epilog="示例:\n  mytool reinit",
    )
    reinit_parser.set_defaults(func=reinit)

    woman_parser = add_command(
        sub_parser,
        "woman",
        help="在终端中查看 man 手册",
        description="按手册名称查看中文 man 手册，无需管道输入。翻译与展示功能尚未实现。",
        epilog=(
            "示例:\n"
            "  mytool woman ls\n"
            "  mytool woman 3 printf\n"
            "  mytool woman ls --refresh\n"
            "  mytool woman ls --original"
        ),
    )
    woman_parser.set_defaults(func=woman)
    woman_parser.add_argument(
        "section",
        nargs="?",
        help="指定手册章节号",
    )
    woman_parser.add_argument(
        "manual_name",
        help="要查看的手册名称",
    )
    woman_mode = woman_parser.add_mutually_exclusive_group()
    woman_mode.add_argument(
        "--refresh",
        action="store_true",
        help="跳过缓存并重新翻译",
    )
    woman_mode.add_argument(
        "--original",
        action="store_true",
        help="显示原始 man 手册，不进行翻译",
    )

    help_parser = add_command(
        sub_parser,
        "help",
        help="显示 mytool 或某个命令的帮助",
        description="不带参数时显示 mytool 的帮助；带上命令名时显示该命令的帮助。",
        epilog="示例:\n  mytool help\n  mytool help find",
    )
    help_parser.add_argument("topic", nargs="?", metavar="命令", help="要查看的命令名")

    return parser, sub_parser.choices


def verify(text: str) -> bool:
    return len(text.strip()) == 0


def read_pipe(command_parser: MytoolParser) -> str:
    if sys.stdin.isatty():
        command_parser.error("没有管道输入！")

    text = sys.stdin.read()
    if verify(text):
        command_parser.error("管道输入的内容为空！")
    return text


def main() -> None:
    parser, commands = build_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "help":
        if args.topic is None:
            parser.print_help()
        elif args.topic in commands:
            commands[args.topic].print_help()
        else:
            parser.error(f"'{args.topic}' 不是 mytool 的命令")
        return

    result: str | None = None

    try:
        if args.command == "init" or args.command == "reinit":
            args.func()
            return

        if args.command == "woman":
            args.func(
                args.manual_name,
                section=args.section,
                refresh=args.refresh,
                original=args.original,
            )
            return

        text = read_pipe(commands[args.command])

        if args.command == "trans":
            cmd = hook_fetch()
            result = args.func(cmd, text, refresh=args.refresh)

        elif args.command == "sum":
            result = args.func(text)

        elif args.command == "find" or args.command == "ask":
            result = args.func(text, args.question)

        elif args.command == "log":
            result = args.func(
                text,
                question=args.question,
                command=cmd,
                apply_filter=args.apply_filter,
                no_filter=args.no_filter,
            )

    except RuntimeError as error:
        parser.exit(1, f"error: {error}\n")

    except APIError as error:
        parser.exit(1, f"error: API 请求失败（{type(error).__name__}）: {error}\n")

    if result is None:
        parser.exit(1, "error: 模型没有返回文本\n")

    print(result)


if __name__ == "__main__":
    main()
