#!/usr/bin/env python3
"""Remove AdSense/Ad Inserter markup and install the supplied Taboola placements."""

from __future__ import annotations

import base64
import binascii
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "site"
PUBLISHER_ID = "wansheng-network"
LAYOUT_MARKER = "<!-- taboola-layout:screenshot-d -->"

ADSENSE_LOADER_RE = re.compile(
    r"<script\b[^>]*\bsrc=(['\"])[^'\"]*pagead2\.googlesyndication\.com/pagead/js/adsbygoogle\.js[^'\"]*\1[^>]*>\s*</script>",
    re.IGNORECASE | re.DOTALL,
)
ADSENSE_BLOCK_RE = re.compile(
    r"<div\b[^>]*class=(['\"])[^'\"]*\bcode-block-2\b[^'\"]*\1[^>]*>.*?</div>",
    re.IGNORECASE | re.DOTALL,
)
ADSENSE_INS_RE = re.compile(
    r"<ins\b[^>]*class=(['\"])[^'\"]*\badsbygoogle\b[^'\"]*\1[^>]*>.*?</ins>",
    re.IGNORECASE | re.DOTALL,
)
ADSENSE_PUSH_RE = re.compile(
    r"<script\b[^>]*>\s*\(?\s*adsbygoogle\s*=\s*window\.adsbygoogle\s*\|\|\s*\[\]\s*\)?\.push\s*\(\s*\{\s*\}\s*\)\s*;?\s*</script>",
    re.IGNORECASE | re.DOTALL,
)
AD_INSERTER_RUNTIME_RE = re.compile(
    r"<script(?:\s[^>]*)?>(?:(?!</script>).)*?\bai_front\s*=.*?</script>",
    re.IGNORECASE | re.DOTALL,
)
ADSENSE_RESOURCE_RE = re.compile(
    r"<(?:link|script)\b[^>]*(?:googlesyndication|googleadservices|doubleclick\.net)[^>]*>(?:\s*</script>)?",
    re.IGNORECASE | re.DOTALL,
)
DATA_JAVASCRIPT_RE = re.compile(
    r"<script\b[^>]*\bsrc=(?P<quote>['\"])data:text/javascript;base64,"
    r"(?P<payload>[^'\"]+)(?P=quote)[^>]*>\s*</script>",
    re.IGNORECASE | re.DOTALL,
)
TABOOLA_MARKER_RE = re.compile(
    r"<!-- taboola:[^>]+ -->.*?<!-- /taboola:[^>]+ -->",
    re.IGNORECASE | re.DOTALL,
)
LAYOUT_MARKER_RE = re.compile(r"\s*<!-- taboola-layout:[^>]+ -->", re.IGNORECASE)

ENCODED_AD_MARKERS = (
    "ai_front",
    "ai_block_class_def",
    "adsbygoogle",
    "ad inserter",
    "automatically placed by adsense auto ads code",
)


def head_code(page_type: str) -> str:
    return f"""{LAYOUT_MARKER}
<!-- taboola:head-{page_type} -->
<style id="taboola-layout-guard">
  .taboola-placement {{
    box-sizing: border-box !important;
    display: block;
    width: 100% !important;
    max-width: 100% !important;
    margin-left: 0 !important;
    margin-right: 0 !important;
    overflow: hidden !important;
  }}
  .taboola-placement > div,
  .taboola-placement iframe,
  .taboola-placement .trc_rbox,
  .taboola-placement .trc_rbox_container,
  .taboola-placement .trc_related_container,
  .taboola-placement .tbl-feed-container {{
    box-sizing: border-box !important;
    min-width: 0 !important;
    width: 100% !important;
    max-width: 100% !important;
    overflow: hidden !important;
  }}
  .taboola-placement [style*="width"],
  .taboola-placement .videoCube,
  .taboola-placement .tbl-feed-card {{
    box-sizing: border-box !important;
    min-width: 0 !important;
    max-width: 100% !important;
  }}
  .taboola-placement img,
  .taboola-placement video {{
    max-width: 100% !important;
    height: auto !important;
  }}
  @media (max-width: 767px) {{
    .blog-over-single-content-box {{
      overflow-x: hidden;
    }}
    .taboola-placement {{
      margin-top: 24px !important;
      margin-bottom: 24px !important;
    }}
    .taboola-placement .videoCube,
    .taboola-placement .syndicatedItem,
    .taboola-placement .tbl-feed-card {{
      width: 100% !important;
      margin-left: 0 !important;
      margin-right: 0 !important;
    }}
  }}
</style>
<script id="taboola-loader">
(function () {{
    var PUBLISHER_ID = '{PUBLISHER_ID}';
    var PAGE_TYPE = '{page_type}';
    var LOADER_URL = '//cdn.taboola.com/libtrc/' + PUBLISHER_ID + '/loader.js';
    var LOADER_PRIVACY_URL = '//static.tblcontent.com/libtrc/' + PUBLISHER_ID + '/loader.privacy.js';
    var SCRIPT_ID = 'tb_loader_script';

    window._taboola = window._taboola || [];
    var pageTypePush = {{}};
    pageTypePush[PAGE_TYPE] = 'auto';
    window._taboola.push(pageTypePush);

    var firstScript = document.getElementsByTagName('script')[0];
    function injectLoader(id, src, fallbackSrc) {{
        if (document.getElementById(id)) return;
        var s = document.createElement('script');
        s.async = true;
        s.src = src;
        s.id = id;
        if (fallbackSrc) {{
            s.onerror = function () {{
                if (s.parentNode) s.parentNode.removeChild(s);
                injectLoader(SCRIPT_ID + '_fb', fallbackSrc, null);
            }};
        }}
        firstScript.parentNode.insertBefore(s, firstScript);
    }}

    injectLoader(SCRIPT_ID, LOADER_URL, LOADER_PRIVACY_URL);
    if (window.performance && typeof window.performance.mark === 'function') {{
        window.performance.mark('tbl_ic');
    }}
}})();
</script>
<!-- /taboola:head-{page_type} -->"""


