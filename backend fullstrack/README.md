# Simple Universal Website Scraper 

This project is a beginner-friendly MVP that scrapes a web page, organizes content into section-aware JSON, and presents it through a minimal FastAPI + Jinja2 frontend.

## Features
- `GET /healthz` health endpoint.
- `POST /scrape` static scraping (requests + BeautifulSoup) with Playwright fallback.
- Extracts page title, description, language, canonical URL, and sectioned content.
- Three scroll attempts and a single "load more" click attempt in dynamic mode.
- Frontend form to submit a URL, view per-section JSON, and download the result.

## Quickstart
1. Install dependencies:
   ```bash
   python -m pip install -r requirements.txt
   playwright install chromium
   ```
2. Run the dev server:
   ```bash
   ./run.sh
   ```
3. Open http://localhost:8000 and scrape any public URL.

## JSON Shape
```json
{
  "url": "https://example.com",
  "fetched_at": "... ISO timestamp ...",
  "source": "static | dynamic",
  "meta": {
    "title": "...",
    "description": "...",
    "canonical_url": "...",
    "language": "en"
  },
  "sections": [
    {
      "label": "section-1",
      "heading": "Heading text",
      "text": "Clipped section text...",
      "links": [{ "text": "More", "href": "https://example.com/more" }]
    }
  ],
  "stats": { "section_count": 1, "html_length": 12345 },
  "trace": {
    "attempts": [{ "mode": "static", "errors": [] }]
  }
}
```

## Notes
- Static scraping returns immediately unless content is too thin, in which case Playwright is attempted.
- Errors are recorded in the `trace` block; unhandled failures return HTTP 500.
- The frontend keeps dependencies minimal and focuses on JSON display and download.


