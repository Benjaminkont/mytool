import gzip
import hashlib
import subprocess
from pathlib import Path

from openai.types.chat import ChatCompletionMessageParam

from mytool.config import create_client

# 缓存路径
CACHE_DIR = Path.home() / ".local" / "share" / "mytool" / "woman"

# 提示词是 Claude 给我的
woman_system_prompt: str = """你会收到一份 man 手册的 roff 源码。请把其中给人阅读的英文翻译成中文，然后输出完整的源码。

roff 源码有两种行：
1. 以 . 开头的是宏行（排版命令）。宏名和参数里的命令名、选项保持不变，只翻译 .Nd .Sh .Ss .SH .SS 后面的说明文字。
2. 不以 . 开头的是普通文字行。把它翻译成中文，行首绝对不要加 . 。

其他规则：
- 输出的行数和原文一致，一行对应一行，不要合并或拆分行
- 命令名、选项（如 -a、--all）、文件路径保持不变
- \\fB、\\fR、\\fI、\\- 等转义序列保持不变
- 只输出源码本身，不要用代码块包裹，不要加任何解释

示例输入：
.Sh DESCRIPTION
The
.Nm
utility waits for a number of seconds.
.Sh SEE ALSO

示例输出：
.Sh 描述
该
.Nm
工具会等待若干秒。
.Sh 另请参阅
"""


class WomanClient:
    def __init__(self) -> None:
        self.client = create_client()

        self.messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": woman_system_prompt},
        ]

    def chat(self, help: str) -> str:
        self.messages.append({"role": "user", "content": help})
        response = self.client.chat.completions.create(
            # model="local-qwen",
            model="deepseek-flash",
            messages=self.messages,
            stream=False,
        )

        answer = response.choices[0].message.content
        if answer is None:
            raise RuntimeError("Model error")
        return str(answer)


def find_manuals(manual_name: str, section: str | None) -> list[Path]:
    """找出对应命令所有的手册
    Args:
        manual_name: str        => 命令名称
        section: str | None     => 可选 选择哪个命令手册

    Returns:
        list[Path]              => 所有手册的路径
    """
    cmd: list[str] = ["man", "-aw"]

    if section:
        cmd.append(section)

    cmd.append(manual_name)
    try:
        output = subprocess.run(
            cmd,
            text=True,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError as error:
        raise RuntimeError("系统中未找到 man 命令") from error

    if output.returncode:
        raise RuntimeError(output.stderr.strip() or f"找不到手册: {manual_name}")

    paths = [Path(line) for line in output.stdout.splitlines() if line.strip()]
    if not paths:
        raise RuntimeError(f"找不到手册: {manual_name}")
    return paths


def choose_manual(manual_name: str, paths: list[Path]) -> Path:
    """提供能够供用户选择手册的入口
    Args:
        manual_name: str    => 命令名称
        paths: list[Path]   => 路径

    Returns:
        Path                => 对应手册路径
    """

    print(f"命令 '{manual_name}' 有 {len(paths)} 条手册\n")
    print("分别为: ")

    # 显示格式例如 [1] printf(1)  /usr/share/man/man1/printf.1
    for index, path in enumerate(paths, 1):
        file_name = path.name.removesuffix(".gz")
        name, _, sec = file_name.rpartition(".")
        print(f"    [{index}] {name}({sec})  {path}")

    print()

    choice = 0
    while True:
        try:
            choice = int(input("请输入 [] 中的序号来选择对应的手册\n"))
        except ValueError:
            print("请输入对应的数字")
        except (EOFError, KeyboardInterrupt):
            raise RuntimeError("Exit from keyboard")

        if 1 <= choice <= len(paths):
            return paths[choice - 1]


def read_source(path: Path) -> str:
    """读取 man 命令对应手册中的内容
    Args:
        path: Path  => 手册文件路径

    Returns:
        str         => man 手册文件中的内容
    """
    # man 有两种格式 一种直接是文本 还有一种是 gz 压缩包
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8", errors="replace") as f:
            source = f.read()
    else:
        source = path.read_text(encoding="utf-8", errors="replace")

    lines = [line for line in source.splitlines() if not line.startswith('.\\"')]
    return "\n".join(lines) + "\n"


def check_roff(page: Path) -> None:
    """检查译文格式有无问题
    Args:
        page: Path      => 译文路径

    Raise:
        RuntimeError    => 译文格式出错
    """
    try:
        result = subprocess.run(
            ["mandoc", "-T", "lint", "-W", "error", str(page)],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as error:
        raise RuntimeError(
            "系统中未找到 mandoc，无法验证翻译后的手册格式"
        ) from error

    if result.returncode != 0:
        raise RuntimeError(
            f"Roff Format Error: \n    {result.stdout}\n    {result.stderr}"
        )


def cache_path(source: str, file_name: str) -> Path:
    """构建缓存路径
    Args:
        source: str         => man 原文
        file_name: str      => man 文件名

    Returns:
        Path                => 译文缓存路径
    """
    # 取前 16 位哈希值就够了
    key = hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]
    return CACHE_DIR / key / file_name


def build_translation(source: str, cached: Path) -> None:
    """构建翻译
    Args:
        source: str     => 译文原文
        cached: Path    => 缓存路径
    """
    translated = WomanClient().chat(source)

    cached.parent.mkdir(parents=True, exist_ok=True)
    tmp = cached.with_name(cached.name + ".tmp")
    tmp.write_text(translated, encoding="utf-8")

    try:
        check_roff(tmp)
    except RuntimeError:
        failed = cached.with_name(cached.name + ".failed")
        tmp.replace(failed)
        print(f"译文未通过检查 保存在: {failed}")
        raise

    tmp.replace(cached)


def woman(
    manual_name: str,
    *,
    section: str | None = None,
    refresh: bool = False,
    original: bool = False,
) -> None:
    """woman 命令本体
    Args:
        manual_name: str        => 命令名称
        section: str | None     => 默认值 None 为命令手册第几篇
        refresh: bool           => 默认值 False 是否重新生成翻译
        original: bool          => 默认值 False 显示原本 man 内容
    """
    paths: list[Path] = find_manuals(manual_name, section)

    if len(paths) > 1:  # 如果命令有多个手册就给用户选择权
        path = choose_manual(manual_name, paths)
    else:
        path = paths[0]

    if original:
        # 显示原本 man 命令
        subprocess.run(["man", str(path)], check=False)
        return

    file_name = path.name.removesuffix(".gz")
    source = read_source(path)
    cached = cache_path(source, file_name)

    if refresh or not cached.exists():
        if refresh:
            print("已选择强制重新翻译 正在重新翻译")
        else:
            print("未检测到缓存 正在翻译")

        build_translation(source, cached)
    else:
        print(f"缓存命中: {cached}")

    subprocess.run(["man", str(cached)], check=False)
