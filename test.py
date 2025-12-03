# ============ config.py ============
import os
from pathlib import Path


class Config:
    # Directories
    BASE_DIR = Path(__file__).parent
    DOWNLOAD_DIR = BASE_DIR / "downloads"
    LOGS_DIR = BASE_DIR / "logs"

    # Settings
    CHECK_INTERVAL = 0.5  # seconds
    TARGET_SITE = "wallhaven"
    MAX_CONCURRENT_DOWNLOADS = 3

    # Ensure directories exist
    DOWNLOAD_DIR.mkdir(exist_ok=True)
    LOGS_DIR.mkdir(exist_ok=True)


# ============ utils.py ============
import re
from datetime import datetime


def is_url(text):
    """Check if text is a valid URL"""
    url_pattern = re.compile(
        r"^https?://"
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"
        r"localhost|"
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
        r"(?::\d+)?"
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE,
    )
    return url_pattern.match(text) is not None


def contains_target(url, target):
    """Check if URL contains target string"""
    return target.lower() in url.lower()


def get_timestamp():
    """Get formatted timestamp"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log_message(message, level="INFO"):
    """Log a message with timestamp"""
    timestamp = get_timestamp()
    print(f"[{timestamp}] [{level}] {message}")


# ============ clipboard_monitor.py ============
import pyperclip
import time
from utils import is_url, contains_target, log_message
from config import Config


class ClipboardMonitor:
    def __init__(self, callback=None, target_site=None):
        """
        Initialize clipboard monitor

        Args:
            callback: Function to call when URL is captured
            target_site: Only capture URLs containing this string (optional)
        """
        self.callback = callback
        self.target_site = target_site or Config.TARGET_SITE
        self.captured_urls = []
        self.last_clipboard = ""
        self.is_running = False

    def start(self):
        """Start monitoring clipboard"""
        self.is_running = True
        log_message(f"Clipboard monitor started (filtering: {self.target_site})")

        try:
            while self.is_running:
                current_clipboard = pyperclip.paste()

                if current_clipboard != self.last_clipboard:
                    if is_url(current_clipboard) and contains_target(
                        current_clipboard, self.target_site
                    ):
                        self._on_url_captured(current_clipboard)

                    self.last_clipboard = current_clipboard

                time.sleep(Config.CHECK_INTERVAL)

        except KeyboardInterrupt:
            self.stop()

    def _on_url_captured(self, url):
        """Handle captured URL"""
        log_message(f"URL captured: {url}", "SUCCESS")
        self.captured_urls.append(url)

        # Call the callback if provided
        if self.callback:
            self.callback(url)

    def stop(self):
        """Stop monitoring"""
        self.is_running = False
        log_message(f"Clipboard monitor stopped. Total URLs: {len(self.captured_urls)}")
        return self.captured_urls

    def get_captured_urls(self):
        """Get all captured URLs"""
        return self.captured_urls


# ============ scraper.py ============
import requests
from bs4 import BeautifulSoup
from utils import log_message


class WallhavenScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        )

    def get_image_url(self, page_url):
        """
        Extract direct image URL from Wallhaven page

        Args:
            page_url: Wallhaven page URL (e.g., https://wallhaven.cc/w/123456)

        Returns:
            Direct image URL or None if not found
        """
        try:
            log_message(f"Scraping: {page_url}")
            response = self.session.get(page_url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            # Wallhaven stores the image in an <img> tag with id="wallpaper"
            img_tag = soup.find("img", {"id": "wallpaper"})

            if img_tag and img_tag.get("src"):
                image_url = img_tag["src"]
                log_message(f"Image URL found: {image_url}", "SUCCESS")
                return image_url
            else:
                log_message("Could not find image URL on page", "WARNING")
                return None

        except Exception as e:
            log_message(f"Scraping error: {str(e)}", "ERROR")
            return None

    def get_image_info(self, page_url):
        """Get additional image information"""
        try:
            response = self.session.get(page_url, timeout=10)
            soup = BeautifulSoup(response.content, "html.parser")

            info = {"image_url": None, "resolution": None, "tags": []}

            # Get image URL
            img_tag = soup.find("img", {"id": "wallpaper"})
            if img_tag:
                info["image_url"] = img_tag.get("src")

            # Get resolution
            res_tag = soup.find("h3", class_="showcase-resolution")
            if res_tag:
                info["resolution"] = res_tag.text.strip()

            # Get tags
            tag_elements = soup.find_all("a", class_="tagname")
            info["tags"] = [tag.text.strip() for tag in tag_elements]

            return info

        except Exception as e:
            log_message(f"Error getting image info: {str(e)}", "ERROR")
            return None


# ============ downloader.py ============
import requests
from pathlib import Path
from urllib.parse import urlparse
from config import Config
from utils import log_message


class ImageDownloader:
    def __init__(self, download_dir=None):
        """
        Initialize downloader

        Args:
            download_dir: Directory to save images (default: from config)
        """
        self.download_dir = Path(download_dir) if download_dir else Config.DOWNLOAD_DIR
        self.download_dir.mkdir(exist_ok=True)
        self.session = requests.Session()

    def download(self, image_url, filename=None):
        """
        Download image from URL

        Args:
            image_url: Direct image URL
            filename: Custom filename (optional, will extract from URL if not provided)

        Returns:
            Path to downloaded file or None if failed
        """
        try:
            log_message(f"Downloading: {image_url}")

            # Generate filename if not provided
            if not filename:
                filename = Path(urlparse(image_url).path).name

            filepath = self.download_dir / filename

            # Download
            response = self.session.get(image_url, stream=True, timeout=30)
            response.raise_for_status()

            # Save
            with open(filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            log_message(f"Downloaded: {filepath}", "SUCCESS")
            return filepath

        except Exception as e:
            log_message(f"Download error: {str(e)}", "ERROR")
            return None

    def download_from_page(self, page_url, scraper):
        """
        Download image from Wallhaven page URL

        Args:
            page_url: Wallhaven page URL
            scraper: WallhavenScraper instance

        Returns:
            Path to downloaded file or None
        """
        image_url = scraper.get_image_url(page_url)

        if image_url:
            return self.download(image_url)
        else:
            log_message("Cannot download: no image URL found", "ERROR")
            return None


# ============ main.py ============
from clipboard_monitor import ClipboardMonitor
from scraper import WallhavenScraper
from downloader import ImageDownloader
from utils import log_message


def process_url(url):
    """Process captured URL: scrape and download"""
    scraper = WallhavenScraper()
    downloader = ImageDownloader()

    # Download the image
    result = downloader.download_from_page(url, scraper)

    if result:
        log_message(f"Successfully saved: {result}", "SUCCESS")
    else:
        log_message(f"Failed to download from: {url}", "ERROR")


def main():
    """Main entry point"""
    print("=" * 60)
    print("Wallhaven Auto-Downloader")
    print("=" * 60)
    print("\nThis program will:")
    print("1. Monitor your clipboard for Wallhaven URLs")
    print("2. Automatically scrape the image URL")
    print("3. Download the image to the downloads folder")
    print("\nPress Ctrl+C to stop\n")
    print("=" * 60 + "\n")

    # Create monitor with callback
    monitor = ClipboardMonitor(callback=process_url)

    try:
        monitor.start()
    except KeyboardInterrupt:
        urls = monitor.stop()
        print(f"\n\nTotal URLs processed: {len(urls)}")


if __name__ == "__main__":
    main()
