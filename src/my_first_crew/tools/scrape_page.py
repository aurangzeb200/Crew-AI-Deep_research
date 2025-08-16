import asyncio
from playwright.async_api import async_playwright
import nest_asyncio

nest_asyncio.apply()
with open("page_text.txt", "w", encoding="utf-8"): pass

async def scrape_single_url(url: str, OUTPUT_FILE: str = "page_text.txt", MAX_RETRIES: int = 3, MIN_TEXT_LENGTH: int =100):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/116.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()
        text_content = ""

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_selector("body", timeout=10000)

                # Extract content while excluding nav, footer, ads, etc.
                text = await page.evaluate("""
                    () => {
                        const unwantedSelectors = [
                            'nav', 'footer', 'header', 'aside',
                            '.sidebar', '.advertisement', '.ads', '[role="banner"]',
                            '[role="navigation"]', '[role="contentinfo"]',
                            'script', 'style', 'noscript'
                        ];
                        
                        // Remove unwanted elements from DOM copy
                        unwantedSelectors.forEach(sel => {
                            document.querySelectorAll(sel).forEach(el => el.remove());
                        });

                        // Grab main readable content
                        const elements = document.querySelectorAll(
                            'main p, main h1, main h2, main h3, main h4, main li, main blockquote, ' +
                            'article p, article h1, article h2, article h3, article h4, article li, article blockquote, ' +
                            'body p, body h1, body h2, body h3, body h4, body li, body blockquote'
                        );

                        return Array.from(elements)
                            .map(el => el.innerText.trim())
                            .filter(t => t.length > 0)
                            .join("\\n\\n")
                            .replace(/\\s+/g, ' ')
                            .trim();
                    }
                """)

                if len(text) >= MIN_TEXT_LENGTH:
                    text_content = text
                    break
                else:
                    continue
                
            except Exception as e:
                continue
        await browser.close()

        if text_content:
            with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
                f.write(f"--- Content from {url} ---\n{text_content}\n\n")
        else:
            print("")