from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINKS_FILE = ROOT / "data" / "links.json"
USER_AGENT = "ancveirs-profile-link-health/1.0 (+https://github.com/ancveirs-lv/ancveirs-lv)"


def main() -> int:
    payload = json.loads(LINKS_FILE.read_text(encoding="utf-8"))
    failures = 0

    for item in payload["links"]:
        req = urllib.request.Request(
            item["url"],
            headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*;q=0.8"},
            method="GET",
        )

        try:
            with urllib.request.urlopen(req, timeout=20) as response:
                status = response.getcode()
                final_url = response.geturl()
                print(f"OK   {status:<3} {item['id']}: {final_url}")
                if not 200 <= status < 400:
                    failures += 1
        except urllib.error.HTTPError as exc:
            if exc.code in (403, 429, 999):
                print(f"WARN {exc.code:<3} {item['id']}: rate-limited or bot-blocked")
            else:
                print(f"FAIL {exc.code:<3} {item['id']}: {item['url']}")
                failures += 1
        except Exception as exc:
            print(f"FAIL --- {item['id']}: {type(exc).__name__}: {exc}")
            failures += 1

    if failures:
        print(f"Link health failed: {failures} link(s)")
        return 1

    print("Link health passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
