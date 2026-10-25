"""
不知道怎么敲命令（无米之炊或看 --help 找用法）	
无管道（直接问）：
    mytool how "怎么看 8080 端口被谁占了"
有管道（查帮助）：
    docker --help | mytool how "怎么用 compose"	- 通过 sys.stdin.isatty() 自动判断有无管道输入，question 参数必填。
- 无管道时：结合当前系统环境（macOS/Linux），直接给出可复制的命令与一句话解释。
- 有管道时：结合左侧命令 cmd 与帮助文本回答；若当前仅为顶层帮助且目标在子命令中，直接给出下一步命令（如 docker compose --help | mytool how "..."）。
"""


