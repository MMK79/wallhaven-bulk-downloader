import os
import asyncio
import aiofiles
import aiohttp
from aiolimiter import AsyncLimiter
from pathlib import Path
from tqdm import tqdm
from typing import List, Tuple
import time
import glob


# Configuration
DOWNLOAD_LIMIT = 4
CPU_WORKERS = os.cpu_count()
DOWNLOAD_PATH = Path("wallhaven_download")
API_ADDRESS = "https://wallhaven.cc/api/v1/w/"
API_CALL_LIMIT = AsyncLimiter(max_rate=45, time_period=60)
# API_CALL_LIMIT = AsyncLimiter(max_rate=5, time_period=60)


def api_token_tracker(set_timer : int = 60)-> None:
    """Track When your Token get accessable again"""
    for _ in tqdm(range(set_timer), desc="Until Your API Token get Free!", leave=False):
        time.sleep(1)


def get_all_captured_url_files() -> List[str]:
    captured_url_files = glob.glob("captured_url_*.txt")
    if captured_url_files:
        return captured_url_files
    raise Exception("Go Capture some url of your favorite images from Wallhaven")



async def concatenate_clipboard_files(captured_url_files: List[str])->str:
    """Gather all captured_url files and make a single whishlist.txt file"""
    async for captured_url_file in aiter(captured_url_files):
        async with aiofiles.open(captured_url_file) as f:




def retrieve_image_ids(
    wishlist_file: str = "wishlist.txt",
) -> List[str]:
    """read wishlist.txt file and extract image ids from url"""
    if not os.path.exists(wishlist_file):
        raise Exception("Create wishlist.txt with 1 link per line")

    with open(wishlist_file) as f:
        ids = [line.strip().split("/")[-1] for line in f.readlines() if line.strip()]
    return ids


def batch_ids(ids: List[str]) -> List[List[str]]:
    ids_batch = [ids[i : i + 45] for i in range(0, len(ids), 45)]
    return ids_batch


async def get_single_img_src(
    asession: aiohttp.ClientSession,
    id: str,
    api_address: str = API_ADDRESS,
    api_limit: AsyncLimiter = API_CALL_LIMIT,
):
    print(f"Working on {id}")
    async with api_limit:
        try:
            async with asession.get(api_address + id) as response:
                if response.status == 200:
                    data = await response.json()
                    src = data["data"]["path"]
                    print(f"[API] ✓ Got URL for {id}")
                    return (src, id)
                elif response.status == 429:
                    print(f"[API] ✗ {id} - Rate limited (429)")
                    return None
                else:
                    print(f"[API] ✗ {id} - Status {response.status}")
                    return None
        except Exception as e:
            print(f"[API] ✗ {id} - Error: {e}")
            return None


async def get_img_srcs(
    ids: List[str],
    api_address: str = API_ADDRESS,
    api_limit: AsyncLimiter = API_CALL_LIMIT,
) -> List[Tuple[str, str] | None]:
    time_out = aiohttp.ClientTimeout(total=60)
    try:
        async with aiohttp.ClientSession(timeout=time_out) as asession:
            coroutines = [
                get_single_img_src(asession, id, api_address, api_limit) for id in ids
            ]
            urls = await asyncio.gather(*coroutines, return_exceptions=True)
        return urls
    except Exception as e:
        print()


async def download_single_img(
    client: aiohttp.ClientSession, url: str, img_id: str, semaphore: asyncio.Semaphore
) -> Path:
    time_out = aiohttp.ClientTimeout(total=15)
    async with semaphore:
        print(f"[DL] Downloading {img_id}")
        response = await client.get(url, timeout=time_out, allow_redirects=True)

        file_name = url.split("/")[-1]
        download_path = DOWNLOAD_PATH / file_name

        async with aiofiles.open(download_path, "wb") as f:
            async for chunk in response.content.iter_chunked(8192):
                await f.write(chunk)

        print(f"[DL] ✓ Saved {img_id} to {download_path}")
        return download_path


async def download_imgs(
    urls_ids: List[Tuple[str, str] | BaseException | None],
) -> List[Path]:
    dl_semaphore = asyncio.Semaphore(DOWNLOAD_LIMIT)
    clean_urls_ids = [
        url_id
        for url_id in urls_ids
        if (url_id is not None) or (url_id is not BaseException)
    ]
    async with aiohttp.ClientSession() as client:
        coroutines = [
            download_single_img(
                client=client, url=url_id[0], img_id=url_id[1], semaphore=dl_semaphore
            )
            for url_id in clean_urls_ids
            if url_id is not None or BaseException
        ]
        img_paths = await asyncio.gather(*coroutines, return_exceptions=False)

    return img_paths


if __name__ == "__main__":
    concatenate_clipboard_files()
    # api_token_tracker()
    # print("[INFO] Reading image IDs from wishlist.txt")
    # ids = retrieve_image_ids()
    # print(f"[INFO] Found {len(ids)} image IDs\n")
    #
    # print("[INFO] Fetching image URLs from API (45 requests per 60 seconds)")
    # urls = asyncio.run(get_img_srcs(ids))
    #
    # print("[INFO] Downloading image URLs from API (45 requests per 60 seconds)")
    # download_imgs = asyncio.run(download_imgs(urls))
