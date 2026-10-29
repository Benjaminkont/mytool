# mytool/commands/woman.py


import subprocess
from pathlib import Path


def find_manuals(manual_name: str, section: str | None) -> list[Path]:
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


def woman(
    manual_name: str,
    *,
    section: str | None = None,
    refresh: bool = False,
    original: bool = False,
) -> None:
    paths: list[Path] = find_manuals(manual_name, section)

    # TODO: Add feature that can allow user to choose when there are several matches
    path = paths[0]

    if original:
        subprocess.run(["man", str(path)], check=False)
        return

    raise NotImplementedError("Command [woman] is not implemented yet!")
