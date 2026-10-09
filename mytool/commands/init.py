import os
from pathlib import Path
from mytool.cache import init_db


def init():
    HOME = Path.home()
    config_dir = HOME / ".config" / "mytool"
    config_dir.mkdir(parents=True, exist_ok=True)

    env_path = config_dir / ".env"

    try:
        with env_path.open("x", encoding="utf-8") as f:
            env_path.chmod(0o600)
            f.write(
                "DEEPSEEK_API_KEY=\n"
                "BASE_URL=https://api.deepseek.com\n"
            )
    except FileExistsError:
        print(f"配置文件已存在:{env_path}")
    else:
        print(f"配置文件已创建。请填写 API_key:{env_path}")

    init_db()
    print("翻译数据库已准备好")
