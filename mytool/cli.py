from __future__ import annotations

import argparse
import sys
from openai import APIError
from mytool.commands.trans import translate
from mytool.commands.find import find
from mytool.commands.summary import summary
from mytool.commands.ask import ask

def verify(text : str) -> bool:
    if(len(text.strip()) == 0):
        return True
    else:
        return False



def main():
    parser = argparse.ArgumentParser("一个个人工具箱")


    sub_parser = parser.add_subparsers(
        dest="command",
        required=True
    )

    trans_parser = sub_parser.add_parser("trans")
    trans_parser.set_defaults(func=translate)
    trans_parser.add_argument("--refresh", action="store_true", help="跳过缓存并重新翻译")

    find_parser = sub_parser.add_parser("find")
    find_parser.set_defaults(func=find)
    find_parser.add_argument("question")

    summary_parser = sub_parser.add_parser("sum")
    summary_parser.set_defaults(func=summary)

    ask_parser = sub_parser.add_parser("ask")
    ask_parser.set_defaults(func=ask)
    ask_parser.add_argument("question")

    args = parser.parse_args()

    text = sys.stdin.read()
    if verify(text):
        parser.error("标准输入文本长度为零")

    result = ""

    try:
        if args.command == "trans":
            result = args.func(text, refresh=args.refresh)

        elif args.command == "sum":
            result = args.func(text)

        elif(args.command == "find" or args.command == "ask"):
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
