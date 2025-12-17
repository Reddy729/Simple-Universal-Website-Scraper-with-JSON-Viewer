## Design Notes

- **Static-first strategy:** Requests + BeautifulSoup are used before Playwright to keep most scrapes fast and resource-light. A fallback triggers when static content is empty or very short.
- **Playwright usage:** Minimal headless Chromium session with three scroll attempts and one "load more" click attempt to surface lazy content.
- **Sectioning heuristic:** Collects `<header>`, `<main>`, `<section>`, and `<footer>` tags. Falls back to `<body>` if none found. Headings become labels when present; otherwise defaults to `section-n`.
- **Payload safety:** Section text is clipped at 5k characters and links are capped to 50 per section to avoid oversized responses.
- **Traceability:** Each scrape includes a `trace` block with attempts and errors to make behavior observable from the client.
- **Frontend goals:** Keep HTML/CSS/JS simple—form submission via fetch, loading status, section list with expandable JSON, and download button.

