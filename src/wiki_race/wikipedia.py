from __future__ import annotations

from urllib.parse import unquote

import requests
from bs4 import BeautifulSoup

from .constants import LINK_BLACKLIST, WIKI_BASE


WIKI_HEADERS = {"User-Agent": "WikiRaceAI/1.0"}


def article_name(url: str) -> str:
    return unquote(url.split("/wiki/")[-1]).replace("_", " ")


def article_url(article_name_text: str) -> str:
    return f"{WIKI_BASE}/wiki/{article_name_text.replace(' ', '_')}"


def path_to_titles(history: list[str]) -> list[str]:
    return [article_name(url) for url in history]


def get_wiki_page(url: str) -> tuple[str, list[str]]:
    try:
        response = requests.get(url, timeout=10, headers=WIKI_HEADERS)
        if response.status_code != 200:
            return "", []

        soup = BeautifulSoup(response.text, "html.parser")
        content = soup.find("div", {"id": "mw-content-text"})
        page_text = (content.get_text() if content else soup.get_text())[:3000]

        seen: set[str] = set()
        links: list[str] = []
        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            if href.startswith("/wiki/") and ":" not in href and href not in seen and href not in LINK_BLACKLIST:
                seen.add(href)
                links.append(f"{WIKI_BASE}{href}")

        return page_text, links[:120]
    except Exception:
        return "", []
