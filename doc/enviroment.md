# mytool 的依赖、外部文件与部署

本文依据当前的 `pyproject.toml`、`mytool/config.py`、`mytool/cache.py` 和 `README.md` 整理。项目是命令行工具，不需要单独运行一个常驻服务。安装依赖会访问软件包仓库；下文的安装命令是操作说明，本次文档编写没有执行安装或调用模型 API。

## 1. 项目依赖

### 运行环境

- **Python 3.10 或更新版本：** 这是 README 中的要求，当前源码也使用了 `str | None` 等较新的类型语法。`pyproject.toml` 尚未用 `requires-python` 声明或强制检查这个版本范围。
- **操作系统与终端：** 命令从标准输入读取文本，适合在支持管道的终端中运行。示例使用类 Unix 路径和 shell 命令；当前代码中的用户文件路径也是按 `Path.home()` 组合出来的。
- **兼容 OpenAI 接口的模型服务：** `trans`、`find`、`sum`、`ask` 发起请求时需要有效的 `DEEPSEEK_API_KEY` 和 `BASE_URL`，以及可用的网络连接。代码目前使用 `deepseek-flash` 模型名；服务端是否支持该模型需要以实际配置和请求结果为准。缓存命中的 `trans` 不会发起模型请求。

### `pyproject.toml` 声明的第三方 Python 包

- `openai`：创建 API 客户端并发送聊天请求。
- `python-dotenv`：从用户配置文件加载环境变量。
- `httpx2[socks]`：项目显式声明的网络依赖，包含 SOCKS 代理所需支持；曾用来解决 pipx 环境中缺少 `socksio` 的报错。

这些依赖目前**没有固定版本**，仓库也没有锁定完整依赖树的 lock 文件。安装时实际取得的间接依赖及版本由当时的包仓库和安装环境决定。

### Python 标准库与安装工具

- 源码使用 `argparse`、`sys`、`os`、`pathlib` 和 `sqlite3` 等标准库；SQLite 翻译缓存不需要额外安装 Python 数据库包。
- `pip` 用于安装项目及依赖；`venv` 可创建项目开发环境。`pipx` 是可选的**安装工具**，用于把 `mytool` 放进独立环境并暴露全局命令，不是 `pyproject.toml` 中的运行依赖。
- `docker`、`git`、`man` 等是使用示例或后续设计中提到的外部命令，**不是安装 `mytool` 所必需的依赖**。当前 CLI 尚未提供 `man` 子命令。

## 2. 项目目录之外的文件和状态

项目源码位于仓库的 `mytool/` 中，但运行时还会使用用户目录下的文件：

- `~/.config/mytool/.env`：由用户创建的配置文件，存放 `DEEPSEEK_API_KEY` 和 `BASE_URL`。`mytool/config.py` 在导入时读取它；同名的进程环境变量也可提供配置，已有环境变量不会被该文件覆盖。该文件包含凭据，不应放入仓库或提交到版本控制。
- `~/.local/share/mytool/trans.db`：`trans` 的 SQLite 缓存文件，由 `mytool/cache.py` 在需要查询或保存缓存时创建。表以完整输入原文为键，保存译文及更新时间。它与项目源码、pipx 安装目录分开，因此更新安装包不会以替换源码的方式删除这份数据。
- 采用 pipx 安装时，通常会出现 `~/.local/bin/mytool` 命令入口，以及 `~/.local/share/pipx/venvs/mytool/` 中的独立 Python 环境。实际位置可通过 `command -v mytool` 和 `pipx list` 核对，受 pipx 配置影响。

项目内的 `.venv/` 是开发环境，`build/`、`dist/`、`*.egg-info/` 和 `__pycache__/` 是可能产生的本地文件或目录；它们与上面列出的用户目录文件不同。项目 `.gitignore` 已包含这些常见生成物和项目目录里的 `.env`。

## 3. 部署与使用

下面两种安装方式择一即可。命令应在**项目根目录**执行，即包含 `pyproject.toml` 的目录。安装过程可能下载依赖；本节只是说明步骤，没有在编写本文时执行。

### 开发方式：项目虚拟环境

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -m mytool --help
```

`-e` 表示可编辑安装，适合修改源码后立即用这个虚拟环境验证。命令入口还可以写成 `.venv/bin/mytool --help`。不必先激活虚拟环境，但要使用 `.venv/bin/` 中的 Python 或命令。

### 日常方式：pipx 全局命令

先确保本机已安装 pipx，并已将其应用目录加入终端的 `PATH`。在项目根目录执行：

```sh
pipx install .
mytool --help
```

普通 `pipx install .` 把项目装进 pipx 管理的独立环境。修改源码或依赖后，应按实际安装方式重新安装，例如执行 `pipx reinstall mytool`，再用 `command -v mytool` 与 `mytool --help` 核对正在使用的命令。`--help` 不需要 API 配置，也不会发送模型请求。

### 配置 API 并运行

在用户目录创建 `~/.config/mytool/.env`，写入自己的配置，不要把真实密钥放进命令历史或仓库：

```dotenv
DEEPSEEK_API_KEY=你的_API_Key
BASE_URL=https://api.deepseek.com
```

保存后将该文件权限设为仅自己可读写，例如在类 Unix 系统中运行 `chmod 600 ~/.config/mytool/.env`。也可以通过同名环境变量提供配置，环境变量优先于 `.env` 中的同名值。

确认命令能启动后，可用管道处理文本：

```sh
docker --help | mytool trans
docker --help | mytool trans --refresh
```

第一次翻译未命中缓存时会调用模型，可能产生费用；相同原文再次输入会返回缓存。`--refresh` 跳过缓存查询并重新请求模型，成功后更新译文。真实 API 返回和上述安装流程尚未在本次文档编写中重新验证。
