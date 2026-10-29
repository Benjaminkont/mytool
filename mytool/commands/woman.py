# mytool/commands/woman.py


import subprocess
from pathlib import Path


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
    output = subprocess.run(
        cmd,
        text=True,
        capture_output=True,
        check=False,
    )

    if output.returncode:
        raise RuntimeError(output.stderr.strip() or f"找不到手册: {manual_name}")
    return [Path(str(line)) for line in output.stdout.splitlines()]


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

    raise NotImplementedError("Command [woman] is not implemented yet!")
