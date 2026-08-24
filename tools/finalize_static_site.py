#!/usr/bin/env python3
"""Finalize the mirrored WordPress output for a static custom-domain deploy."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "site"
OLD_DOMAIN = "funwsax.top"
NEW_DOMAIN = "globeareaax.top"
OLD_BRAND = "FunWSAX"
NEW_BRAND = "GlobeAreaAX"
TEXT_SUFFIXES = {".html", ".htm", ".css", ".js", ".mjs", ".xml", ".txt", ".json", ".svg"}


def rewrite_search_form(match: re.Match[str]) -> str:
    form = match.group(0)
    start_match = re.match(r"<form\b[^>]*>", form, flags=re.IGNORECASE | re.DOTALL)
    if not start_match:
        return form
    start = start_match.group(0)
    if not re.search(r"(?:role|class)\s*=\s*(['\"])[^'\"]*search", start, flags=re.IGNORECASE):
        return form

    if re.search(r"\baction\s*=", start, flags=re.IGNORECASE):
        start = re.sub(r"\baction\s*=\s*(['\"])[^'\"]*\1", 'action="/search/"', start, flags=re.IGNORECASE)
    else:
        start = start[:-1] + ' action="/search/">'
    if re.search(r"\bmethod\s*=", start, flags=re.IGNORECASE):
        start = re.sub(r"\bmethod\s*=\s*(['\"])[^'\"]*\1", 'method="get"', start, flags=re.IGNORECASE)
    else:
        start = start[:-1] + ' method="get">'

    body = form[start_match.end() :]
    body = re.sub(r"\bname\s*=\s*(['\"])s\1", 'name="q"', body, flags=re.IGNORECASE)
    return start + body


def decode_cloudflare_email(match: re.Match[str]) -> str:
    encoded = match.group(1)
    try:
        key = int(encoded[:2], 16)
        decoded = bytes(int(encoded[index : index + 2], 16) ^ key for index in range(2, len(encoded), 2)).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return 'href="/"'
    decoded = decoded.replace(f"www.{OLD_DOMAIN}", NEW_DOMAIN).replace(OLD_DOMAIN, NEW_DOMAIN)
    decoded = decoded.replace(OLD_BRAND, NEW_BRAND)
    return f'href="mailto:{html.escape(decoded, quote=True)}"'


def clean_html(text: str) -> str:
    text = re.sub(
        r"<link\b[^>]*type=(['\"])application/(?:rss|rdf)\+xml\1[^>]*?/?>",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"<link\b[^>]*rel=(['\"])EditURI\1[^>]*?/?>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<link\b[^>]*rel=(['\"])https://api\.w\.org/\1[^>]*?/?>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<link\b[^>]*title=(['\"])oEmbed[^>]*?/?>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<meta\b[^>]*name=(['\"])generator\1[^>]*?/?>", "", text, flags=re.IGNORECASE)
    text = re.sub(
        r"<script\b[^>]*wp-statistics-tracker-js[^>]*>.*?</script>",
        "",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    text = re.sub(
        r"<script\b[^>]*email-decode\.min\.js[^>]*>.*?</script>",
        "",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    text = re.sub(
        r'href=["\']/cdn-cgi/l/email-protection#([0-9a-f]+)["\']',
        decode_cloudflare_email,
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"<form\b[^>]*id=(['\"])commentform\1[^>]*>.*?</form>",
        '<p class="comments-closed">Comments are closed on this static archive.</p>',
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    text = re.sub(r"<form\b.*?</form>", rewrite_search_form, text, flags=re.IGNORECASE | re.DOTALL)
    return text


def plain_text(fragment: str) -> str:
    fragment = re.sub(r"<script\b.*?</script>|<style\b.*?</style>", " ", fragment, flags=re.IGNORECASE | re.DOTALL)
    fragment = re.sub(r"<[^>]+>", " ", fragment)
    return " ".join(html.unescape(fragment).split())


def build_search_index() -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for path in sorted(ROOT.glob("20??/??/??/*/index.html")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        title_match = re.search(r"<title>(.*?)</title>", text, flags=re.IGNORECASE | re.DOTALL)
        title = plain_text(title_match.group(1)) if title_match else path.parent.name.replace("-", " ").title()
        title = re.split(r"\s+[–—-]\s+GlobeAreaAX\b", title, maxsplit=1)[0]

        article_match = re.search(r"<article\b.*?</article>", text, flags=re.IGNORECASE | re.DOTALL)
        content = plain_text(article_match.group(0) if article_match else text)
        excerpt = content[:260].rsplit(" ", 1)[0] + ("…" if len(content) > 260 else "")
        url = "/" + path.relative_to(ROOT).parent.as_posix() + "/"
        records.append({"title": title, "url": url, "excerpt": excerpt, "content": content})
    return records


def main() -> None:
    rewritten = 0
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        updated = text.replace(f"www.{OLD_DOMAIN}", NEW_DOMAIN).replace(OLD_DOMAIN, NEW_DOMAIN)
        updated = updated.replace(OLD_BRAND, NEW_BRAND)
        if path.suffix.lower() in {".html", ".htm"}:
            updated = clean_html(updated)
        if updated != text:
            path.write_text(updated, encoding="utf-8")
            rewritten += 1

    records = build_search_index()
    (ROOT / "search-index.json").write_text(
        json.dumps(records, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(json.dumps({"rewritten_files": rewritten, "search_records": len(records)}))


if __name__ == "__main__":
    main()
