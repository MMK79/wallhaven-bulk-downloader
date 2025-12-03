# Other solution
# from pandas.io.clipboard import clipboard_get
from types import FunctionType
from typing import List
import pyperclip
import time

# work with regax
import re
from datetime import datetime


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
    if "wallhaven" in text:
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


if __name__ == "__main__":
    monitor_clipboard()
