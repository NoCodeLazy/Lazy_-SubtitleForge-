import sys
import threading
import webbrowser

import uvicorn

from .app import app
from .config_manager import config_manager


def main():
    server = config_manager.get("server")
    host = server.get("host", "127.0.0.1")
    port = int(server.get("port", 8080))
    auto_open = server.get("auto_open_browser", True)

    if auto_open:
        threading.Timer(2.0, lambda: webbrowser.open(f"http://{host}:{port}")).start()

    print(f"🚀 Subtitle Agent 已启动: http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
