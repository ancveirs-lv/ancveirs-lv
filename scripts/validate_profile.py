from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
README_EN = ROOT / "README.md"
README_LV = ROOT / "README.lv.md"
LINKS_FILE = ROOT / "data" / "links.json"

REQUIRED_FILES = (
    README_EN,
    README_LV,
    LINKS_FILE,
    ROOT / "CHANGELOG.md",
    ROOT / ".github" / "CODEOWNERS",
    ROOT / ".github" / "workflows" / "ci.yml",
    ROOT / ".github" / "workflows" / "link-health.yml",
    ROOT / "scripts" / "validate_profile.py",
    ROOT / "scripts" / "check_links.py",
    ROOT / "tests" / "test_profile.py",
)

SECTION_ORDER = (
    "public-work",
    "research",
    "focus",
    "policy-standards",
    "principles",
    "stack",
    "collaboration",
    "scope",
)

MARKER_RE = re.compile(r"<!--\s*section:([a-z0-9-]+)\s*-->")
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
H2_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
ALLOWED_LINK_KINDS = {"profile", "project", "research"}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_links() -> dict:
    return json.loads(read(LINKS_FILE))


def validate_required_files() -> list[str]:
    return [
        f"missing required file: {path.relative_to(ROOT)}"
        for path in REQUIRED_FILES
        if not path.exists()
    ]


def validate_language_parity() -> list[str]:
    errors: list[str] = []
    en = read(README_EN)
    lv = read(README_LV)

    en_markers = tuple(MARKER_RE.findall(en))
    lv_markers = tuple(MARKER_RE.findall(lv))

    if en_markers != SECTION_ORDER:
        errors.append(
            f"README.md section markers differ from canonical order: {en_markers}"
        )
    if lv_markers != SECTION_ORDER:
        errors.append(
            f"README.lv.md section markers differ from canonical order: {lv_markers}"
        )
    if en_markers != lv_markers:
        errors.append("language section marker parity failed")

    if "[Latviski](README.lv.md)" not in en:
        errors.append("README.md is missing Latvian language link")
    if "[English](README.md)" not in lv:
        errors.append("README.lv.md is missing English language link")

    en_h2 = H2_RE.findall(en)
    lv_h2 = H2_RE.findall(lv)
    if len(en_h2) != len(SECTION_ORDER):
        errors.append(f"README.md expected {len(SECTION_ORDER)} H2 sections, found {len(en_h2)}")
    if len(lv_h2) != len(SECTION_ORDER):
        errors.append(f"README.lv.md expected {len(SECTION_ORDER)} H2 sections, found {len(lv_h2)}")

    return errors


def validate_registered_links() -> list[str]:
    errors: list[str] = []
    payload = load_links()

    if payload.get("schema_version") != 1:
        errors.append("data/links.json schema_version must be 1")

    links = payload.get("links")
    if not isinstance(links, list) or not links:
        return errors + ["data/links.json links must be a non-empty array"]

    ids: list[str] = []
    urls: list[str] = []
    en = read(README_EN)
    lv = read(README_LV)

    for item in links:
        if not isinstance(item, dict):
            errors.append("link registry entry must be an object")
            continue

        link_id = item.get("id")
        kind = item.get("kind")
        url = item.get("url")
        required = item.get("required_in_both_readmes")

        if kind not in ALLOWED_LINK_KINDS:
            errors.append(f"link {link_id!r} has invalid kind: {kind!r}")

        if not isinstance(required, bool):
            errors.append(
                f"link {link_id!r} required_in_both_readmes must be boolean"
            )

        if not isinstance(link_id, str) or not re.fullmatch(r"[a-z0-9_]+", link_id):
            errors.append(f"invalid link id: {link_id!r}")
        else:
            ids.append(link_id)

        if not isinstance(url, str):
            errors.append(f"link {link_id!r} has invalid url")
            continue

        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.netloc:
            errors.append(f"link {link_id!r} must use an absolute https URL: {url}")
        urls.append(url)

        if required is True:
            if url not in en:
                errors.append(f"registered link missing from README.md: {link_id}")
            if url not in lv:
                errors.append(f"registered link missing from README.lv.md: {link_id}")

    if len(ids) != len(set(ids)):
        errors.append("duplicate link id")
    if len(urls) != len(set(urls)):
        errors.append("duplicate registered URL")

    registered_urls = set(urls)
    readme_external_urls = {
        target
        for target in LINK_RE.findall(en + "\n" + lv)
        if target.startswith("https://")
    }

    for url in sorted(readme_external_urls - registered_urls):
        errors.append(f"README external URL is not registered: {url}")

    return errors


def validate_local_links() -> list[str]:
    errors: list[str] = []

    for path in (README_EN, README_LV):
        text = read(path)
        for target in LINK_RE.findall(text):
            if target.startswith(("https://", "mailto:", "#")):
                continue

            clean = target.split("#", 1)[0]
            if not clean:
                continue

            resolved = (path.parent / clean).resolve()
            try:
                resolved.relative_to(ROOT.resolve())
            except ValueError:
                errors.append(f"{path.name}: local link escapes repository: {target}")
                continue

            if not resolved.exists():
                errors.append(f"{path.name}: broken local link: {target}")

    return errors


def validate_text_hygiene() -> list[str]:
    errors: list[str] = []

    for path in (README_EN, README_LV):
        text = read(path)

        if "\t" in text:
            errors.append(f"{path.name}: tab character found")

        for lineno, line in enumerate(text.splitlines(), start=1):
            if line.rstrip() != line:
                errors.append(f"{path.name}:{lineno}: trailing whitespace")

        headings = H2_RE.findall(text)
        if len(headings) != len(set(headings)):
            errors.append(f"{path.name}: duplicate H2 heading")

        if "http://" in text:
            errors.append(f"{path.name}: insecure http URL found")

        if "<img" in text.lower():
            errors.append(f"{path.name}: raw HTML image tag is not allowed")

    return errors


def run_all() -> list[str]:
    errors: list[str] = []
    errors.extend(validate_required_files())
    if errors:
        return errors

    errors.extend(validate_language_parity())
    errors.extend(validate_registered_links())
    errors.extend(validate_local_links())
    errors.extend(validate_text_hygiene())
    return errors


def main() -> int:
    errors = run_all()
    if errors:
        print(f"Profile validation failed with {len(errors)} error(s):")
        for error in errors:
            print(f"- {error}")
        return 1

    payload = load_links()
    print(
        "Profile validation passed: "
        f"2 language variants, {len(SECTION_ORDER)} paired sections, "
        f"{len(payload['links'])} registered public links."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
