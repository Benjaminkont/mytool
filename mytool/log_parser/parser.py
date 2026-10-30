"""对日志做可解释的本地统计和证据筛选。"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass


_ERROR_RE = re.compile(
    r"\b(?:error|err|fatal|critical|exception|traceback|panic)\b"
    r"|失败|异常|超时|timed\s*out|connection\s+refused|permission\s+denied",
    re.IGNORECASE,
)
_WARNING_RE = re.compile(
    r"\b(?:warn|warning)\b|警告|注意",
    re.IGNORECASE,
)
_UUID_RE = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class LogAnalysis:
    """本地分析结果；不修改原始日志。"""

    raw_text: str
    compact_text: str
    total_lines: int
    error_lines: int
    warning_lines: int
    repeated_lines: int
    omitted_lines: int
    was_compacted: bool

    @property
    def statistics(self) -> str:
        return (
            f"总行数：{self.total_lines}\n"
            f"错误或异常相关行：{self.error_lines}\n"
            f"警告相关行：{self.warning_lines}\n"
            f"折叠的重复行：{self.repeated_lines}\n"
            f"筛选时省略的行：{self.omitted_lines}\n"
            f"是否经过压缩：{'是' if self.was_compacted else '否'}"
        )


def _normalize(line: str) -> str:
    """将易变化的标识归一化，用于发现重复日志模板。"""
    normalized = _UUID_RE.sub("<uuid>", line.strip().lower())
    normalized = re.sub(r"\b\d+\b", "<number>", normalized)
    return re.sub(r"\s+", " ", normalized)


def _key_indices(lines: list[str]) -> tuple[set[int], set[int]]:
    errors = {index for index, line in enumerate(lines) if _ERROR_RE.search(line)}
    warnings = {
        index
        for index, line in enumerate(lines)
        if index not in errors and _WARNING_RE.search(line)
    }
    return errors, warnings


def _numbered(index: int, line: str) -> str:
    return f"[line {index + 1}] {line}"


def _compact_lines(
    lines: list[str],
    errors: set[int],
    warnings: set[int],
    counts: Counter[str],
    max_chars: int,
) -> tuple[str, int]:
    key = errors | warnings
    keep: set[int] = set()

    # 错误和警告附近的少量上下文通常比单独一行更有用。
    for index in key:
        keep.update(range(max(0, index - 2), min(len(lines), index + 3)))

    # 保留开头和结尾，帮助判断启动阶段和最终状态。
    keep.update(range(min(40, len(lines))))
    keep.update(range(max(0, len(lines) - 40), len(lines)))

    # 对重复模板保留第一次出现；统计信息会告诉模型其余内容被折叠。
    first_seen: set[str] = set()
    for index, line in enumerate(lines):
        normalized = _normalize(line)
        if counts[normalized] <= 1 or normalized not in first_seen:
            keep.add(index)
        first_seen.add(normalized)

    selected: list[int] = []
    emitted_templates: set[str] = set()
    for index in sorted(keep):
        normalized = _normalize(lines[index])
        if counts[normalized] > 1:
            if normalized in emitted_templates:
                continue
            emitted_templates.add(normalized)
        selected.append(index)
    parts: list[str] = []
    previous = -1
    for index in selected:
        if index > previous + 1:
            parts.append(f"... [省略 {index - previous - 1} 行] ...")
        parts.append(_numbered(index, lines[index]))
        previous = index

    compact = "\n".join(parts)
    omitted = max(0, len(lines) - len(selected))

    if len(compact) <= max_chars:
        return compact, omitted

    # 保留压缩结果的两端；行号和截断说明让模型知道证据不完整。
    head_size = max_chars // 2
    tail_size = max_chars - head_size
    compact = (
        compact[:head_size]
        + "\n... [压缩证据中间部分因长度限制被截断] ...\n"
        + compact[-tail_size:]
    )
    return compact, omitted


def analyze_log(text: str, *, max_chars: int = 12000) -> LogAnalysis:
    """分析日志并生成带行号的原文和可解释的压缩证据。"""
    lines = text.splitlines()
    if not lines:
        return LogAnalysis(text, "", 0, 0, 0, 0, 0, False)

    errors, warnings = _key_indices(lines)
    counts = Counter(_normalize(line) for line in lines if _normalize(line))
    repeated = sum(max(0, count - 1) for count in counts.values())
    raw = "\n".join(_numbered(index, line) for index, line in enumerate(lines))

    needs_compact = len(raw) > max_chars or repeated > 0 or len(lines) > 120
    if not needs_compact:
        return LogAnalysis(
            raw,
            raw,
            len(lines),
            len(errors),
            len(warnings),
            0,
            0,
            False,
        )

    compact, omitted = _compact_lines(lines, errors, warnings, counts, max_chars)
    return LogAnalysis(
        raw,
        compact,
        len(lines),
        len(errors),
        len(warnings),
        repeated,
        omitted,
        True,
    )
