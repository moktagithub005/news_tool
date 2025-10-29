import os
import requests
from datetime import datetime, timedelta

# ✅ Load API Key
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

def fetch_newsapi(query: str, days_back: int = 2, page_size: int = 10):
    """
    Fetch news from NewsAPI with UPSC relevance filtering.
    """
    if not NEWS_API_KEY:
        print("❌ ERROR: NEWS_API_KEY missing in .env")
        return []

    base_url = "https://newsapi.org/v2/everything"
    from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

    # ✅ Default UPSC-enhanced query strategy
    if not query or query.strip() == "":
        query = "India AND Government"

    params = {
        "q": query,
        "from": from_date,
        "language": "en",
        "pageSize": page_size,
        "sortBy": "publishedAt",
        "apiKey": NEWS_API_KEY,
    }

    print(f"🔎 Fetching news for query: {query}")

    try:
        response = requests.get(base_url, params=params, timeout=10)
        data = response.json()

        if data.get("status") != "ok":
            print("⚠️ NewsAPI error:", data)
            return []

        articles = data.get("articles", [])

        # ✅ UPSC Filtering – keep India governance related news
        india_keywords = [
            "india", "delhi", "government", "parliament", "supreme court",
            "rbi", "economy", "scheme", "policy", "election", "budget"
        ]

        filtered = []
        for article in articles:
            text = (article.get("title", "") + " " + article.get("description", "")).lower()
            if any(k in text for k in india_keywords):
                filtered.append(article)

        if not filtered:
            print("⚠️ No India-specific results. Returning original NewsAPI articles.")
            return articles

        print(f"✅ Returning {len(filtered)} relevant articles")
        return filtered

    except Exception as e:
        print(f"❌ fetch_newsapi() failed: {e}")
        return []


# ✅ Wrapper used by backend – now fixed
def fetch_news(query: str, days_back: int = 2, page_size: int = 10,
               use_newsapi: bool = True, use_pib: bool = False, use_prs: bool = False):
    """
    Unified fetcher for FastAPI ingestion route.
    Currently supports only NewsAPI (use_newsapi=True).
    """
    if use_newsapi:
        return fetch_newsapi(query, days_back, page_size)
    return []
