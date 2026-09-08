import httpx


async def scrape_text(url: str) -> str:
    api_url = f"https://r.jina.ai/{url}"
    headers = {
        "Accept": "text/plain",
        "User-Agent": "Mozilla/5.0 (compatible; CVE-OSINT-1/1.0)",
    }
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(api_url, headers=headers)
        resp.raise_for_status()
        return resp.text