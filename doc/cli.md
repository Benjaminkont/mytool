# cli 维护指南

## 1. 一条命令是怎么跑起来的

在终端输入 `docker --help | mytool find "怎么列出容器"` 后，程序依次经过：

```
pyproject.toml          [project.scripts] mytool = "mytool.cli:main"
   │
   ▼
mytool/cli.py  main()
   ├─ build_parser()     登记所有子命令、参数和帮助文字
   ├─ parse_args()       把命令行字符串解析成 args 对象
   ├─ 处理 help / init / reinit 这类不读管道的命令
   ├─ 检查管道输入，读取标准输入的文本
   └─ 按 args.command 分发，调用 args.func(...)
          │
          ▼
mytool/commands/find.py  find(text, question)   组织提示词、调用模型、返回字符串
          │
          ▼
main() 把返回值 print 出来
```

`python -m mytool` 走的是 `mytool/__main__.py`，它同样调用 `cli.main()`，所以两种启动方式的行为一致。

### 文件分工

| 文件                   | 负责什么                                                                                     |
| ---------------------- | -------------------------------------------------------------------------------------------- |
| `mytool/cli.py`        | 只管命令行：登记子命令、解析参数、检查输入、分发、输出结果和错误                             |
| `mytool/commands/*.py` | 每个子命令的具体逻辑，一般一个命令一个文件                                                   |
| `mytool/config.py`     | 从 `~/.config/mytool/.env` 读取配置，`create_client()` 创建模型客户端                        |
| `mytool/cache.py`      | `trans` 用的本机 SQLite 翻译缓存                                                             |
| `mytool/hook.py`       | `hook_fetch()` 从 Zsh 钩子设置的 `MYTOOL_PIPELINE` 里取出管道左侧的命令；取不到时返回 `None` |
| `mytool/console.py`    | 共用的 rich `Console` 对象                                                                   |

`commands/` 里的 `explain.py`、`how.py`、`log.py` 目前只有说明文字，`man.py` 是空文件，它们都**还没有在 `cli.py` 里登记**，所以 `mytool` 里还看不到这些命令。

## 2. `cli.py` 的三个组成部分

### `MytoolParser`

继承自 `argparse.ArgumentParser`，只重写了 `error()`：出错时先输出 `error: 原因`，再输出**当前这个 parser** 的完整帮助，然后以退出码 2 退出。

子命令的 parser 默认和父 parser 用同一个类，所以 `mytool find` 缺参数时，显示的是 `find` 的帮助，而不是总帮助。

### `add_command()`

登记子命令的小函数，统一设置 `help`、`description`、`epilog` 和 `formatter_class`。新增命令时请用它，不要直接调用 `sub_parser.add_parser()`，否则帮助的格式会不一致。

它返回新建的子命令 parser，用来继续 `add_argument()` 和 `set_defaults()`。注意：函数签名目前标注的是 `-> None`，和实际返回值不符，运行不受影响，但类型检查工具会报错，可以改成 `-> MytoolParser`。

### `build_parser()` 和 `main()`

- `build_parser()` 负责登记所有命令，返回 `(总 parser, 命令表)`。命令表就是 `sub_parser.choices`，一个"命令名 → 子命令 parser"的字典。`help` 命令和"给某个命令报错"都要靠它查找对应的 parser。
- `main()` 负责运行时的流程，见第 1 节的流程图。

## 3. 添加一个新命令

下面以一个虚构的命令 `rewrite` 为例，它的作用是"把管道传入的文本改写得更通顺"。它和 `sum` 一样，只读管道文本，没有别的参数。

### 第 1 步：在 `mytool/commands/` 下写命令逻辑

新建 `mytool/commands/rewrite.py`，参照 `summary.py` 的写法：

```python
from __future__ import annotations

from openai.types.chat import ChatCompletionMessageParam

from mytool.config import create_client

system_prompt = "把用户提供的文本改写得更通顺，保持原意"


class RewriteClient:
    def __init__(self, text: str):
        self.client = create_client()
        self.messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ]

    def chat(self):
        response = self.client.chat.completions.create(
            model="deepseek-flash", messages=self.messages, stream=False
        )
        return response.choices[0].message.content


def rewrite(text: str) -> str | None:
    return RewriteClient(text).chat()
```

