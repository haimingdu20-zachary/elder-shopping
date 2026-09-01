from __future__ import annotations

import os
from pathlib import Path

from app.backup import BackupService


def main() -> None:
    data_dir = Path(os.getenv("DATA_DIR", "data"))
    result = BackupService(data_dir).backup()
    print(result)


if __name__ == "__main__":
    main()
