# mytool

一个从终端管道读取文本，并用 DeepSeek 处理文本的 Python 命令行工具箱。

## 项目简介

`mytool` 用于在终端中直接处理已有的文本或命令输出，省去手动复制到聊天窗口的步骤。目前提供中文翻译、文本摘要、基于命令帮助文本的问答，以及日志分析问答。所有命令都从标准输入读取文本；需要提问的命令把问题作为命令参数。

项目仍处于原型阶段。Python 语法和命令分发曾做过本地检查，但仓库尚无自动化测试，也没有在本项目中确认真实 API 返回结果。运行模型请求可能产生费用。

## 技术栈

- Python 3.10+；命令行参数使用标准库 `argparse` 解析。
- `openai`：调用兼容 OpenAI 接口的 DeepSeek 服务。
- `python-dotenv`：从用户配置文件加载 API 配置。
- `httpx2[socks]`：当前在 `pyproject.toml` 中声明的网络依赖。
- `pipx`：可选，用于将工具安装为独立的终端命令。
- SQLite（Python 标准库）：在本机按原文缓存翻译结果。

## 安装与配置

需要 Python 3.10 或更新版本。先取得源码；如果仓库已托管，请将下面的占位符换成实际仓库地址：

```sh
git clone <仓库地址>
cd mytool
```

如果源码已在本机，直接进入项目目录即可。开发时可以在虚拟环境中安装：

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e .
```

要在其他目录直接使用 `mytool` 命令，也可以在项目目录运行 `pipx install .`。修改源码后，普通的 pipx 安装需要重新安装才能使用新版本。这些安装命令会从包仓库下载依赖；本 README 编写时没有重新执行安装。

在 `~/.config/mytool/.env` 中填写配置：

```dotenv
DEEPSEEK_API_KEY=你的_API_Key
BASE_URL=https://api.deepseek.com
```

请勿将真实密钥提交到仓库。程序也会读取同名环境变量；配置缺失时会显示错误。当前代码中的模型名为 `deepseek-flash`，实际调用还取决于所用服务是否支持该模型。

## 快速使用

安装后，先查看命令帮助；这一步不会调用模型 API：

```sh
mytool --help
python -m mytool --help  # 在已安装项目的 Python 环境中运行
```

四个子命令都需要非空的标准输入。以下命令会发起 API 请求：

```sh
# 翻译成中文
printf 'Hello, world!\n' | mytool trans

# 相同的原文会直接使用缓存；输出变化时会重新翻译并保存新记录
docker --help | mytool trans

# 即使输出未变，也重新翻译并更新缓存
docker --help | mytool trans --refresh

# 仅根据提供的帮助文本回答命令用法问题
git --help | mytool find "怎样查看帮助？"

# 总结文本
printf '第一段内容。第二段内容。\n' | mytool sum

# 根据日志文本回答问题
printf 'ERROR: connection timed out\n' | mytool ask "可能是什么原因？"
```

`find` 只应依据传入的帮助文本作答；文本不足以确定用法时，它的提示词要求说明无法确定。模型是否始终遵守该约束尚未经过真实请求验证。

`trans` 按完整的标准输入文本进行精确匹配，包括空格和换行；只有原文完全相同才会使用缓存。缓存文件位于 `~/.local/share/mytool/trans.db`；只有翻译成功才会写入。`--refresh` 会跳过查询，并在翻译成功后更新该原文的译文。修改源码后若通过普通的 pipx 安装，需重新安装才能使用新版本。

## 目录结构

```text
mytool/
├── pyproject.toml         # 项目元数据、依赖和 mytool 命令入口
├── README.md              # 项目说明
├── doc/                   # 开发阶段记录
└── mytool/
    ├── cli.py             # 参数解析、标准输入检查和命令分发
    ├── config.py          # 读取配置并创建 API 客户端
    ├── cache.py           # SQLite 翻译缓存
    ├── __main__.py        # python -m mytool 的入口
    └── commands/
        ├── trans.py       # 中文翻译
        ├── find.py        # 命令帮助问答
        ├── summary.py     # 文本摘要，对应 sum 子命令
        └── ask.py         # 日志分析问答
```

## 贡献指南

欢迎报告问题或改进文档和代码。仓库公开托管后，可通过 Issue 描述复现步骤、预期结果和实际结果；提交代码时，请从独立分支创建 Pull Request，说明改动目的和本地验证结果。报告问题时请删除日志中的密钥等敏感信息。当前仓库尚无自动化测试配置，也尚未记录公开仓库地址。

## 开源协议

当前仓库没有 `LICENSE` 文件，尚未声明开源许可证。选择并添加许可证之前，不应将本项目视为已按 MIT、GPL 等协议授权再分发。