命令模块要遵守这几条约定，`main()` 才能统一处理：

- **只接收参数，不自己读标准输入。** 文本由 `main()` 读好后传进来。不要在模块顶层调用 `sys.stdin.read()`，否则一 `import` 就会卡住等输入，`mytool -h` 都跑不了。项目早期的 `trans.py` 就出过这个问题。
- **返回字符串，由 `main()` 负责 `print`。** 拿不到结果时返回 `None`，`main()` 会输出 `error: 模型没有返回文本`。
- **可预见的错误抛 `RuntimeError("中文原因")`。** `main()` 会把它显示成 `error: 中文原因`。`create_client()` 缺少配置时就是这么做的。
- **`create_client()` 要在函数里调用，不要放在模块顶层。** 这样没配置 API key 时，`mytool -h` 仍然能正常显示。

各命令的模型调用代码目前是重复的。`doc/TODO.md` 里计划把它们统一封装成公共模块，统一之后，这一步就只需要写提示词和调用一个公共函数。

### 第 2 步：在 `build_parser()` 里登记

在 `cli.py` 顶部导入：

```python
from mytool.commands.rewrite import rewrite
```

在 `build_parser()` 里，`help_parser` 的前面加上：

```python
    rewrite_parser = add_command(
        sub_parser,
        "rewrite",
        help="把输入的文本改写得更通顺",
        description="把通过管道传入的文本改写得更通顺，保持原意。",
        epilog="示例:\n  cat draft.txt | mytool rewrite",
    )
    rewrite_parser.set_defaults(func=rewrite)
```

命令在总帮助里的显示顺序，就是登记的顺序。`help` 建议始终放在最后。

### 第 3 步：在 `main()` 里分发

在 `main()` 的 `try` 块里，加一个分支，按函数需要的参数调用：

```python
        elif args.command == "rewrite":
            result = args.func(text)
```

如果参数和已有的某个命令完全一样，也可以合并到那个分支，例如 `sum` 的分支写成 `elif args.command in ("sum", "rewrite"):`。

### 第 4 步：验证

先运行下面这些不调用模型的检查：

```sh
python -m py_compile mytool/cli.py mytool/commands/rewrite.py   # 语法检查，没有输出就是通过
python -m mytool                    # 总帮助里应该出现 rewrite
python -m mytool help rewrite       # 应该显示 rewrite 的描述和示例
python -m mytool rewrite            # 没有管道时应该报错，并显示 rewrite 的帮助
```

然后再做一次真实调用，比如 `echo "今天 天气 好 我 出门" | python -m mytool rewrite`。**这一步会请求模型 API，可能产生费用。**

如果日常使用的是 pipx 安装的 `mytool`，改完代码后要运行 `pipx reinstall mytool`，终端里的 `mytool` 才会用上新代码。

### 第 5 步：同步文档

- `README.md` 里的命令表和使用示例
- `AGENTS.md` 里"项目现状"列出的命令
- 本文里如有涉及的地方

## 4. 不同类型命令的写法

### 参数的几种写法

| 想要的效果     | 写法                                                                 | 取值             |
| -------------- | -------------------------------------------------------------------- | ---------------- |
| 必填的位置参数 | `p.add_argument("question", help="...")`                             | `args.question`  |
| 可选的位置参数 | `p.add_argument("question", nargs="?", help="...")`                  | 不传时是 `None`  |
| 开关选项       | `p.add_argument("--refresh", action="store_true", help="...")`       | `True` / `False` |
| 带值的选项     | `p.add_argument("-n", "--lines", type=int, default=100, help="...")` | 自动转换成 `int` |

位置参数的内容里有空格时，用户需要加引号，比如 `mytool find "怎么列出容器"`，建议在 `help` 里提醒一句。

### 不需要管道输入的命令

`main()` 目前假设：除了 `help`、`init`、`reinit` 以外，所有命令都要从管道读取文本，没有管道就报错。

