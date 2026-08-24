#!/usr/bin/env python3
"""Check internal references and migration invariants for the static site."""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit


ROOT = Path(__file__).resolve().parents[1] / "site"
HOST = "globeareaax.top"
OLD_HOST = "funwsax.top"
TEXT_SUFFIXES = {".html", ".htm", ".css", ".js", ".mjs", ".xml", ".txt", ".json", ".svg"}
CSS_URL_RE = re.compile(r"url\(\s*(['\"]?)(.*?)\1\s*\)", re.IGNORECASE)


class Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.values: list[str] = []

    def handle_starttag(self, _tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if not value:
                continue
            if name.lower() in {"href", "src", "poster", "action", "data-src", "data-lazy-src"}:
                self.values.append(value)
            elif name.lower() in {"srcset", "data-srcset"}:
                self.values.extend(part.strip().split(" ", 1)[0] for part in value.split(","))


def public_url(path: Path) -> str:
    rel = path.relative_to(ROOT).as_posix()
    if rel == "index.html":
        return f"https://{HOST}/"
    if rel.endswith("/index.html"):
        return f"https://{HOST}/" + rel[: -len("index.html")]
    return f"https://{HOST}/" + rel


def local_target(url: str, base: str) -> Path | None:
    url = url.strip()
    if not url or url.startswith(("#", "data:", "mailto:", "tel:", "javascript:", "blob:")):
        return None
    split = urlsplit(urljoin(base, url))
    if split.hostname not in {HOST, f"www.{HOST}"}:
        return None
    path = unquote(split.path or "/").lstrip("/")
    if not path:
        return ROOT / "index.html"
    target = ROOT / path
    if path.endswith("/") or not Path(path).suffix:
        target = target / "index.html"
    return target


def main() -> None:
    html_files = sorted(ROOT.rglob("*.html"))
    missing: dict[str, list[str]] = {}
    old_domain_files: list[str] = []
    php_asset_refs: list[str] = []

    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if OLD_HOST in text:
            old_domain_files.append(path.relative_to(ROOT).as_posix())
        if re.search(r"wp-content/[^'\"\s<>]+\.php(?:[?'\"\s<>]|$)", text):
            php_asset_refs.append(path.relative_to(ROOT).as_posix())

        candidates: list[str] = []
        if path.suffix.lower() in {".html", ".htm"}:
            parser = Links()
            parser.feed(text)
            candidates.extend(parser.values)
        if path.suffix.lower() in {".html", ".htm", ".css", ".svg"}:
            candidates.extend(match[1] for match in CSS_URL_RE.findall(text))

        base = public_url(path)
        for candidate in candidates:
            target = local_target(candidate, base)
            if target is not None and not target.is_file():
                key = target.relative_to(ROOT).as_posix()
                missing.setdefault(key, []).append(path.relative_to(ROOT).as_posix())

    report = {
        "html_files": len(html_files),
        "all_files": sum(1 for path in ROOT.rglob("*") if path.is_file()),
        "old_domain_files": old_domain_files,
        "php_asset_reference_files": php_asset_refs,
        "missing_internal_targets": {key: sorted(set(value))[:5] for key, value in sorted(missing.items())},
        "largest_file_bytes": max(path.stat().st_size for path in ROOT.rglob("*") if path.is_file()),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if old_domain_files or php_asset_refs or missing:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
