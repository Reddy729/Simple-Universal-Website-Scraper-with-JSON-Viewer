import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0 Safari/537.36"
)
REQUEST_TIMEOUT = 20
SCROLL_ATTEMPTS = 3


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_headers() -> Dict[str, str]:
    return {
        "User-Agent": USER_AGENT,
        "Accept-Language": "en-US,en;q=0.9",
    }


def _normalize_url(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.scheme:
        return f"https://{url}"
    return url


def _extract_metadata(soup: BeautifulSoup, url: str) -> Dict[str, Optional[str]]:
    title = soup.title.string.strip() if soup.title and soup.title.string else None
    description_tag = soup.find("meta", attrs={"name": "description"})
    description = description_tag.get("content") if description_tag else None
    canonical_tag = soup.find("link", rel="canonical")
    canonical = canonical_tag.get("href") if canonical_tag else None
    lang = soup.html.get("lang") if soup.html else None
    return {
        "title": title,
        "description": description,
        "canonical_url": urljoin(url, canonical) if canonical else None,
        "language": lang,
    }


def _extract_sections(soup: BeautifulSoup, base_url: str) -> List[Dict]:
    sections = []
    candidates = soup.find_all(["header", "main", "section", "footer"])
    if not candidates and soup.body:
        candidates = [soup.body]

    for idx, tag in enumerate(candidates):
        heading = tag.find(["h1", "h2", "h3", "h4"])
        label = heading.get_text(strip=True) if heading else f"section-{idx + 1}"
        text_content = " ".join(tag.stripped_strings)
        links = []
        for a in tag.find_all("a", href=True):
            links.append(
                {
                    "text": a.get_text(strip=True),
                    "href": urljoin(base_url, a["href"]),
                }
            )
        sections.append(
            {
                "label": label,
                "heading": heading.get_text(strip=True) if heading else None,
                "text": text_content[:5000],  # avoid oversized payloads
                "links": links[:50],
            }
        )
    return sections


def _should_fallback(sections: List[Dict]) -> bool:
    if not sections:
        return True
    total_text = sum(len(sec.get("text", "")) for sec in sections)
    return total_text < 500


def _build_response(
    url: str, source: str, soup: BeautifulSoup, raw_html: str
) -> Dict[str, object]:
    sections = _extract_sections(soup, url)
    return {
        "url": url,
        "fetched_at": _now_iso(),
        "source": source,
        "meta": _extract_metadata(soup, url),
        "sections": sections,
        "stats": {
            "section_count": len(sections),
            "html_length": len(raw_html),
        },
    }


def scrape_static(url: str) -> Tuple[Dict[str, object], List[str]]:
    errors: List[str] = []
    try:
        resp = requests.get(
            url,
            headers=_build_headers(),
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
    except Exception as exc:
        errors.append(f"static_fetch_error: {exc}")
        raise

    soup = BeautifulSoup(resp.text, "html.parser")
    parsed = _build_response(url, "static", soup, resp.text)
    if _should_fallback(parsed["sections"]):
        errors.append("insufficient_content_after_static")
    return parsed, errors


async def scrape_dynamic(url: str) -> Tuple[Dict[str, object], List[str]]:
    from playwright.async_api import async_playwright  # lazy import to keep startup fast

    errors: List[str] = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 720})
        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            for _ in range(SCROLL_ATTEMPTS):
                await page.mouse.wheel(0, 2000)
                await page.wait_for_timeout(800)

            try:
                load_more = page.get_by_text("load more", exact=False).first
                await load_more.click(timeout=2000)
                await page.wait_for_timeout(1200)
            except Exception:
                errors.append("load_more_not_found_or_click_failed")

            html = await page.content()
        except Exception as exc:
            errors.append(f"dynamic_error: {exc}")
            raise
        finally:
            await browser.close()

    soup = BeautifulSoup(html, "html.parser")
    parsed = _build_response(url, "dynamic", soup, html)
    return parsed, errors


async def scrape_url(raw_url: str) -> Dict[str, object]:
    url = _normalize_url(raw_url)
    trace: Dict[str, object] = {"errors": [], "attempts": []}

    try:
        static_result, static_errors = scrape_static(url)
        trace["attempts"].append({"mode": "static", "errors": static_errors})
        if not _should_fallback(static_result["sections"]):
            static_result["trace"] = trace
            return static_result
    except Exception as exc:
        trace["attempts"].append({"mode": "static", "errors": [str(exc)]})

    try:
        dynamic_result, dynamic_errors = await scrape_dynamic(url)
        trace["attempts"].append({"mode": "dynamic", "errors": dynamic_errors})
        dynamic_result["trace"] = trace
        return dynamic_result
    except Exception as exc:
        trace["errors"].append(f"dynamic_failed: {exc}")
        raise RuntimeError("Both static and dynamic scraping failed") from exc

