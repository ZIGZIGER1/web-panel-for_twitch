from __future__ import annotations

import subprocess
import sys
from pathlib import Path


CREATE_NEW_PROCESS_GROUP = 0x00000200
DETACHED_PROCESS = 0x00000008


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    target = base_dir / "mopsyan_sysan.py"
    pythonw = Path(sys.executable.replace("python.exe", "pythonw.exe"))
    executable = pythonw if pythonw.exists() else Path(sys.executable)

    subprocess.Popen(
        [str(executable), str(target)],
        cwd=str(base_dir),
        creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
        close_fds=True,
    )


if __name__ == "__main__":
    main()
