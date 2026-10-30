from __future__ import annotations

import argparse
import sys
from typing import NoReturn

from openai import APIError


from mytool.commands.init import init, reinit
from mytool.commands.trans import translate
from mytool.commands.how import how
from mytool.commands.explain import explain
from mytool.commands.log import log
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

    help_parser = add_command(
        sub_parser,
        "help",
        help="显示 mytool 或某个命令的帮助",
        description="不带参数时显示 mytool 的帮助；带上命令名时显示该命令的帮助。",
        epilog="示例:\n  mytool help\n  mytool help find",
    )
    help_parser.add_argument("topic", nargs="?", metavar="命令", help="要查看的命令名")

    woman_parser = add_command(
        sub_parser,
        "woman",
        help="在终端中查看 man 手册",
        description="按手册名称查看中文 man 手册，无需管道输入。翻译与展示功能尚未实现。",
        epilog=(
            "示例:\n"
            "  mytool woman ls\n"
            "  mytool woman printf --section 3\n"
            "  mytool woman ls --refresh\n"
            "  mytool woman ls --original"
        ),
    )
    woman_parser.set_defaults(func=woman)
    woman_parser.add_argument("manual_name", help="要查看的手册名称")
    woman_parser.add_argument("--section", help="指定手册章节号")
    woman_mode = woman_parser.add_mutually_exclusive_group()
    woman_mode.add_argument(
        "--refresh", action="store_true", help="跳过缓存并重新翻译"
    )
    woman_mode.add_argument(
        "--original", action="store_true", help="显示原始 man 手册，不进行翻译"
    )

    how_parser = add_command(
        sub_parser,
        "how",
        help="根据命令帮助文本回答用法问题（侧重命令行工具）",
        description=(
            "把某个命令的帮助文本通过管道传入，再用参数提出问题，回答该命令怎么用。"
            "如果没有管道输入，则直接根据当前系统环境给出可复制的命令与一句话解释。"
        ),
        epilog='示例:\n  docker --help | mytool how "怎么用 compose"\n  mytool how "怎么看 8080 端口被谁占了"',
    )

    how_parser.set_defaults(func=how)
    how_parser.add_argument("question", help="想问的问题，含空格时记得加引号")

    explain_parser = add_command(
        sub_parser,
        "explain",
        help="逐段拆解命令字符串并解释各个参数的含义",
        description=(
            "把用户提供的命令字符串逐段拆解，并用大白话解释每个参数的含义。"
            "如果命令中有潜在风险（如删除文件、覆盖数据、修改系统权限等），会醒目标注。"
        ),
        epilog='示例:\n  mytool explain "find . -mtime +7 -exec rm -rf {} \\;"',
    )
    explain_parser.set_defaults(func=explain)
    explain_parser.add_argument(
        "command_text",
        help="要解释的命令字符串，含空格时记得加引号",
    )

    log_parser = add_command(
        sub_parser,
        "log",
        help="分析管道传入的命令输出或日志",
        description=(
            "必须通过管道传入日志。没有问题时自动总结异常；"
            "提供问题时针对该问题分析。"
        ),
        epilog=(
            "示例:\n"
            "  journalctl -n 100 | mytool log\n"
            "  docker ps -a | mytool log \"为什么退出了\""
        ),
    )
    log_parser.set_defaults(func=log)
    log_parser.add_argument(
        "question",
        nargs="?",
        help="想问的问题，含空格时记得加引号",
    )
    log_mode = log_parser.add_mutually_exclusive_group()
    log_mode.add_argument(
        "--filter",
        dest="apply_filter",
        action="store_true",
        help="强制使用本地压缩后的日志证据",
    )
    log_mode.add_argument(
        "--no-filter",
        dest="no_filter",
        action="store_true",
        help="强制把完整日志传给模型",
    )

    return parser, sub_parser.choices


def verify(text: str) -> bool:
    return len(text.strip()) == 0


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

    if args.command == "init" or args.command == "reinit":
        args.func()
        return

    if args.command == "woman":
        try:
            args.func(
                args.manual_name,
                section=args.section,
                refresh=args.refresh,
                original=args.original,
            )
        except RuntimeError as error:
            parser.exit(1, f"error: {error}\n")
        return

    command_parser = commands[args.command]

    cmd = hook_fetch()

    # 只有标准输入不是终端时才读取，避免无管道运行时一直等待输入。
    has_stdin = not sys.stdin.isatty()
    text: str | None = None

    if has_stdin:
        text = sys.stdin.read()
        if verify(text):
            command_parser.error("管道传入的文本为空")
    elif args.command not in ("how", "explain"):
        command_parser.error("没有收到管道输入")

    result = ""

    try:
        if args.command == "how":
            result = args.func(text, args.question, command=cmd)

        elif args.command == "explain":
            result = args.func(args.command_text)

        elif args.command == "trans":
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
        parser.exit(1, f"error: API 请求失败（{type(error).__name__}）\n")

    if result is None:
        parser.exit(1, "error: 模型没有返回文本\n")

    print(result)


if __name__ == "__main__":
    main()