def placement_code(marker: str, container: str, mode: str, placement: str) -> str:
    return f"""<!-- taboola:{marker} -->
<section class="taboola-placement taboola-{marker}" aria-label="Sponsored content" style="margin:32px 0;clear:both">
  <div id="{container}"></div>
  <script>
    window._taboola = window._taboola || [];
    window._taboola.push({{
      mode: '{mode}',
      container: '{container}',
      placement: '{placement}',
      target_type: 'mix'
    }});
  </script>
</section>
<!-- /taboola:{marker} -->"""


FLUSH_CODE = """<!-- taboola:flush -->
<script>
  window._taboola = window._taboola || [];
  window._taboola.push({flush: true});
</script>
<!-- /taboola:flush -->"""

HOME_WIDGET = placement_code(
    "homepage-widget-1",
    "taboola-homepage-widget-1",
    "thumbnails-a-1x1",
    "Homepage widget-1",
)
HOME_FEED = placement_code(
    "homepage-feed",
    "taboola-homepage-feed",
    "alternating-thumbnails-a",
    "Homepage Feed",
)
ARTICLE_WIDGET_1 = placement_code(
    "article-page-widget-1",
    "taboola-article-page-widget-1",
    "thumbnails-a-1x1",
    "Article page widget-1",
)
ARTICLE_WIDGET_2 = placement_code(
    "article-page-widget-2",
    "taboola-article-page-widget-2",
    "thumbnails-a-1x1",
    "Article page widget-2",
)
ARTICLE_FEED = placement_code(
    "article-page-feed",
    "taboola-article-page-feed",
    "thumbnails-a-1x1",
    "Article page Feed",
)


def is_article(path: Path) -> bool:
    relative = path.relative_to(ROOT).as_posix()
    return bool(re.fullmatch(r"20\d{2}/\d{2}/\d{2}/[^/]+/index\.html", relative))


def is_home(path: Path) -> bool:
    relative = path.relative_to(ROOT).as_posix()
    return relative == "index.html" or bool(re.fullmatch(r"page/\d+/index\.html", relative))


def remove_google_ads(text: str) -> tuple[str, int]:
    removed = 0

    def remove_encoded_ad_script(match: re.Match[str]) -> str:
        nonlocal removed
        payload = match.group("payload")
        try:
            decoded = base64.b64decode(payload, validate=True).decode("utf-8", errors="ignore")
        except (binascii.Error, ValueError):
            return match.group(0)
        if any(marker in decoded.lower() for marker in ENCODED_AD_MARKERS):
            removed += 1
            return ""
        return match.group(0)

    text = DATA_JAVASCRIPT_RE.sub(remove_encoded_ad_script, text)
    for pattern in (
        ADSENSE_BLOCK_RE,
        ADSENSE_LOADER_RE,
        ADSENSE_INS_RE,
        ADSENSE_PUSH_RE,
        AD_INSERTER_RUNTIME_RE,
        ADSENSE_RESOURCE_RE,
    ):
        text, count = pattern.subn("", text)
        removed += count
    return text, removed


def insert_before_close(text: str, tag: str, code: str) -> str:
    pattern = re.compile(rf"</{tag}>", re.IGNORECASE)
    updated, count = pattern.subn(code + f"\n</{tag}>", text, count=1)
    if count != 1:
        raise ValueError(f"Missing </{tag}> insertion point")
    return updated


