import subprocess
import unittest
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread


class ApplicationFileHandler(SimpleHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/":
            self.path = "/frontend/dist/index.html"
        elif self.path.startswith("/assets/"):
            self.path = f"/frontend/dist{self.path}"
        super().do_GET()


class BrowserUiBehaviorTests(unittest.TestCase):
    def assert_browser_harness_passes(self, harness: str) -> None:
        chrome = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
        if not chrome.exists():
            self.skipTest("Google Chrome is required for browser interaction tests.")

        project_root = Path(__file__).resolve().parent.parent
        handler = partial(ApplicationFileHandler, directory=project_root)
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with TemporaryDirectory(dir=Path(__file__).parent) as profile:
                completed = subprocess.run(
                    [
                        str(chrome),
                        "--headless",
                        "--disable-gpu",
                        "--no-sandbox",
                        f"--user-data-dir={profile}",
                        "--virtual-time-budget=3000",
                        "--dump-dom",
                        (
                            f"http://127.0.0.1:{server.server_port}/"
                            f"tests/{harness}"
                        ),
                    ],
                    capture_output=True,
                    check=False,
                    encoding="utf-8",
                    errors="replace",
                    timeout=30,
                )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn('data-result="PASS"', completed.stdout, completed.stdout)

    def test_review_controls_and_mouse_editing_in_browser(self) -> None:
        self.assert_browser_harness_passes("browser_ui_harness.html")

if __name__ == "__main__":
    unittest.main()
