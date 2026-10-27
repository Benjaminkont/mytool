import os
import shlex
from pathlib import Path

from mytool.cache import clear_cache, init_db

HOOK_SCRIPT = """autoload -Uz add-zsh-hook

_mytool_preexec() {
    export MYTOOL_PIPELINE="$3"
    return 0
}

add-zsh-hook preexec _mytool_preexec
"""


def _init_zsh_hook(config_dir: Path) -> None:
    """保存钩子脚本，并让新 Zsh 会话自动加载；保留已有脚本。"""
    hook_path = config_dir / "hook.zsh"
    try:
        with hook_path.open("x", encoding="utf-8") as file:
            file.write(HOOK_SCRIPT)
    except FileExistsError:
        print(f"Zsh 钩子文件已存在：{hook_path}")
    else:
        print(f"Zsh 钩子文件已创建：{hook_path}")

    zsh_dir = Path(os.environ["ZDOTDIR"]) if "ZDOTDIR" in os.environ else Path.home()
    zshrc_path = zsh_dir / ".zshrc"
    zshrc_path.parent.mkdir(parents=True, exist_ok=True)
    existing = zshrc_path.read_text(encoding="utf-8") if zshrc_path.exists() else ""
    source_line = f"source {shlex.quote(str(hook_path))}"

    if source_line not in (line.strip() for line in existing.splitlines()):
        separator = "\n" if existing and not existing.endswith("\n") else ""
        with zshrc_path.open("a", encoding="utf-8") as file:
            file.write(f"{separator}\n# mytool: 加载命令捕获钩子\n{source_line}\n")
        print(f"Zsh 加载语句已添加：{zshrc_path}")
    else:
        print(f"Zsh 加载语句已存在：{zshrc_path}")

    print("新 Zsh 终端会自动注册钩子。当前终端请单独执行：")
    print(f"source {shlex.quote(str(zshrc_path))}")


def init():
    HOME = Path.home()
    config_dir = HOME / ".config" / "mytool"
    config_dir.mkdir(parents=True, exist_ok=True)

    env_path = config_dir / ".env"

    try:
        with env_path.open("x", encoding="utf-8") as f:
            env_path.chmod(0o600)
            f.write("DEEPSEEK_API_KEY=\nBASE_URL=https://api.deepseek.com\n")
    except FileExistsError:
        print(f"配置文件已存在:{env_path}")
    else:
        print(f"配置文件已创建。请填写 API_key:{env_path}")

    # 初始化数据库
    init_db()
    print("翻译数据库已准备好")
    _init_zsh_hook(config_dir)


def reinit():
    """清空翻译缓存，保留已有配置；缺少配置时创建模板。"""
    init()
    clear_cache()
    print("翻译缓存已清空")
