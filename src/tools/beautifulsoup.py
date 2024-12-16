import logging
import random
import time
from typing import Dict, List, Optional, Union

import requests
from bs4 import BeautifulSoup
from models.tool import Tool, ToolArgument
from pydantic import Field, PrivateAttr
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# List of common user agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
]


class BeautifulSoupAPIError(Exception):
    """Custom exception for BeautifulSoup API errors."""

    pass


class BeautifulSoupTool(Tool):
    _session: requests.Session = PrivateAttr()

    name: str = Field(
        "READ_WEBPAGE",
        description="A tool to read and parse web pages using BeautifulSoup.",
    )
    description: str = Field(
        """Read and parse a web page given its URL and return the page content with various options."""
    )

    arguments: List[ToolArgument] = [
        ToolArgument(
            name="url",
            type="string",
            description="The URL of the web page to read",
        ),
        ToolArgument(
            name="parser",
            type="string",
            description="The parser to use with BeautifulSoup (e.g., 'html.parser', 'lxml')",
            default="html.parser",
            required=False,
        ),
        ToolArgument(
            name="extract_type",
            type="string",
            description="Type of content to extract (text, links, images, all)",
            default="text",
            required=False,
        ),
        ToolArgument(
            name="timeout",
            type="int",
            description="Request timeout in seconds",
            default="30",
            required=False,
        ),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create a session with retry strategy"""
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def _get_headers(self) -> Dict[str, str]:
        """Generate random headers for the request"""
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    def _extract_content(
        self, soup: BeautifulSoup, extract_type: str
    ) -> Union[str, Dict]:
        """Extract specific content based on extract_type"""
        if extract_type == "text":
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            text = " ".join(soup.stripped_strings)
            return text

        if extract_type == "links":
            links = []
            for link in soup.find_all("a"):
                href = link.get("href")
                text = link.get_text(strip=True)
                if href:
                    links.append({"text": text, "url": href})
            return {"links": links}

        elif extract_type == "images":
            images = []
            for img in soup.find_all("img"):
                src = img.get("src")
                alt = img.get("alt", "")
                if src:
                    images.append({"src": src, "alt": alt})
            return {"images": images}

        elif extract_type == "all":
            return soup.prettify()

        return "Error: Invalid extract_type specified"

    def execute(
        self,
        url: str,
        parser: str = "html.parser",
        extract_type: str = "text",
        timeout: int = 30,
    ) -> str:
        """Execute reading a web page using BeautifulSoup and return the parsed content."""
        if not url.strip():
            logger.error("URL cannot be empty or whitespace.")
            return "Error: URL cannot be empty."

        try:
            # Add random delay to avoid rate limiting
            time.sleep(random.uniform(1, 3))

            # Ensure timeout is an integer
            timeout = int(timeout)

            response = self._session.get(
                url,
                headers=self._get_headers(),
                timeout=timeout,
                verify=True,  # SSL verification
            )

            response.raise_for_status()

            # Check content type
            content_type = response.headers.get("content-type", "").lower()
            if "text/html" not in content_type:
                logger.warning(f"Unexpected content type: {content_type}")
                return f"Error: Unexpected content type: {content_type}"

            # Detect and use correct encoding
            response.encoding = response.apparent_encoding

            soup = BeautifulSoup(response.text, parser)
            content = self._extract_content(soup, extract_type)

            logger.info(f"Successfully read web page: {url}")

            if isinstance(content, dict):
                return str(content)
            return content

        except requests.RequestException as e:
            logger.error(f"Request error for URL '{url}': {e}")
            return f"Error: {e}"
        except BeautifulSoupAPIError as e:
            logger.error(f"BeautifulSoupAPIError for URL '{url}': {e}")
            return f"Error: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error for URL '{url}': {e}")
            raise BeautifulSoupAPIError(f"Failed to read web page: {e}") from e