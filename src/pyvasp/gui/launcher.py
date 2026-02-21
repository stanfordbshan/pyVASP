"""Desktop-style launcher for pyVASP GUI.

This launcher starts the local GUI host and opens either:
- a native desktop window (when `pywebview` is available), or
- the default browser as a fallback.
"""

from __future__ import annotations

import argparse
import socket
import threading
import time
import webbrowser
from typing import Any

import uvicorn

from pyvasp.gui.host import create_gui_app


def build_parser() -> argparse.ArgumentParser:
    """Create launcher argument parser."""

    parser = argparse.ArgumentParser(prog="pyvasp", description="Launch pyVASP GUI as an app window")
    parser.add_argument("--mode", choices=["direct", "api", "auto"], default="direct", help="Backend execution mode")
    parser.add_argument(
        "--api-base-url",
        default="http://127.0.0.1:8000",
        help="Remote API base URL for api/auto mode",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Local host for GUI service")
    parser.add_argument("--port", type=int, default=8080, help="Preferred local port")
    parser.add_argument(
        "--window",
        choices=["auto", "webview", "browser"],
        default="auto",
        help="Window target: native webview if available, or browser fallback",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Launch pyVASP GUI host and open a local window."""

    args = build_parser().parse_args(argv)
    port = _find_available_port(args.host, args.port)
    url = f"http://{args.host}:{port}"

    app = create_gui_app(mode=args.mode, api_base_url=args.api_base_url)
    server, thread = _start_server(app=app, host=args.host, port=port)
    try:
        _wait_until_ready(host=args.host, port=port, timeout_s=15.0)

        if args.window in {"auto", "webview"} and _run_webview(url=url):
            return 0

        _run_browser(url=url)
        return 0
    finally:
        _stop_server(server, thread)


def _start_server(*, app: Any, host: str, port: int) -> tuple[uvicorn.Server, threading.Thread]:
    config = uvicorn.Config(app=app, host=host, port=port, log_level="info", reload=False)
    server = uvicorn.Server(config)
    server.install_signal_handlers = lambda: None  # type: ignore[assignment]
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    return server, thread


def _stop_server(server: uvicorn.Server, thread: threading.Thread) -> None:
    server.should_exit = True
    thread.join(timeout=5.0)


def _wait_until_ready(*, host: str, port: int, timeout_s: float) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            if sock.connect_ex((host, port)) == 0:
                return
        time.sleep(0.1)
    raise RuntimeError(f"pyVASP GUI failed to start on {host}:{port}")


def _find_available_port(host: str, preferred: int) -> int:
    for port in range(preferred, preferred + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if sock.connect_ex((host, port)) != 0:
                return port
    raise RuntimeError(f"No free port available near {host}:{preferred}")


def _run_webview(*, url: str) -> bool:
    try:
        import webview  # type: ignore[import-not-found]
    except Exception:
        return False

    webview.create_window("pyVASP", url, width=1280, height=900, resizable=True)
    webview.start()
    return True


def _run_browser(*, url: str) -> None:
    webbrowser.open(url, new=1)
    print(f"pyVASP GUI running at {url} (Ctrl+C to stop)")
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        return


if __name__ == "__main__":
    raise SystemExit(main())
