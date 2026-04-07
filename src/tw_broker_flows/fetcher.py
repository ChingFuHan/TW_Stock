from __future__ import annotations

from datetime import datetime, timezone
import re
import ssl
from typing import Any
import urllib.request


META_CHARSET_PATTERN = re.compile(br"charset=['\"]?([A-Za-z0-9_-]+)", re.I)


FetchResult = dict[str, Any]


def detect_encoding(content: bytes, headers: dict[str, str]) -> str:
    content_type = headers.get("Content-Type", "")
    header_match = re.search(r"charset=([A-Za-z0-9_-]+)", content_type, re.I)
    if header_match:
        return header_match.group(1)

    meta_match = META_CHARSET_PATTERN.search(content[:2000])
    if meta_match:
        return meta_match.group(1).decode("ascii", errors="ignore")

    return "utf-8"


def decode_content(content: bytes, encoding: str) -> str:
    return content.decode(encoding, errors="replace")


def fetch_url(url: str, timeout: int = 30) -> FetchResult:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; tw-broker-flow-scraper/0.1)"},
    )

    with urllib.request.urlopen(request, timeout=timeout, context=ssl.create_default_context()) as response:
        content = response.read()
        headers = dict(response.headers.items())
        encoding = detect_encoding(content, headers)
        return {
            "url": url,
            "status_code": getattr(response, "status", 200),
            "headers": headers,
            "content": content,
            "encoding": encoding,
            "text": decode_content(content, encoding),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
