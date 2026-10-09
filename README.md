# mytool

一个帮助阅读终端技术文本的 Python 命令行工具箱，通过 DeepSeek 提供中文翻译、摘要和问答，并在本机复用已有译文。

## 项目简介

`mytool` 用于在终端中直接处理已有的文本或命令输出，省去手动复制到聊天窗口的步骤。最明确的日常场景是读懂 `docker --help` 等英文命令帮助：把输出通过管道交给工具，得到中文译文，之后阅读相同原文时复用本机缓存，减少重复请求带来的等待和费用。

目前提供中文翻译、文本摘要、基于命令帮助文本的问答，以及日志分析问答。所有命令都从标准输入读取文本；需要提问的命令把问题作为命令参数。程序读完全部输入后处理，模型结果一次性输出。

| 命令 | 用途 | 输入方式 |
|---|---|---|
| `trans` | 翻译成中文，支持本机缓存与 `--refresh` | 管道传入原文 |
| `find "问题"` | 依据帮助文本回答命令用法问题 | 管道传入帮助，参数提供问题 |
| `sum` | 总结文本 | 管道传入文本 |
| `ask "问题"` | 根据文本回答问题，当前侧重日志分析 | 管道传入日志等文本，参数提供问题 |

项目仍处于原型阶段。业务代码的 Python 语法、命令分发和缓存行为曾做过本地或模拟检查，尚无针对业务代码的正式自动化测试配置，项目记录也没有确认真实 API 成功返回。`Learn/` 已有独立的离线教学实验与自动化测试，不能将其结果当作业务程序的端到端验证。运行模型请求可能产生费用。

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

如果源码已在本机，直接进入包含 `pyproject.toml` 的项目根目录。下面两种安装方式按使用场景选择即可。

### 日常使用：通过 pipx 安装

pipx 会为工具创建独立的 Python 环境，并提供可在其他目录运行的 `mytool` 命令，不需要每次激活项目虚拟环境。

**1. 准备 pipx 与 PATH。** 先检查是否已安装：

```sh
pipx --version
```

如果显示版本号，直接运行下面的 `pipx ensurepath`。如果提示找不到命令，Ubuntu 23.04 及更新版本可先安装：

```sh
sudo apt update
sudo apt install pipx
```

