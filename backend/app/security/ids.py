"""ID 与房间码生成（标准库）。

设计事实源：docs/01-architecture/r001-app-architecture.md §9.4
ID 一律 `前缀_随机`（TEXT 主键，日志与人工核对友好）；
房间码 6 位，字符集剔除了易混的 `0/O/1/I`。
"""
from __future__ import annotations

import secrets

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 6


def new_id(prefix: str) -> str:
    """如 `new_id("usr") -> usr_3f1c9a4b2d5e6f70`。"""
    return f"{prefix}_{secrets.token_hex(8)}"


def new_code() -> str:
    """6 位房间码（剔除 0/O/1/I，方便口头传播）。"""
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
