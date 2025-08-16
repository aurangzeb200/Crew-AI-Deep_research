from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
from crewai_tools import SerperDevTool
import asyncio
from my_first_crew.tools.tool import scrape_text_and_links

class CrawlWebsiteInput(BaseModel):
    """Input schema for crawl_website tool."""
    url: str = Field(..., description="The full URL of the competitor's website Product or Services page to crawl. The url should be correct and accurate like https://example.com.")


class CrawlWebsiteTool(BaseTool):
    name: str = "fast_web_crawler"
    description: str = (
        "Extracts useful text content from a competitor's Product and Services pages."
    )
    args_schema: Type[BaseModel] = CrawlWebsiteInput

    def _run(self, url: str) -> str:
        asyncio.run(scrape_text_and_links(url))
        with open("page_text.txt", "r", encoding="utf-8") as f:
            all_text = f.read()
        return all_text


class FlexibleSerperDevInput(BaseModel):
    """Input schema for FlexibleSerperDevTool."""
    search_query: str = Field(..., description="The search query to search for information on the web")

class FlexibleSerperDevTool(SerperDevTool):  
    name: str = "FlexibleSerperDevTool"
    description: str = (
        "Use Serper DevTool to fetch real-time, up-to-date information from the web like news, "
        "facts, or recent data. Invoke it only when current or external information is needed."
    )
    args_schema: Type[BaseModel] = FlexibleSerperDevInput
    
    def _run(self, search_query: str) -> dict:
        return super()._run(search_query=search_query)