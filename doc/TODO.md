# mytool 第一版重构规划与 TODO 清单

## 1. 核心定位与设计理念

针对**“英语不太好、终端基础薄弱、因来回复制粘贴上下文去问 AI 太累而容易中途放弃”**的使用痛点，`mytool` 的核心目标是：
- **零手动交代上下文**：利用管道（`stdin`）、Zsh Hook（`MYTOOL_PIPELINE` 捕获管道左侧命令）以及 Python `platform`（当前操作系统与 Shell 环境），在终端原地自动打包完整上下文喂给模型。
- **直接给下一步可执行的结论**：避免长篇大论，直接给出可复制的命令、子命令进步引导（如从 `docker --help` 引导至 `docker compose --help`）、异常原因定位或风险提示。

## 2. 子命令重规划清单（5 组核心命令）

| 子命令 | 核心场景 | 使用方式 | 关键行为与设计要求 |
|---|---|---|---|
| `init` / `reinit` | 环境初始化与重置 | `mytool init`<br>`mytool reinit` | - `init`：安全创建 `~/.config/mytool/.env`（权限 `600`）、初始化 SQLite 缓存库、检查或引导配置 `.zshrc` 中的 `MYTOOL_PIPELINE` 钩子。<br>- `reinit`：重置/清空本地翻译缓存表或重建配置模板。 |
| `trans` | 看不懂英文输出，需通读中文全文 | `命令 \| mytool trans`<br>`命令 \| mytool trans --refresh` | - 必须有管道输入。<br>- 提示词约束：忠实翻译为中文，**保留命令名、子命令名、参数选项（如 `-v`、`--help`）原样不乱译**，保持原有缩进排版。<br>- 命中本地缓存时瞬间输出；未命中时流式打印并在完成后写入缓存。 |
| `how` | 不知道怎么敲命令（无米之炊或看 `--help` 找用法） | **无管道（直接问）**：<br>`mytool how "怎么看 8080 端口被谁占了"`<br>**有管道（查帮助）**：<br>`docker --help \| mytool how "怎么用 compose"` | - 通过 `sys.stdin.isatty()` 自动判断有无管道输入，`question` 参数必填。<br>- **无管道时**：结合当前系统环境（macOS/Linux），直接给出可复制的命令与一句话解释。<br>- **有管道时**：结合左侧命令 `cmd` 与帮助文本回答；若当前仅为顶层帮助且目标在子命令中，直接给出下一步命令（如 `docker compose --help \| mytool how "..."`）。 |
| `log` | 看不懂命令输出或日志（合并原 `sum` 与 `ask`） | **无问题（自动降噪总结）**：<br>`journalctl -n 100 \| mytool log`<br>**带问题（针对性排错）**：<br>`docker ps -a \| mytool log "为什么退出了"` | - 必须有管道输入，`question` 参数**可选**。<br>- **不传问题时**：自动过滤 90% 的正常流水账信息，单独拎出警告、错误和异常行，并用大白话解释报错含义与可能原因。<br>- **传入问题时**：结合左侧命令 `cmd` 与输出内容，针对性回答问题并给出排查建议。 |
| `explain` | 网上抄来一串长命令，看不懂也不敢回车 | `mytool explain "find . -mtime +7 -exec rm -rf {} \;"` | - 无需管道输入，命令字符串参数必填。<br>- 逐段拆解命令与各个参数的大白话含义。<br>- 醒目标注潜在风险（如删除文件、覆盖数据、修改系统权限等）。 |

## 3. 底层基础能力改造清单

