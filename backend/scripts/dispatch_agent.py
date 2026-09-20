"""给**已存在**的房间补派转写 worker（演示兜底；新建房已自动派单）。

用法（仓库根目录，后端环境）：
    python backend/scripts/dispatch_agent.py room_xxxxxxxx
设计事实源：`docs/rounds/r010-transcription/design.md` §9.3.4。
"""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import load_settings  # noqa: E402
from app.services import livekit as livekit_service  # noqa: E402


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("用法：python backend/scripts/dispatch_agent.py <room_id>")
        return 2
    settings = load_settings()
    room_id = argv[1]
    result = livekit_service.ensure_transcriber(room_id, settings)
    print(f"[dispatch] room={room_id} agent={settings.stt_agent_name} mode={settings.stt_mode} → {result or '失败（见日志）'}")
    return 0 if result else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
