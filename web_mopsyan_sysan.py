from __future__ import annotations

import time

from web_runtime import WebRuntime


def main() -> None:
    app = WebRuntime()
    app.start(open_browser_on_start=True)
    print(f"Web-панель: {app.dashboard_url}")
    print(f"Сцена OBS: {app.overlay_url}")
    print(f"Чат OBS: {app.chat_browser_url}")

    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        pass
    finally:
        app.shutdown()


if __name__ == "__main__":
    main()
