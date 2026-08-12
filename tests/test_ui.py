import unittest
from html.parser import HTMLParser

from fastapi.testclient import TestClient

from api.app import app


class _AssetParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.assets: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        attributes = dict(attrs)
        asset = attributes.get("src") if tag == "script" else attributes.get("href")
        if asset and asset.startswith("/assets/"):
            self.assets.append(asset)


class DetectionUiTests(unittest.TestCase):
    def test_root_serves_built_react_application(self) -> None:
        with TestClient(app) as client:
            ui_response = client.get("/")
            docs_response = client.get("/docs")
            parser = _AssetParser()
            parser.feed(ui_response.text)
            asset_responses = [client.get(path) for path in parser.assets]

        self.assertEqual(ui_response.status_code, 200)
        self.assertIn("<title>Water Leaking Detector</title>", ui_response.text)
        self.assertGreaterEqual(len(parser.assets), 2)
        self.assertEqual(
            ui_response.headers.get("cache-control"),
            "no-store, max-age=0",
        )
        self.assertEqual(docs_response.status_code, 200)
        for response in asset_responses:
            self.assertEqual(response.status_code, 200)
            self.assertIn(
                response.headers.get("content-type", "").split(";")[0],
                {"application/javascript", "text/css", "text/javascript"},
            )


if __name__ == "__main__":
    unittest.main()
