from bs4 import BeautifulSoup
import requests
import os
from os import listdir
import asyncio
import aiohttp
from typing import List


def retreive_images_links(
    wishlist_file: str = "whishlist.txt",
) -> List[str]:
    """Open wishlist.txt file
    Return: list of images links url
    """
    if not os.path.exists(wishlist_file):
        raise Exception("Create images_download_list.txt with 1 link per line")

    with open(wishlist_file, "r") as f:
        # line.strip() -> remove spaces at the beginning and at the end of the string
        # file.readlines() -> return list containing each line in the file as a list item
        links = [line.strip() for line in f.readlines() if line.strip()]
    return links


def batching(image_list=retreive_images_links()):
    """Split into batches of max 45"""
    # there is no limit for the end part of slicing in list
    return [image_list[i : i + 45] for i in range(0, len(image_list), 45)]


async def fetch_html(session, link):
    """Async HTTP Get HTML"""
    async with session.get(link) as result:
        return await result.text()


async def image_data_extractor(session, link):
    """Extract image src + id from a link."""
    html = await fetch_html(session, link)
    soup = BeautifulSoup(html, "lxml")

    main_tag = soup.find("main")
    if not main_tag:
        return None

    img_tag = main_tag.find("img")
    if not img_tag:
        return None

    image_url = img_tag["src"]
    image_id = image_url.split("/")[-1]

    return image_url, image_id


async def scrap_image_links():
    """Returns list of (image_url, image_id)"""
    links = retreive_images_links()
    batches = batching(links)

    results = []

    async with aiohttp.ClientSession() as session:
        for batch in batches:
            tasks = [image_data_extractor(session, link) for link in batch]
            batch_results = await asyncio.gather(*tasks)
            results.extend([res for res in batch_results if res])
    return results


async def download_image(session, image_url, file_path):
    """Async download of a single image."""
    async with session.get(image_url) as res:
        content = await res.read()

    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(content)


async def download_images():
    """Download all scraped images asynchronously."""
    download_path = "/Volumes/MASOUD/Gallery/"
    images = await scrap_image_links()

    async with aiohttp.ClientSession() as session:
        tasks = []
        for img_url, img_id in images:
            file_path = os.path.join(download_path, img_id)
            tasks.append(download_image(session, img_url, file_path))

        await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(download_images())