其他系统的安装方法见 [pipx 官方安装说明](https://pipx.pypa.io/stable/how-to/install-pipx.html)。安装后执行：

```sh
pipx ensurepath
```

它会把 pipx 的命令目录加入 PATH（终端查找命令的目录列表）。按提示重新打开终端，使 PATH 设置生效。

**2. 安装并验证 mytool。** 在项目根目录执行，确保 `python3` 是 Python 3.10 或更新版本：

```sh
python3 --version
pipx install --python python3 .
pipx list
command -v mytool
mytool --help
```

这里的 `.` 表示安装当前目录的项目。安装成功后，`pipx list` 应列出 `mytool`，`command -v mytool` 应显示命令位置，`mytool --help` 应显示 `trans`、`find`、`sum` 和 `ask` 四个子命令。可以切换到其他目录再执行 `mytool --help`，确认不依赖项目目录；查看帮助不会调用模型 API。如果找不到 `mytool`，先确认已运行 `pipx ensurepath` 并重新打开终端。

**3. 修改源码后更新安装。** 普通 pipx 安装使用安装时的代码副本。保留原源码目录，修改后执行：

```sh
pipx reinstall mytool
mytool --help
```

`reinstall` 会按原来的来源和安装选项重新安装；它依赖最初安装的源码路径仍然存在。如果源码已移到其他位置，可在新的项目根目录执行 `pipx install --force --python python3 .`，更新安装来源。命令含义见 [pipx 命令参考](https://pipx.pypa.io/stable/reference/cli.html)。

### 开发使用：项目虚拟环境

如果希望修改源码后立即验证，可使用可编辑安装：

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/mytool --help
```

`-e` 表示可编辑安装。验证本地修改时使用 `.venv/bin/mytool`，确保运行的是项目开发环境中的版本。

上述安装和重新安装命令可能下载依赖。本次文档更新核对了 pipx 官方说明及本机命令帮助，没有执行安装、重新安装或真实 API 请求。

### 配置模型服务

在 `~/.config/mytool/.env` 中填写配置：

```dotenv
DEEPSEEK_API_KEY=你的_API_Key
BASE_URL=https://api.deepseek.com
```

请勿将真实密钥提交到仓库。程序也会读取同名环境变量，已有环境变量优先于配置文件；配置缺失时会显示错误。当前代码中的模型名为 `deepseek-flash`，尚不能通过配置文件修改；实际调用还取决于所用服务是否支持该模型及请求参数。

## 快速使用

安装后，先查看命令帮助；这一步不会调用模型 API：

```sh
mytool --help
python -m mytool --help  # 在已安装项目的 Python 环境中运行
```

四个子命令都需要非空、非纯空白的标准输入。管道符 `|` 会把左侧命令的输出交给右侧的 `mytool`。以下示例中，`trans` 命中缓存时直接返回译文，其余情况会发起 API 请求：

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

`trans` 按完整的标准输入文本进行精确匹配，包括空格和换行；只有原文完全相同才会使用缓存。缓存文件位于 `~/.local/share/mytool/trans.db`，保存原文、译文和更新时间。只有请求正常返回且译文不是 `None` 时才会写入；当前代码未排除空字符串。`--refresh` 会跳过查询，在得到可写入的结果后更新该原文的译文；请求失败或返回 `None` 时保留旧记录。

缓存只按原文匹配，不识别产生文本的命令，也不会因模型或提示词修改而自动失效。原文变化会产生新记录。当前只有 `trans` 使用缓存，`find`、`sum` 和 `ask` 每次都会请求模型。

## 手册阅读库：设计方向

阶段记录提出了进一步的需求：发现相关的 `man` 手册，按需阅读整篇中文译文，并逐步积累可搬运、可复用的个人译文库。这既要解决英文手册的阅读问题，也要帮助发现尚不知道名称的相关手册。

讨论中的入口是 `mytool man <名称>`，以整篇手册为翻译和缓存单位。该命令尚未实现：`mytool/commands/man.py` 目前为空，CLI 未注册 `man`。相关手册的发现和选择、首次阅读流程、版本识别与缓存导入导出仍需确定。具体背景见 [阶段一记录](doc/阶段一.md)。

## 学习材料与项目文档

项目也用于学习 Python 命令行开发、模型调用和本地数据存储。以下材料可从仓库内直接阅读：

- [Learn 学习入口](Learn/README.md)：九章源码阅读与离线实验，涵盖缓存、提示词模板、CLI、测试、重试、服务调度、模型选择、回答评估和手册阅读；各章提供中文注释版摘录。
- [学习材料验证记录](Learn/VALIDATION.md)：记录教学示例的检查结果及验证范围。
- [阶段一记录](doc/阶段一.md)：项目演进、翻译缓存的取舍和手册阅读库的讨论。
- [依赖、外部文件与部署](doc/enviroment.md)：运行环境、用户配置、缓存位置与安装方式。
- [API SDK 使用方式](doc/Turital/API-SDK.md)：统一配置与模型请求层的改造建议，示例结构尚未接入业务代码。

学习实验仅使用 Python 标准库，不需要安装项目依赖、配置 API Key 或调用模型。可在仓库根目录执行：

```sh
# 运行一个缓存实验
python3 Learn/01-shellgpt-cache/demo.py

# 运行全部教学示例与测试，并核对预期输出
python3 Learn/check_examples.py

# 检查教学材料的摘录指纹、本地链接和 Python 语法
python3 Learn/check_materials.py
```

这些实验使用模拟响应、临时数据库和教学数据；其中的调度、重试、模型选择等设计并未因此成为 `mytool` 的已有功能。

## 目录结构

```text
mytool/
├── pyproject.toml         # 项目元数据、依赖和 mytool 命令入口
├── README.md              # 项目说明
├── doc/                   # 阶段记录、环境说明与 SDK 改造建议
├── Learn/                 # 九章学习材料、离线实验与独立测试
└── mytool/
    ├── cli.py             # 参数解析、标准输入检查和命令分发
    ├── config.py          # 读取配置并创建 API 客户端
    ├── cache.py           # SQLite 翻译缓存
    ├── __main__.py        # python -m mytool 的入口
    └── commands/
        ├── trans.py       # 中文翻译
        ├── find.py        # 命令帮助问答
        ├── summary.py     # 文本摘要，对应 sum 子命令
        ├── ask.py         # 日志分析问答
        └── man.py         # 空占位文件，尚未接入 CLI
```

## 贡献指南

欢迎报告问题或改进文档和代码。仓库公开托管后，可通过 Issue 描述复现步骤、预期结果和实际结果；提交代码时，请从独立分支创建 Pull Request，说明改动目的和本地验证结果。报告问题时请删除日志中的密钥等敏感信息。当前业务代码尚无正式自动化测试配置，也尚未记录公开仓库地址；修改学习材料时可运行上面的离线检查。

## 开源协议

当前仓库没有 `LICENSE` 文件，尚未声明开源许可证。选择并添加许可证之前，不应将本项目视为已按 MIT、GPL 等协议授权再分发。
