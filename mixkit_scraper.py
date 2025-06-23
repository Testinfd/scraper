import requests
from bs4 import BeautifulSoup
import os
import argparse
import json
import re # For extracting JSON from script tags

# Attempt to import the helper function. If this script is run standalone, this might fail.
try:
    from media_downloader_tool import get_remote_file_size
except ImportError:
    # Fallback for standalone execution or if media_downloader_tool is not in PYTHONPATH
    def get_remote_file_size(url, timeout=5):
        # print(f"Warning: Using fallback get_remote_file_size for {url}")
        try:
            response = requests.head(url, timeout=timeout, allow_redirects=True)
            response.raise_for_status()
            content_length = response.headers.get('Content-Length')
            return int(content_length) if content_length else None
        except Exception: # Broad exception for fallback
            return None

MIXKIT_BASE_URL = "https://mixkit.co"
# Search URL structure: https://mixkit.co/free-stock-video/search/?q=nature

DEFAULT_DOWNLOAD_TIMEOUT = 20  # seconds
DEFAULT_REQUEST_TIMEOUT = 15 # seconds

def download_file(url, folder_name, file_name, timeout=DEFAULT_DOWNLOAD_TIMEOUT):
    """Downloads a file from a URL into a specified folder with a timeout."""
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
    headers = {
        'User-Agent': 'MediaDownloaderTool/1.0 Python-requests/X.Y.Z',
        'Referer': MIXKIT_BASE_URL
    }
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

def list_mixkit_videos(query, list_limit=25, request_timeout=DEFAULT_REQUEST_TIMEOUT, **kwargs):
    """
    Searches Mixkit for videos by scraping the website and returns a list of item details.
    """
    search_url = f"{MIXKIT_BASE_URL}/free-stock-video/search/?q={requests.utils.quote(query)}"
    headers = {
        'User-Agent': 'MediaDownloaderTool/1.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)', # A common bot UA
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    }

    try:
        response = requests.get(search_url, headers=headers, timeout=request_timeout)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
    except requests.exceptions.Timeout:
        # print(f"Timeout during Mixkit page request for query: {query}")
        return {"items": [], "error": f"Mixkit: Timeout fetching page for '{query[:50]}'", "status_message": None}
    except requests.exceptions.RequestException as e:
        # print(f"Page request error for Mixkit query '{query}': {e}")
        return {"items": [], "error": f"Mixkit: Network error for '{query[:50]}': {e}", "status_message": None}
    except Exception as e: # Catch BeautifulSoup errors or others
        # print(f"Error processing Mixkit page for '{query}': {e}")
        return {"items": [], "error": f"Mixkit: Error processing page for '{query[:50]}': {e}", "status_message": None}

    found_items = []
    query_words = query.split()
    smart_query_name_base = "_".join(query_words[:2]).lower()
    smart_query_name_base = "".join(c if c.isalnum() else "_" for c in smart_query_name_base).strip('_')

    # Attempt 1: Look for embedded JSON data in <script type="application/ld+json"> or similar
    # This is often a good source if sites use it for SEO or structured data.
    # Mixkit (Oct 2023) uses a <script id="__NEXT_DATA__" type="application/json"> tag
    # which contains a lot of page data, including items for lists.

    next_data_script = soup.find('script', id='__NEXT_DATA__', type='application/json')
    if next_data_script:
        try:
            page_data = json.loads(next_data_script.string)
            # The exact path to items can be deeply nested and might change.
            # Example path: page_data['props']['pageProps']['initialItems']['data'] (if on a search results page)
            # or page_data['props']['pageProps']['items']['data']
            # or page_data['props']['pageProps']['tag']['items']['data'] (if on a tag page)
            # Need to find the right path. Let's try a few common ones or look for a list of items.

            items_list = None
            if 'props' in page_data and 'pageProps' in page_data['props']:
                page_props = page_data['props']['pageProps']
                if 'initialItems' in page_props and isinstance(page_props['initialItems'], dict) and 'data' in page_props['initialItems']:
                    items_list = page_props['initialItems']['data']
                elif 'items' in page_props and isinstance(page_props['items'], dict) and 'data' in page_props['items']:
                    items_list = page_props['items']['data']
                elif 'tag' in page_props and isinstance(page_props['tag'], dict) and 'items' in page_props['tag'] and 'data' in page_props['tag']['items']:
                     items_list = page_props['tag']['items']['data']
                # Add more potential paths if discovered

                # Sometimes items are directly in page_props if it's a specific item page
                # For search results, it's usually a list.

            if items_list and isinstance(items_list, list):
                for item_data in items_list:
                    if len(found_items) >= list_limit:
                        break
                    if item_data.get("type") != "video": # Ensure it's a video item
                        continue

                    item_id = item_data.get("id")
                    title = item_data.get("name", f"Mixkit Video {item_id}")

                    # Direct video URL is often in 'download_url' or a similar key like 'url_hd', 'url_sd'
                    video_url = item_data.get("download_url_video_hd", item_data.get("download_url_video_sd")) # Prefer HD
                    if not video_url: # Fallback
                        video_url = item_data.get("download_url")

                    if not video_url and 'metadata' in item_data and 'resolutions' in item_data['metadata']:
                        # metadata.resolutions might be like: {"1080p": "url1", "720p": "url2"}
                        resolutions = item_data['metadata']['resolutions']
                        if '1080p' in resolutions: video_url = resolutions['1080p']
                        elif '720p' in resolutions: video_url = resolutions['720p']
                        elif '480p' in resolutions: video_url = resolutions['480p']
                        elif resolutions: video_url = list(resolutions.values())[0] # take any if specific not found


                    if not video_url:
                        # print(f"No download_url for Mixkit item: {title}")
                        continue

                    file_extension = os.path.splitext(video_url.split('/')[-1].split('?')[0])[1] or ".mp4"
                    final_filename = f"mixkit_{smart_query_name_base}_{item_id}{file_extension}"
                    final_filename = "_".join(filter(None, final_filename.split('_')))

                    preview_image_url = item_data.get("thumbnail_url") # Often available
                    if not preview_image_url and item_data.get("poster_url"): # another common key
                        preview_image_url = item_data.get("poster_url")

                    size_bytes = item_data.get("size_bytes") # Check if size is directly in JSON
                    if size_bytes is None and 'metadata' in item_data and item_data['metadata'].get('size_bytes'):
                        size_bytes = item_data['metadata']['size_bytes']

                    if size_bytes is None: # Fallback to HEAD request if not in JSON
                        size_bytes = get_remote_file_size(video_url, timeout=request_timeout)

                    found_items.append({
                        "id": item_id,
                        "title": title,
                        "url": video_url,
                        "type": "video",
                        "filename": final_filename,
                        "platform": "mixkit",
                        "preview_image_url": preview_image_url,
                        "description": item_data.get("description_text", item_data.get("description", "")),
                        "size_bytes": size_bytes
                    })
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"Error parsing Mixkit JSON data from <script id='__NEXT_DATA__'>: {e}")
            # Fallback to HTML parsing if JSON fails or doesn't yield results
            found_items = [] # Clear items if JSON parsing failed partway

    # Attempt 2: Fallback to parsing visible HTML elements if __NEXT_DATA__ fails or yields no items
    # This is more brittle. Structure: <div class="item-grid-card"> ... <a href="item_page_url"> ... <img src="thumb_url"> ... <h3>title</h3>
    # The challenge here is that the direct MP4 download link is usually NOT on the search results cards.
    # This path would require a two-step scrape (search page -> item detail page).
    # Given the complexity and the user's preference for robustness vs. deep scraping,
    # if __NEXT_DATA__ fails, we might return empty or only surface-level info.
    # For now, if __NEXT_DATA__ provides results, we use them. If not, we return empty.
    # A full HTML scraping fallback for search results cards would typically only yield links to detail pages.

    if not found_items:
        #  print(f"Could not extract video data from Mixkit for '{query}' using embedded JSON. HTML structure might have changed or no items found.")
        # This specific print is probably too verbose if we have a status_message system.
        # The function will return a status_message if items_list was empty before loop.
        pass


    status_msg = None
    if not next_data_script:
        status_msg = f"Mixkit: Could not find __NEXT_DATA__ script tag for '{query[:50]}'. Site structure may have changed."
    elif not items_list: # If next_data_script was found, but items_list remained None
        status_msg = f"Mixkit: Found __NEXT_DATA__ but failed to locate items list within it for '{query[:50]}'."
    elif not found_items: # If items_list was processed but no valid items were extracted
        status_msg = f"Mixkit: No suitable video items extracted from __NEXT_DATA__ for '{query[:50]}'."

    return {"items": found_items[:list_limit], "error": None, "status_message": status_msg}


