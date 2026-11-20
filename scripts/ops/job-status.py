#!/usr/bin/env python3
"""把 ~/Library/Logs/home-service-hub/status/*.json 濃縮成早報的一行。

失敗或太久沒跑（超過 max 小時）才列出；還沒有紀錄的 job 先略過（剛上線時）。
早報用 macOS 內建 /usr/bin/python3（3.9）執行，所以不能用 3.11 的 datetime.UTC。
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

STATUS_DIR = Path.home() / "Library/Logs/home-service-hub/status"
# job -> (中文名, 最久幾小時沒跑算異常)；平日 job 給 100h 以涵蓋連假
JOBS = {
    "backup": ("資料庫備份", 30),
    "restore-drill": ("還原演練", 8 * 24),
    "portfolio.tw_daily_prices": ("股價抓取", 100),
    "portfolio.portfolio_snapshot": ("資產快照", 30),
    "portfolio.dividend_auto_record": ("股利入帳", 100),
    "portfolio.dca": ("定期定額", 100),
    "portfolio.symbol_map_refresh": ("股票代號表", 8 * 24),
    "portfolio.accounting_retry": ("記帳同步補送", 30),
}


def summarize(status_dir: Path = STATUS_DIR, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)  # noqa: UP017 (py3.9)
    problems, checked = [], 0
    for job, (label, max_hours) in JOBS.items():
        path = status_dir / f"{job}.json"
        if not path.exists():
            continue
        checked += 1
        data = json.loads(path.read_text())
        age_h = (now - datetime.fromisoformat(data["at"])).total_seconds() / 3600
        if not data["ok"]:
            problems.append(f"{label}失敗")
        elif age_h > max_hours:
            problems.append(f"{label} {int(age_h // 24)} 天沒跑")
    if problems:
        return "⚠️ 排程異常：" + "、".join(problems)
    return f"排程：全部正常（{checked} 項）"


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            now = datetime(2026, 11, 20, 8, tzinfo=timezone.utc)  # noqa: UP017 (py3.9)
            (p / "backup.json").write_text(json.dumps({"ok": True, "at": "2026-11-19T19:17:00+00:00"}))
            assert summarize(p, now) == "排程：全部正常（1 項）"
            (p / "portfolio.dca.json").write_text(json.dumps({"ok": False, "at": "2026-11-19T09:30:00+00:00"}))
            (p / "backup.json").write_text(json.dumps({"ok": True, "at": "2026-11-17T19:17:00+00:00"}))
            assert summarize(p, now) == "⚠️ 排程異常：資料庫備份 2 天沒跑、定期定額失敗", summarize(p, now)
        print("selftest ok")
    else:
        print(summarize())
