import requests
from bs4 import BeautifulSoup
import os
import argparse
import json # Still useful for structured data, though not for API responses
import re

# Frinkiac base URL.
FRINKIAC_BASE_URL = "https://frinkiac.com"

DEFAULT_DOWNLOAD_TIMEOUT = 10  # seconds
DEFAULT_REQUEST_TIMEOUT = 10 # seconds for fetching HTML

def download_file(url, folder_name, file_name, timeout=DEFAULT_DOWNLOAD_TIMEOUT):
    """Downloads a file from a URL into a specified folder with a timeout."""
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
    headers = {'User-Agent': 'MediaDownloaderTool/1.0 Python-requests/X.Y.Z'}
    try:
        response = requests.get(url, stream=True, headers=headers, timeout=timeout)
        response.raise_for_status()
        file_path = os.path.join(folder_name, file_name)
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Downloaded {file_name} to {folder_name}")
        return file_path
    except requests.exceptions.Timeout:
        print(f"Timeout downloading {url} to {file_name}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error downloading {url} to {file_name}: {e}")
        return None

def list_frinkiac_media(query_quote, list_limit=25, request_timeout=DEFAULT_REQUEST_TIMEOUT, **kwargs):
    """
    Searches Frinkiac for screencaps based on a quote by scraping the website
    and returns a list of item details.
    """
    search_url = f"{FRINKIAC_BASE_URL}/?q={requests.utils.quote(query_quote)}"
    headers = {'User-Agent': 'MediaDownloaderTool/1.0 Python-requests/X.Y.Z'}

    try:
        response = requests.get(search_url, headers=headers, timeout=request_timeout)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
    except requests.exceptions.Timeout:
        # print(f"Timeout during Frinkiac page request for quote: {query_quote}")
        return {"items": [], "error": f"Frinkiac: Timeout fetching page for '{query_quote[:50]}'", "status_message": None}
    except requests.exceptions.RequestException as e:
        # print(f"Page request error for Frinkiac query '{query_quote}': {e}")
        return {"items": [], "error": f"Frinkiac: Network error for '{query_quote[:50]}': {e}", "status_message": None}
    except Exception as e: # Catch other potential errors like BS4 issues
        # print(f"Error processing Frinkiac page for '{query_quote}': {e}")
        return {"items": [], "error": f"Frinkiac: Error processing page for '{query_quote[:50]}': {e}", "status_message": None}

    found_items = []
    # Frinkiac search results are typically in elements with class "frame-item" or similar structure.
    # This needs to be based on actual Frinkiac HTML structure.
    # Let's assume each result item is a div with class 'frame-panel'
    # Inside which an 'a' tag has href like '/caption/SXXEXX/timestamp'
    # and an 'img' tag has the image. Subtitles are nearby.

    # Based on inspecting frinkiac.com (Oct 2023 view):
    # Results are in <div class="col-sm-4 frame-panel">
    #   <a href="/caption/S10E04/197947">
    #     <img class="img-responsive frame-image" src="/img/S10E04/197947.jpg">
    #   </a>
    #   <div class="caption-panel">
    #     <div class="subtitle-text">SUBTITLE LINE 1</div>
    #     <div class="subtitle-text">SUBTITLE LINE 2</div> ...
    #   </div>
    # </div>

    query_words = query_quote.split()
    smart_query_name_base = "_".join(query_words[:2]).lower()
    smart_query_name_base = "".join(c if c.isalnum() else "_" for c in smart_query_name_base).strip('_')

    frame_panels = soup.find_all('div', class_='frame-panel', limit=list_limit * 2) # Fetch more initially

    if not frame_panels:
        # print(f"No frame panels found for '{query_quote}' on Frinkiac.")
        return {"items": [], "error": None, "status_message": f"Frinkiac: No matching frames found for '{query_quote[:50]}'"}

    for panel in frame_panels:
        if len(found_items) >= list_limit:
            break

        link_tag = panel.find('a', href=True)
        img_tag = panel.find('img', class_='frame-image', src=True)

        if not link_tag or not img_tag:
            continue

        href_match = re.search(r'/caption/(S\d+E\d+)/(\d+)', link_tag['href'])
        if not href_match:
            continue

        episode = href_match.group(1)
        timestamp = href_match.group(2)

        image_url_path = img_tag['src']
        if not image_url_path.startswith('http'):
            image_url = f"{FRINKIAC_BASE_URL}{image_url_path}"
        else:
            image_url = image_url_path # Should not happen for Frinkiac's relative URLs

        subtitles_divs = panel.select('.caption-panel .subtitle-text')
        subtitle_lines = [s.get_text(strip=True) for s in subtitles_divs]
        full_subtitle = " ".join(subtitle_lines) if subtitle_lines else query_quote # Fallback

        item_id = f"{episode}_{timestamp}"
        title = f"Frinkiac: {full_subtitle[:80]}"
        if len(full_subtitle) > 80: title += "..."

        file_extension = ".jpg" # Frinkiac images are jpg
        final_filename = f"frinkiac_{smart_query_name_base}_{item_id}{file_extension}"
        final_filename = "_".join(filter(None, final_filename.split('_')))

        found_items.append({
            "id": item_id,
            "title": title,
            "url": image_url,
            "type": "image",
            "filename": final_filename,
            "platform": "frinkiac",
            "episode": episode,
            "timestamp": timestamp,
            "subtitle": full_subtitle,
            "preview_image_url": image_url # For image, preview is the image itself
        })

    status_msg = None
    if not found_items and not soup.find_all('div', class_='frame-panel'): # Check if frame_panels was empty initially
        # This case is now handled by the earlier check on frame_panels, but as a safeguard:
        status_msg = f"Frinkiac: No frame panels found at all for '{query_quote[:50]}'."
    elif not found_items: # Found panels but couldn't extract items
        status_msg = f"Frinkiac: Found frame panels but could not extract valid items for '{query_quote[:50]}'."

    return {"items": found_items[:list_limit], "error": None, "status_message": status_msg}