def transform(path: Path, original: str) -> tuple[str, int, str | None]:
    page_type: str | None = None
    expected_markers: tuple[str, ...] = ()
    if is_home(path):
        page_type = "homepage"
        expected_markers = ("head-homepage", "homepage-widget-1", "homepage-feed", "flush")
    elif is_article(path):
        page_type = "article"
        expected_markers = (
            "head-article",
            "article-page-widget-1",
            "article-page-widget-2",
            "article-page-feed",
            "flush",
        )

    taboola_complete = LAYOUT_MARKER in original and bool(expected_markers) and all(
        original.count(f"<!-- taboola:{marker} -->") == 1
        and original.count(f"<!-- /taboola:{marker} -->") == 1
        for marker in expected_markers
    )
    text = original if taboola_complete else TABOOLA_MARKER_RE.sub("", original)
    if not taboola_complete:
        text = LAYOUT_MARKER_RE.sub("", text)
    text, removed = remove_google_ads(text)

    if page_type == "homepage" and not taboola_complete:
        text = insert_before_close(text, "head", head_code(page_type))
        text, first_count = re.subn(
            r"(<div class=['\"]blog-over-page-header-container['\"]></div>\s*<div class=['\"]blog-over-container['\"]>)",
            r"\1\n" + HOME_WIDGET,
            text,
            count=1,
            flags=re.IGNORECASE,
        )
        text, feed_count = re.subn(
            r"(<article\b[^>]*\bblog-over-modern-card\b.*?</article>\s*<article\b[^>]*\bblog-over-modern-card\b.*?</article>)",
            r"\1\n" + HOME_FEED,
            text,
            count=1,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if first_count != 1 or feed_count != 1:
            raise ValueError(f"Homepage placement anchors missing in {path}")
        text = insert_before_close(text, "body", FLUSH_CODE)

    elif page_type == "article" and not taboola_complete:
        text = insert_before_close(text, "head", head_code(page_type))
        text, title_count = re.subn(
            r"(</h1>)(\s*<div class=['\"]blog-over-single-meta['\"])",
            r"\1\n" + ARTICLE_WIDGET_1 + r"\n\2",
            text,
            count=1,
            flags=re.IGNORECASE,
        )
        text, paragraph_count = re.subn(
            r"(<div class=['\"]blog-over-single-content['\"][^>]*>.*?<p\b.*?</p>)",
            r"\1\n" + ARTICLE_WIDGET_2,
            text,
            count=1,
            flags=re.IGNORECASE | re.DOTALL,
        )
        # Most articles expose a share-buttons block immediately after the
        # article content.  Some older exports omit it and move straight to
        # the tag block, so accept that equivalent end-of-article anchor too.
        text, feed_count = re.subn(
            r"</div>(\s*<div class=['\"]blog-over-share-buttons['\"])",
            "</div>\n" + ARTICLE_FEED + r"\n\1",
            text,
            count=1,
            flags=re.IGNORECASE,
        )
        if feed_count == 0:
            text, feed_count = re.subn(
                r"</div>(\s*<div class=['\"]blog-over-single-tags['\"])",
                "</div>\n" + ARTICLE_FEED + r"\n\1",
                text,
                count=1,
                flags=re.IGNORECASE,
            )
        if title_count != 1 or paragraph_count != 1 or feed_count != 1:
            raise ValueError(f"Article placement anchor missing in {path}")
        text = insert_before_close(text, "body", FLUSH_CODE)

    text = re.sub(r"[ \t]+(?=\r?$)", "", text, flags=re.MULTILINE)
    return text, removed, page_type


def main() -> None:
    pending: dict[Path, str] = {}
    transformed: dict[Path, str] = {}
    removed_total = 0
    modified = 0
    home_pages = 0
    article_pages = 0

    for path in sorted(ROOT.rglob("*.html")):
        original = path.read_text(encoding="utf-8", errors="ignore")
        updated, removed, page_type = transform(path, original)
        transformed[path] = updated
        removed_total += removed
        home_pages += page_type == "homepage"
        article_pages += page_type == "article"
        if updated != original:
            pending[path] = updated
            modified += 1

    combined = "\n".join(transformed.values())
    forbidden = re.compile(
        r"adsbygoogle|pagead2\.googlesyndication\.com|ca-pub-|\bai_front\s*=",
        re.IGNORECASE,
    )
    if forbidden.search(combined):
        raise SystemExit("AdSense or Ad Inserter code remains after transformation")
    if home_pages != 4 or article_pages != 34:
        raise SystemExit(f"Unexpected page classification: home={home_pages}, article={article_pages}")

    for path, updated in pending.items():
        path.write_text(updated, encoding="utf-8")

    print(
        json.dumps(
            {
                "modified_html_files": modified,
                "removed_ad_fragments": removed_total,
                "homepage_taboola_pages": home_pages,
                "article_taboola_pages": article_pages,
            }
        )
    )


if __name__ == "__main__":
    main()
