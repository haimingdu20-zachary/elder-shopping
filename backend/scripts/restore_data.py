from __future__ import annotations

import os
from pathlib import Path

from app.backup import BackupService


def main() -> None:
    if os.getenv("RESTORE_CONFIRM") != "YES":
        raise SystemExit("恢复会覆盖当前数据文件。请设置 RESTORE_CONFIRM=YES 后重试。")
    data_dir = Path(os.getenv("DATA_DIR", "data"))
    print(BackupService(data_dir).restore_latest())


if __name__ == "__main__":
    main()
