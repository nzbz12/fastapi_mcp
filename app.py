import os
from typing import List, Dict

import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify, render_template, request


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/search")
    def api_search():
        query = request.args.get("q", "").strip()
        try:
            max_results = int(request.args.get("num", 10))
        except ValueError:
            max_results = 10

        if not query:
            return jsonify({"error": "missing 'q' query parameter"}), 400

        try:
            results = fetch_duckduckgo_results(query=query, max_results=max_results)
            return jsonify({"query": query, "results": results})
        except Exception as exc:  # pragma: no cover - simple demo error handling
            return jsonify({"error": str(exc)}), 500

    return app


def fetch_duckduckgo_results(query: str, max_results: int = 10, timeout_seconds: int = 12) -> List[Dict[str, str]]:
    """Scrape DuckDuckGo HTML results for a query.

    Uses the HTML-only endpoint to avoid client-side JS. Parsing is designed to be
    tolerant to minor markup changes by checking multiple selectors.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }

    # HTML endpoint better suited for scraping than the JS-heavy main page
    url = "https://html.duckduckgo.com/html/"
    params = {"q": query}
    response = requests.get(url, params=params, headers=headers, timeout=timeout_seconds)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    results: List[Dict[str, str]] = []

    # Common selectors across DuckDuckGo HTML variants
    for result in soup.select("div.result, div.web-result, div.result--url-above-snippet"):
        link_el = result.select_one("a.result__a, a.result__url, h2 a")
        if not link_el or not link_el.get("href"):
            continue

        title = link_el.get_text(strip=True)
        href = link_el.get("href")

        # Snippet candidates
        snippet_el = (
            result.select_one("a.result__snippet")
            or result.select_one("div.result__snippet")
            or result.select_one("div.result__summary")
            or result.select_one("div.snippet")
        )
        snippet = snippet_el.get_text(" ", strip=True) if snippet_el else ""

        results.append({"title": title, "url": href, "snippet": snippet})

        if len(results) >= max_results:
            break

    return results


if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)