- **流式输出（Streaming）**：默认启用 `stream=True` 边生成边打印，消除长文本处理时终端长时间空白假死带来的放弃感（`trans` 在流式接收完毕后完整写入缓存）。
- **标准错误（`stderr`）捕获引导**：终端报错默认走 `stderr`，普通管道 `|` 无法捕获。当 `trans` 或 `log` 检测到标准输入为空时，结合 `cmd` 智能提示用户使用 `|&`（如 `原命令 |& mytool log`）将报错一并传入管道。
- **超长输入自动截断**：当管道传入超大日志或长文本（超出设定行数或字符数阈值）时，自动保留开头与结尾最关键的部分并向用户输出截断提示，防止撑爆上下文或消耗过多费用。
- **统一模型调用层**：消除各子命令中重复定义的 `*Client` 类，在公共模块中统一封装客户端创建、系统环境信息注入、流式输出与异常处理。

## 4. 分步执行计划（TODO Checklist）

### 第一阶段：项目依赖与公共基础设施（`pyproject.toml` & `config.py`）
- [ ] **规范 `pyproject.toml`**：补充 `[build-system]`、`requires-python = ">=3.10"`、项目描述，将存疑的 `httpx2[socks]` 修正为标准的 `httpx[socks]`。
- [ ] **重构 `mytool/config.py`（或拆分为 `config.py` + `llm.py`）**：
  - [ ] 支持按需读取 `DEEPSEEK_API_KEY`、`BASE_URL` 与可选的 `DEEPSEEK_MODEL`（提供默认模型名）。
  - [ ] 封装获取当前操作系统与 Shell 环境信息的辅助函数。
  - [ ] 封装统一的模型调用函数（支持 `stream=True` 流式打印并返回完整文本，统一处理超长文本截断）。

### 第二阶段：升级本地缓存与初始化命令（`cache.py` & `init.py`）
- [ ] **重构 `mytool/cache.py`**：
  - [ ] 引入原文 SHA-256 哈希（`text_hash`）解决 `cmd=None`（未配钩子）时 SQLite `NULL` 主键重复插入且无法更新的问题。
  - [ ] 查询时校验原文是否变化：若同一 `command` 的输出内容已更新，自动视为未命中并更新译文与原文。
  - [ ] 新增清空/重置缓存表的函数供 `reinit` 调用。
- [ ] **完善 `mytool/commands/init.py`**：
  - [ ] `init`：创建 `~/.config/mytool/.env`、初始化数据库，并输出或配置 `.zshrc` 的 `MYTOOL_PIPELINE` 钩子说明。
  - [ ] `reinit`：实现真正的重置逻辑（如清理旧缓存表或重建数据库），不再与 `init` 完全重复。

### 第三阶段：实现核心子命令与 CLI 分发（`commands/` & `cli.py`）
- [ ] **升级 `mytool/commands/trans.py`**：改用统一流式请求函数，优化技术文本翻译提示词（保留参数与命令名原样、保持格式）。
- [ ] **新建 `mytool/commands/how.py`（替代原 `find.py`）**：实现“无管道直接推荐命令”与“有管道基于 `--help` 查找用法/引导子命令”双模式。
- [ ] **新建 `mytool/commands/log.py`（替代并合并原 `summary.py` 与 `ask.py`）**：实现 `question` 可选的日志降噪总结与针对性答疑。
- [ ] **新建 `mytool/commands/explain.py`**：实现长命令逐参数大白话拆解与危险操作排雷。
- [ ] **重构 `mytool/cli.py`**：
  - [ ] 注册 `init`、`reinit`、`trans`、`how`、`log`、`explain` 子命令。
  - [ ] 修复 `reinit` 未在读取 `stdin` 前返回的问题。
  - [ ] 使用 `sys.stdin.isatty()` 区分有无管道输入，并在需要管道却收到空输入时给出 `|&` 捕获 `stderr` 的友好提示。

### 第四阶段：本地验证与文档同步
- [ ] **本地检查与模拟测试**：完成语法检查、`--help` 分发验证、无管道/有管道分支验证以及 SQLite 缓存读写测试。
- [ ] **更新文档**：同步更新 `README.md`、`AGENTS.md` 与 `doc/enviroment.md` 中的命令列表和配置说明。