- **不读管道、也没有返回值的命令**（类似 `init`）：在 `init` / `reinit` 那个提前 `return` 的分支里加上命令名即可。
- **不读管道、但需要调用模型并输出结果的命令**（比如 `TODO.md` 里设想的 `explain "命令"`）：需要调整 `main()`，让这类命令跳过读取管道，但仍然走后面的 `try` 和输出逻辑。一种改法：

  ```python
  NO_STDIN_COMMANDS = ("explain",)

  text = ""
  if args.command not in NO_STDIN_COMMANDS:
      if sys.stdin.isatty():
          command_parser.error("没有收到管道输入")
      text = sys.stdin.read()
      if verify(text):
          command_parser.error("管道传入的文本为空")
  ```

- **管道可有可无的命令**（比如 `TODO.md` 里设想的 `how`）：用 `sys.stdin.isatty()` 判断。它返回 `True` 表示没有管道，此时就不读标准输入。

这几种情况目前都还没有实现，上面是建议的写法。

## 5. 帮助文字怎么写

| 参数          | 显示位置                               | 写法建议                                            |
| ------------- | -------------------------------------- | --------------------------------------------------- |
| `help`        | `mytool -h` 的命令列表里，每个命令一行 | 一句话，不加句号                                    |
| `description` | `mytool <命令> -h` 的顶部              | 说清楚输入从哪来（管道还是参数）、输出什么          |
| `epilog`      | `mytool <命令> -h` 的末尾              | 以 `示例:` 开头，每个示例另起一行，前面缩进两个空格 |

`add_command()` 用的是 `RawDescriptionHelpFormatter`，`description` 和 `epilog` 里的 `\n` 会原样换行。不用它的话，argparse 会把多行文字挤成一段。

## 6. 报错和退出码约定

| 场景                                    | 写法                                                                               | 用户看到的                   | 退出码 |
| --------------------------------------- | ---------------------------------------------------------------------------------- | ---------------------------- | ------ |
| 用法错误：缺参数、没有管道、输入为空    | `command_parser.error("原因")`                                                     | `error: 原因` + 该命令的帮助 | 2      |
| 命令名写错、`help` 后面跟了不存在的命令 | argparse 自动处理 / `parser.error(...)`                                            | `error: ...` + 总帮助        | 2      |
| 运行时错误：缺配置、API 失败            | 命令模块里抛 `RuntimeError`，或在 `main()` 里调用 `parser.exit(1, "error: ...\n")` | 只显示 `error: ...`          | 1      |
| 只输入 `mytool`                         | `parser.print_help()` + `sys.exit(1)`                                              | 总帮助                       | 1      |
| 正常结束、`help`、`-h`                  | —                                                                                  | 结果或帮助                   | 0      |

原则：**用户用法写错了，才显示帮助**；网络、配置这类问题和用法无关，只显示原因。

## 7. 修改、重命名或删除命令

- **修改帮助文字或参数**：只改 `build_parser()` 里对应的 `add_command(...)` 和 `add_argument(...)`。如果参数名变了，`main()` 里取值的地方（如 `args.question`）也要一起改。
- **重命名命令**：要改 `add_command` 里的命令名、`main()` 里 `args.command == "..."` 的判断、`epilog` 里的示例，以及第 3 节第 5 步列出的文档。
- **删除命令**：删除 `build_parser()` 里的登记代码、`main()` 里的分支和顶部的 `import`，再决定 `commands/` 里的文件是否保留。

改完之后，至少运行一遍第 3 节第 4 步里不调用模型的那几条检查。

## 8. 已知的小问题

- `usage:`、`options:`、`show this help message and exit`、`invalid choice: ...` 是 argparse 自带的英文，暂时没有汉化。
- 总帮助的"可用命令"下面会多出一行 `<命令>`，这是 argparse 显示子命令组时的固定格式。要去掉需要自定义 formatter。
- `hook_fetch()` 在没有安装 Zsh 钩子、或命令不是简单管道时返回 `None`，这个值会原样传给 `translate()` 当作缓存的键。`cache.py` 里 `lookup()` 和 `save()` 的参数标注是 `cmd: str`，`None` 传进去时缓存是否正常工作，还没有验证过。
- 仓库没有自动化测试。上面的检查命令需要手动运行。