def search_frinkiac_media(query_quote, limit=5, output_dir="frinkiac_media", request_timeout=DEFAULT_REQUEST_TIMEOUT, download_timeout=DEFAULT_DOWNLOAD_TIMEOUT, **kwargs):
    """
    Searches Frinkiac for screencaps by quote (scraping) and downloads them.
    """
    listed_items_data = list_frinkiac_media(query_quote, list_limit=limit, request_timeout=request_timeout)

    listed_items = listed_items_data.get("items", [])

    # CLI feedback for errors or status messages
    if listed_items_data.get("error"):
        print(listed_items_data["error"])
    # Only print status_message if there are no items AND no overriding error
    elif not listed_items and listed_items_data.get("status_message") and not listed_items_data.get("error"):
        print(listed_items_data["status_message"])
    elif not listed_items and not listed_items_data.get("error"): # Generic no items found, if no specific status message
        print(f"Frinkiac: No images found or extracted for quote '{query_quote}'.")

    if not listed_items:
        return [] # Stop if no items to download or error occurred

    downloaded_files = []
    for i, item in enumerate(listed_items): # listed_items is already limited by list_frinkiac_media
        if i >= limit:
            break
        print(f"Downloading Frinkiac image: {item['title']} from {item['url']}")
        download_path = download_file(item['url'], output_dir, item['filename'], timeout=download_timeout)
        if download_path:
            downloaded_files.append(download_path)

    return downloaded_files

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download screencaps from Frinkiac based on quotes (web scraping).")
    parser.add_argument("quote", type=str, help="Search quote for Frinkiac.")
    parser.add_argument("--limit", type=int, default=5, help="Maximum number of images to download.")
    parser.add_argument("--output_dir", type=str, default="frinkiac_media", help="Directory to save downloaded images.")
    parser.add_argument("--request_timeout", type=int, default=DEFAULT_REQUEST_TIMEOUT, help="Timeout for fetching HTML page in seconds.")
    parser.add_argument("--download_timeout", type=int, default=DEFAULT_DOWNLOAD_TIMEOUT, help="Timeout for file downloads in seconds.")

    args = parser.parse_args()

    print(f"Searching Frinkiac (scraping) for quote '{args.quote}' and downloading up to {args.limit} images to '{args.output_dir}'...")
    downloaded = search_frinkiac_media(
        args.quote,
        args.limit,
        args.output_dir,
        request_timeout=args.request_timeout,
        download_timeout=args.download_timeout
    )
    if downloaded:
        print(f"Frinkiac: Successfully downloaded {len(downloaded)} images via scraping.")
    else:
        print("Frinkiac: No images downloaded via scraping.")
    print("Frinkiac image download process complete.")
