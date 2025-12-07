import os
import asyncio
from os.path import exists
import aiofiles
import aiohttp
from aiolimiter import AsyncLimiter
from pathlib import Path
from typing import List, Tuple
import glob
import csv

# Other solution
# from pandas.io.clipboard import clipboard_get
from types import FunctionType
import pyperclip
import time

# work with regax
import re
from datetime import datetime


# Configuration
DOWNLOAD_LIMIT = 4
CPU_WORKERS = os.cpu_count()
DOWNLOAD_DIR = Path("wallhaven_download")
API_ADDRESS = "https://wallhaven.cc/api/v1/w/"
API_CALL_LIMIT = AsyncLimiter(max_rate=45, time_period=60)
# API_CALL_LIMIT = AsyncLimiter(max_rate=5, time_period=60)


def is_url(text) -> bool:
    """Check if the text is a valid URL"""
    url_pattern = re.compile(
        r"^https?://"  # http:// or https://
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain...
        r"localhost|"  # localhost...
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
        r"(?::\d+)?"  # optional port
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE,
    )
    return url_pattern.match(text) is not None


def is_wallhaven(text) -> bool:
    "Only Accept Wallhaven URLs"
    if "https://wallhaven.cc/w/" in text:
        return True
    return False


def monitor_clipboard(conditions: List[FunctionType] = [is_wallhaven]) -> None:
    """Monitor clipboard for URLs"""
    print("URL Clipboard Monitor Started!")
    print("Copy URLs in Browser and they will be captured here.")
    print("Current Active Conditions:")
    for condition in conditions:
        print(f"{condition.__doc__}")
    print("Press Ctrl+C to stop.\n")

    last_clipboard = ""
    captured_urls = []

    try:
        while True:
            # Get current clipboard content
            current_clipboard = pyperclip.paste()

            # Check if clipboard changed and contains a URL
            if current_clipboard != last_clipboard:
                if is_url(current_clipboard):
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    print(f"[{timestamp}] Captured: {current_clipboard}")
                    for condition in conditions:
                        if condition(current_clipboard):
                            captured_urls.append(
                                {"timestamp": timestamp, "url": current_clipboard}
                            )
                        else:
                            print(
                                f"[URL_Conditions] {current_clipboard} Does not match with {condition.__doc__} Condition!"
                            )

                last_clipboard = current_clipboard

            # Check every 0.5 seconds instead of constant capturing
            time.sleep(0.5)

    # End Capture Session with Ctl-C -> capture that moment
    except KeyboardInterrupt:
        print("\n\n=== Monitoring Stopped ===")
        print(f"\nTotal URLs captured: {len(captured_urls)}")

        if captured_urls:
            print("\n=== All Captured URLs ===")
            for i, item in enumerate(captured_urls, 1):
                print(f"{i}. [{item['timestamp']}] {item['url']}")

            # Optionally save to file
            save = input("\nSave to file? (y/n): ").lower()
            if save == "y":
                filename = (
                    f"captured_urls_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                )
                with open(filename, "w") as f:
                    for item in captured_urls:
                        f.write(f"[{item['timestamp']}] {item['url']}\n")
                print(f"URLs saved to {filename}")


def get_all_captured_url_files() -> List[str] | None:
    captured_url_files = glob.glob("captured_urls_*.txt")
    if captured_url_files:
        return captured_url_files
    else:
        return None


def concatenate_clipboard_files(
    captured_url_files: List[str] | None,
    wishlist_file: str = "wishlist.txt",
    failed_file: str = "fails.txt",
) -> None:
    """Gather all captured_url files and make a single whishlist.txt file and remove captured_urls_ files"""
    all_wallhaven_urls = set()
    if captured_url_files is not None:
        for captured_url in captured_url_files:
            with open(captured_url) as c:
                all_wallhaven_urls.update(c.readlines())
                os.remove(captured_url)

    if exists(failed_file):
        with open(failed_file) as f:
            all_wallhaven_urls.update(f.readlines())
            os.remove(failed_file)

    if exists(wishlist_file):
        with open(wishlist_file, "a") as w:
            w.writelines(all_wallhaven_urls)
    else:
        with open(wishlist_file, "w") as w:
            w.writelines(all_wallhaven_urls)

    return None


def retrieve_image_ids(
    wishlist_file: str = "wishlist.txt",
) -> List[str]:
    """read wishlist.txt file and extract image ids from url"""
    if not os.path.exists(wishlist_file):
        raise Exception("There is no wishlist.txt, means you didn't captured any link")

    with open(wishlist_file) as f:
        ids = [line.strip().split("/")[-1] for line in f.readlines() if line.strip()]
    return ids


async def get_single_img_src(
    asession: aiohttp.ClientSession,
    id: str,
    api_address: str = API_ADDRESS,
    api_limit: AsyncLimiter = API_CALL_LIMIT,
) -> Tuple[str, int | BaseException, str]:
    print(f"Working on {id}")
    async with api_limit:
        try:
            async with asession.get(api_address + id) as response:
                status = response.status
                if status == 200:
                    data = await response.json()
                    src = data["data"]["path"]
                    print(f"[API] ✓ Got URL for {id}")
                    return (id, status, src)
                elif status == 429:
                    print(f"[API] ✗ {id} - Rate limited (429)")
                    return (id, status, "")
                else:
                    print(f"[API] ✗ {id} - Status {status}")
                    return (id, status, "")
        except Exception as e:
            print(f"[API] ✗ {id} - Error: {e}")
            return (id, e, "")


async def get_img_srcs_batched(
    ids: List[str],
    batch_size: int = 45,
    api_address: str = API_ADDRESS,
    api_limit: AsyncLimiter = API_CALL_LIMIT,
    file_name: str = "src_wishlist.csv",
) -> str:
    all_urls = []
    batches = [ids[i : i + batch_size] for i in range(0, len(ids), 45)]

    time_out = aiohttp.ClientTimeout(total=60)

    async with aiohttp.ClientSession(timeout=time_out) as asession:
        for batch_num, batch in enumerate(batches, 1):
            print(f"\n[Batch {batch_num}/{len(batches)}] Processing {len(batch)} IDs")

            coroutines = [
                get_single_img_src(asession, id, api_address, api_limit) for id in batch
            ]

            urls = await asyncio.gather(*coroutines, return_exceptions=True)

            all_urls.extend(urls)

            if batch_num < len(batches):
                print("\n[WAIT] Waiting 60s for rate limit reset...")
                for remaining in range(60, 0, -1):
                    print(f"\r[WAIT] {remaining}s remaining...", end="", flush=True)
                    await asyncio.sleep(1)
                print("\r[READY] Starting next batch" + " " * 30)

    if exists(file_name):
        with open(file_name, "a") as f:
            print(f"[INFO] Appending to {file_name}")
            writer = csv.writer(f)
            writer.writerows(all_urls)
    else:
        with open(file_name, "w") as f:
            print(f"[INFO] Writing {file_name}")
            writer = csv.writer(f)
            writer.writerow(["id", "status", "url"])  # Header
            writer.writerows(all_urls)

    return file_name


async def download_single_img(
    client: aiohttp.ClientSession, url: str, id: str, semaphore: asyncio.Semaphore
) -> Tuple[str, str, str]:
    download_status = "0"
    time_out = aiohttp.ClientTimeout(total=60)
    async with semaphore:
        try:
            print(f"[DL] Downloading {id}")
            async with client.get(
                url,
                timeout=time_out,
                allow_redirects=True,
            ) as response:
                if response.status != 200:
                    print(f"[DL] ✗ Saved {id} - Status {response.status}")
                    return id, url, str(response.status)

                file_name = url.split("/")[-1]
                print(file_name)
                download_path = DOWNLOAD_DIR / file_name

                async with aiofiles.open(download_path, "wb") as f:
                    async for chunk in response.content.iter_chunked(8192):
                        await f.write(chunk)

            download_status = "1"
            print(f"[DL] ✓ Saved {id} to {download_path}")

        except asyncio.TimeoutError:
            print(f"[DL] ✗ {id} - Timeout")
            download_status = "Timeout"
        except aiohttp.ClientError as e:
            print(f"[DL] ✗ {id} - Network error: {e}")
            download_status = str(e)
        except OSError as e:
            print(f"[DL] ✗ {id} - File error: {e}")
            download_status = str(e)
        except Exception as e:
            print(f"[DL] ✗ {id} - Unexpected error: {e}")
            download_status = str(e)

        return id, url, download_status


async def download_imgs(
    src_file_name: str = "src_wishlist.csv",
    download_status_file: str = "status_wishlist.csv",
) -> str:
    with open(src_file_name) as f:
        reader = csv.DictReader(f, delimiter=",")
        ids_stats_urls = list(reader)

    dl_semaphore = asyncio.Semaphore(DOWNLOAD_LIMIT)
    async with aiohttp.ClientSession() as client:
        print("[INFO] Coroutines Initialized")
        coroutines = [
            download_single_img(
                client=client,
                url=id_stat_url["url"],
                id=id_stat_url["id"],
                semaphore=dl_semaphore,
            )
            for id_stat_url in ids_stats_urls
            if id_stat_url["status"] == "200"
        ]
        print("[INFO] Fuck it! Downloading!")
        results = await asyncio.gather(*coroutines, return_exceptions=False)

        if exists(download_status_file):
            print(f"[INFO] Appending to {src_file_name}")
            with open(src_file_name, "a") as f:
                writer = csv.writer(f)
                writer.writerows(results)
        else:
            print(f"[INFO] Writing {src_file_name}")
            with open(download_status_file, "w") as f:
                writer = csv.writer(f)
                writer.writerow(["id", "url", "download_status"])
                writer.writerows(results)

    return download_status_file


def clean_wishlist(
    orig_file: str = "wishlist.txt",
    download_stat_file: str = "status_wishlist.csv",
    src_file_name: str = "src_wishlist.csv",
    failed_file: str = "fails.txt",
    orig_file_remove: bool = True,
    download_stat_file_remove: bool = True,
    src_file_name_remove: bool = True,
):
    failure_ids = []
    failed_rows = []
    failure_download = []
    print("[CLEANING] Initiated!")
    print(f"[CHECKING] {download_stat_file}")
    if exists(download_stat_file):
        print("[CLEANING] Capturing Failores dowload_stat file")
        with open(download_stat_file) as d:
            reader = csv.DictReader(d)
            for row in reader:
                if row["download_status"] != "1":
                    print(f"[Failures] this {row['url']} with {row['download_status']}")
                    failure_ids.append(row)
                    failure_download.append(row)
        if download_stat_file_remove:
            os.remove(download_stat_file)
            print("[REMOVED] dowload_stat removed")

    print(f"[CHECKING] {src_file_name}")
    if exists(src_file_name):
        print("[CLEANING] Capturing Failores src_wishlist file")
        with open(src_file_name) as s:
            reader = csv.DictReader(s)
            for row in reader:
                if row["status"] != "200":
                    failure_ids.append(row)
                    print(f"[FAILURES] this {row['url']} with {'status'}")
        if src_file_name_remove:
            os.remove(src_file_name)
            print("[REMOVED] src_wishlist removed")

    failure_ids = [i["id"] for i in failure_ids]

    print(f"[CHECKING] {orig_file}")
    if exists(orig_file):
        with open(orig_file) as o:
            for row in o.readlines():
                id = row.strip().split(" ")[-1].split("/")[-1]
                if id in failure_ids:
                    print(f"[CAPTURED] Failure with {id}")
                    failed_rows.append(row)
        if orig_file_remove:
            os.remove(orig_file)
            print("[REMOVED] wishlist removed")

    if failed_rows:
        if exists(failed_file):
            with open(failed_file, "a") as f:
                f.writelines(failed_rows)
        else:
            with open(failed_file, "w") as f:
                f.writelines(failed_rows)


if __name__ == "__main__":
    print("[INFO] Creating/Created Wallhaven directory within script folder")
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    print("[INFO] Capturing Clipboard, Ctrl-C to exit")
    monitor_clipboard()

    print("[INFO] Finding all captured_url_files")
    captured_url_files = get_all_captured_url_files()

    print("[INFO] Creating wishlist.txt by concatenate all clipboard_files")
    wishlist_file = concatenate_clipboard_files(captured_url_files)

    print("[INFO] Reading image IDs from wishlist.txt")
    ids = retrieve_image_ids()
    print(f"[INFO] Found {len(ids)} image IDs\n")

    print("[INFO] Fetching image URLs from API (45 requests per 60 seconds)")
    urls = asyncio.run(get_img_srcs_batched(ids))

    print("[INFO] Downloading image URLs from API (45 requests per 60 seconds)")
    downloading = asyncio.run(download_imgs())

    print("[INFO] Downloading image URLs from API (45 requests per 60 seconds)")
    clean_wishlist()
