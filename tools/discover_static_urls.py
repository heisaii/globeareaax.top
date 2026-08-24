#!/usr/bin/env python3
"""Discover same-origin URLs referenced by a downloaded static site."""

from __future__ import annotations

import argparse
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit, urlunsplit


URL_ATTRS = {
    "href",
    "src",
    "poster",
    "action",
    "data-src",
    "data-href",
    "data-lazy-src",
    "data-original",
    "data-bg",
}
TEXT_EXTENSIONS = {
    ".html",
    ".htm",
    ".css",
    ".js",
    ".mjs",
    ".xml",
    ".txt",
    ".json",
    ".webmanifest",
    ".svg",
}
CSS_URL_RE = re.compile(r"url\(\s*(['\"]?)(.*?)\1\s*\)", re.IGNORECASE)
IMPORT_RE = re.compile(r"@import\s+(?:url\()?\s*['\"]?([^'\"\s\)]+)", re.IGNORECASE)
ABSOLUTE_RE = re.compile(r"https?://(?:www\.)?funwsax\.top[^\s\"'<>\\)]+", re.IGNORECASE)


class ReferenceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.references: list[str] = []

    def handle_starttag(self, _tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if not value:
                continue
            key = name.lower()
            if key in URL_ATTRS:
                self.references.append(value)
            elif key in {"srcset", "data-srcset"}:
                for candidate in value.split(","):
                    url = candidate.strip().split(" ", 1)[0]
                    if url:
                        self.references.append(url)
            elif key == "style":
                self.references.extend(match[1] for match in CSS_URL_RE.findall(value))
            elif key == "content" and ("http://" in value or "https://" in value):
                self.references.append(value)


def base_url_for_file(root: Path, path: Path, origin: str) -> str:
    relative = path.relative_to(root).as_posix()
    if relative == "index.html":
        return origin + "/"
    if relative.endswith("/index.html"):
        return origin + "/" + relative[: -len("index.html")]
    return origin + "/" + relative


def normalize(candidate: str, base_url: str, host: str) -> str | None:
    candidate = candidate.strip().replace("&amp;", "&")
    if not candidate or candidate.startswith(("#", "data:", "mailto:", "tel:", "javascript:", "blob:")):
        return None

    absolute = urljoin(base_url, candidate)
    split = urlsplit(absolute)
    if split.scheme not in {"http", "https"}:
        return None
    if split.hostname not in {host, f"www.{host}"}:
        return None

    path = unquote(split.path or "/")
    lowered = path.lower()
    blocked_prefixes = (
        "/wp-admin",
        "/wp-login",
        "/wp-json",
        "/xmlrpc.php",
        "/wp-cron.php",
        "/wp-comments-post.php",
        "/cdn-cgi/",
    )
    if lowered.startswith(blocked_prefixes):
        return None
    if lowered.endswith(("/feed/", "/comments/feed/", "/trackback/", "/embed/")):
        return None
    if lowered.endswith(".php"):
        return None

    # Query strings on WordPress assets are only cache-busters. Dynamic search,
    # preview, and comment URLs cannot be represented by a static host.
    clean = urlunsplit(("https", host, split.path or "/", "", ""))
    return clean


def references_from_file(root: Path, path: Path, origin: str) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []

    suffix = path.suffix.lower()
    references: list[str] = []
    if suffix in {".html", ".htm"} or path.name == "index.html":
        parser = ReferenceParser()
        parser.feed(text)
        references.extend(parser.references)
    if suffix in {".css", ".html", ".htm", ".svg"}:
        references.extend(match[1] for match in CSS_URL_RE.findall(text))
        references.extend(IMPORT_RE.findall(text))
    if suffix in TEXT_EXTENSIONS:
        references.extend(ABSOLUTE_RE.findall(text))
    return references


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--host", default="funwsax.top")
    args = parser.parse_args()

    root = args.root.resolve()
    origin = f"https://{args.host}"
    discovered: set[str] = {origin + "/"}

    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        base_url = base_url_for_file(root, path, origin)
        for candidate in references_from_file(root, path, origin):
            normalized = normalize(candidate, base_url, args.host)
            if normalized:
                discovered.add(normalized)

    print(json.dumps(sorted(discovered), ensure_ascii=False))


if __name__ == "__main__":
    main()
