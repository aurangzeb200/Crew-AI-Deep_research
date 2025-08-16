import nest_asyncio
import tldextract  
from playwright.async_api import async_playwright
from my_first_crew.tools.scrape_page import scrape_single_url

nest_asyncio.apply()

def extract_main_domain(url: str) -> str:
    """Extracts the main domain like 'openai' from a given URL."""
    extracted = tldextract.extract(url)
    return extracted.domain.lower()

async def scrape_text_and_links(url):
    target_domain = extract_main_domain(url)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/116.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 720},
        )
        page = await context.new_page()

        await page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => false});"
        )

        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            page_text = await page.evaluate("() => document.body.innerText")
            links = await page.eval_on_selector_all(
                "a",
                """elements => elements.map(el => el.href)"""
            )
        except Exception as e:
            await browser.close()
            return
        await browser.close()

        # Clean links
        links = [link for link in links if link and link.startswith("http")]

        # Save page text
        with open("page_text.txt", "w", encoding="utf-8") as f:
            f.write(page_text)

        # Separate matching & denied URLs
        matching_links = [link for link in links if extract_main_domain(link) == target_domain]

        for i, link in enumerate(matching_links, 1):
            await scrape_single_url(link)