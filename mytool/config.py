import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path.home() / ".config" / "mytool" / ".env")

api_key = os.getenv("DEEPSEEK_API_KEY")
base_url = os.getenv("BASE_URL")

def create_client() -> OpenAI:
    if not api_key:
        raise RuntimeError("缺少 DEEPSEEK_API_KEY，请检查 ~/.config/mytool/.env")
    if not base_url:
        raise RuntimeError("缺少 BASE_URL，请检查 ~/.config/mytool/.env")

    return OpenAI(api_key=api_key, base_url=base_url)