def search_mixkit_videos(query, limit=5, output_dir="mixkit_media", request_timeout=DEFAULT_REQUEST_TIMEOUT, download_timeout=DEFAULT_DOWNLOAD_TIMEOUT, **kwargs):
    """
    Searches Mixkit for videos (scraping) and downloads them.
    """
    listed_items_data = list_mixkit_videos(query, list_limit=limit, request_timeout=request_timeout)

    listed_items = listed_items_data.get("items", [])

    if listed_items_data.get("error"):
        print(listed_items_data["error"])
    elif not listed_items and listed_items_data.get("status_message"):
        print(listed_items_data["status_message"])
    elif not listed_items and not listed_items_data.get("error"):
        print(f"Mixkit: No videos found or extracted for query '{query}'.")

    if not listed_items:
        return []

    downloaded_files = []
    for i, item in enumerate(listed_items): # list is already limited
        if i >= limit:
            break
        print(f"Downloading Mixkit video: {item['title']} ({item['url']})")
        download_path = download_file(item['url'], output_dir, item['filename'], timeout=download_timeout)
        if download_path:
            downloaded_files.append(download_path)

    return downloaded_files


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download videos from Mixkit (web scraping).")
    parser.add_argument("query", type=str, help="Search query for Mixkit videos.")
    parser.add_argument("--limit", type=int, default=5, help="Maximum number of videos to download.")
    parser.add_argument("--output_dir", type=str, default="mixkit_media", help="Directory to save downloaded videos.")
    parser.add_argument("--request_timeout", type=int, default=DEFAULT_REQUEST_TIMEOUT, help="Timeout for fetching HTML page in seconds.")
    parser.add_argument("--download_timeout", type=int, default=DEFAULT_DOWNLOAD_TIMEOUT, help="Timeout for file downloads in seconds.")

    args = parser.parse_args()

    print(f"Searching Mixkit (scraping) for '{args.query}' videos and downloading up to {args.limit} items to '{args.output_dir}'...")
    downloaded = search_mixkit_videos(
        args.query,
        args.limit,
        args.output_dir,
        request_timeout=args.request_timeout,
        download_timeout=args.download_timeout
    )
    if downloaded:
        print(f"Mixkit: Successfully downloaded {len(downloaded)} videos via scraping.")
    else:
        print("Mixkit: No videos downloaded via scraping.")
    print("Mixkit video download process complete.")
