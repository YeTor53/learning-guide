"""口令哈希（Python 标准库 scrypt，零第三方依赖）。

设计事实源：docs/01-architecture/r001-app-architecture.md §9.4
存储格式：`scrypt$N$r$p$salt_b64$hash_b64`（base64url、无填充），与 `002_seed.sql` 的演示数据同口径。
安全取舍：不加外部 pepper（部署复杂度），靠 scrypt 参数与随机 salt；校验用 `hmac.compare_digest` 防时序侧信道。
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

SCRYPT_N = 16384
SCRYPT_R = 8
SCRYPT_P = 1
DK_LEN = 32
SALT_LEN = 16

# 邮箱不存在时也走一次同参数校验，避免用响应时间探测"邮箱是否已注册"
_DUMMY_HASH = None


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64decode(text: str) -> bytes:
    padding = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + padding)


def _scrypt(plain: str, salt: bytes) -> bytes:
    return hashlib.scrypt(plain.encode("utf-8"), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=DK_LEN)


def hash_password(plain: str) -> str:
    """生成 `scrypt$N$r$p$salt$hash`；每次调用都用新的随机 salt。"""
    salt = secrets.token_bytes(SALT_LEN)
    digest = _scrypt(plain, salt)
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${_b64encode(salt)}${_b64encode(digest)}"


def verify_password(plain: str, stored: str) -> bool:
    """校验口令；格式非法或参数不符一律返回 False（不抛异常，避免泄露内部细节）。"""
    parts = stored.split("$") if isinstance(stored, str) else []
    if len(parts) != 6 or parts[0] != "scrypt":
        return False
    try:
        n, r, p = int(parts[1]), int(parts[2]), int(parts[3])
        salt = _b64decode(parts[4])
        expected = _b64decode(parts[5])
    except (ValueError, TypeError):
        return False
    if (n, r, p) != (SCRYPT_N, SCRYPT_R, SCRYPT_P):
        return False
    actual = hashlib.scrypt(plain.encode("utf-8"), salt=salt, n=n, r=r, p=p, dklen=len(expected))
    return hmac.compare_digest(actual, expected)


def dummy_verify(plain: str) -> None:
    """邮箱不存在时调用：花费与真实校验同量级的时间，避免账号枚举。"""
    global _DUMMY_HASH
    if _DUMMY_HASH is None:
        _DUMMY_HASH = hash_password("dummy-password-for-timing")
    verify_password(plain, _DUMMY_HASH)
