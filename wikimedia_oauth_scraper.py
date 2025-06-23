import requests
import os
import argparse
import json

WIKIMEDIA_API_URL = "https://commons.wikimedia.org/w/api.php" # Same API URL
DEFAULT_DOWNLOAD_TIMEOUT = 15
DEFAULT_API_TIMEOUT = 10 # Default for API calls

# Provided OAuth 2.0 Access Token
WIKIMEDIA_ACCESS_TOKEN = "YOUR_ACCESS_TOKEN_HERE"

def _get_auth_headers():
    """Returns headers for authenticated Wikimedia API requests."""
    if not WIKIMEDIA_ACCESS_TOKEN or WIKIMEDIA_ACCESS_TOKEN == "YOUR_ACCESS_TOKEN_HERE": # Basic check
        # This module should ideally not function without a token.
        # For robustness, one might raise an error or return None to signal misconfiguration.
        print("Warning: Wikimedia OAuth Access Token is not set or is a placeholder.")
        return {'User-Agent': 'MediaDownloaderTool/1.0 (OAuth)'} # Fallback to non-authed User-Agent if token is bad
    return {
        'User-Agent': 'MediaDownloaderTool/1.0 (OAuth)',
        'Authorization': f'Bearer {WIKIMEDIA_ACCESS_TOKEN}'
    }

# Note: download_file can be identical to the one in wikimedia_scraper.py
# as file downloads themselves don't typically require auth once the URL is obtained.
# If they did, this would need to use _get_auth_headers too.
# For now, we assume public URLs are returned by the API.
def download_file(url, folder_name, file_name, timeout=DEFAULT_DOWNLOAD_TIMEOUT):
    """Downloads a file from a URL into a specified folder with a timeout."""
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)

    # Use a generic User-Agent for downloads, auth is for API metadata calls
    headers = {
        'User-Agent': 'MediaDownloaderTool/1.0 Python-requests/X.Y.Z'
    }
    try:
        response = requests.get(url, stream=True, headers=headers, timeout=timeout)
        response.raise_for_status()
        file_path = os.path.join(folder_name, file_name)
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Downloaded {file_name} to {folder_name} (OAuth Scraper)")
        return file_path
    except requests.exceptions.Timeout:
        print(f"Timeout downloading {url} (OAuth Scraper) to {file_name}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error downloading {url} (OAuth Scraper) to {file_name}: {e}")
        return None

def list_wikimedia_oauth_media(query, list_limit=25, media_type="all", api_timeout=DEFAULT_API_TIMEOUT):
    """
    Searches Wikimedia Commons using OAuth and returns a dictionary with 'items', 'error', 'status_message'.
    """
    params = {
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": query, "gsrnamespace": 6,
        "gsrlimit": list_limit * 3 if media_type != "all" else list_limit,
        "prop": "imageinfo", "iiprop": "url|mediatype|size|extmetadata",
        "iilimit": 1, "utf8": 1,
    }

    auth_headers = _get_auth_headers()

    try:
        response = requests.get(WIKIMEDIA_API_URL, params=params, headers=auth_headers, timeout=api_timeout)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.Timeout:
        return {"items": [], "error": f"Wikimedia OAuth: API timeout for '{query[:50]}'", "status_message": None}
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401: # Unauthorized
             return {"items": [], "error": f"Wikimedia OAuth: Authentication error (401). Token might be invalid or expired for '{query[:50]}'. Response: {e.response.text[:200]}", "status_message": None}
        return {"items": [], "error": f"Wikimedia OAuth: API HTTP error for '{query[:50]}': {e}. Response: {e.response.text[:200]}", "status_message": None}
    except requests.exceptions.RequestException as e:
        return {"items": [], "error": f"Wikimedia OAuth: API request error for '{query[:50]}': {e}", "status_message": None}
    except json.JSONDecodeError:
        return {"items": [], "error": f"Wikimedia OAuth: Error decoding API response for '{query[:50]}'", "status_message": None}
    except Exception as e:
        return {"items": [], "error": f"Wikimedia OAuth: Unexpected error for '{query[:50]}': {e}", "status_message": None}

    if "error" in data:
        return {"items": [], "error": f"Wikimedia OAuth API Error: {data['error'].get('info', 'Unknown error')}", "status_message": None}
    if not data.get("query", {}).get("pages"):
        return {"items": [], "error": None, "status_message": f"Wikimedia OAuth: No results found for '{query[:50]}'"}

    found_items = []
    query_words = query.split()
    smart_query_name_base = "_".join(query_words[:2]).lower()
    smart_query_name_base = "".join(c if c.isalnum() else "_" for c in smart_query_name_base).strip('_')

    for page_id, page_data in data["query"]["pages"].items():
        if "imageinfo" not in page_data or not page_data["imageinfo"]:
            continue

        img_info = page_data["imageinfo"][0]
        api_media_type = img_info.get("mediatype", "UNKNOWN").lower()
        file_url = img_info.get("url")
        size_bytes = img_info.get("size") # Get the size in bytes
        original_filename_title = page_data.get("title", f"File_{page_id}")

        filename_part = original_filename_title
        if filename_part.startswith("File:"):
            filename_part = filename_part[5:]

        file_extension = os.path.splitext(filename_part)[1].lower()
        if not file_extension and api_media_type == "drawing" and "svg" in img_info.get("mime", ""):
            file_extension = ".svg"
        elif not file_extension:
            file_extension = os.path.splitext(file_url.split('/')[-1])[1].lower() if file_url else ""


        if not file_url:
            continue

        item_actual_media_type = "unknown"
        if api_media_type in ["bitmap", "drawing"] or file_extension in [".jpg", ".jpeg", ".png", ".gif", ".svg", ".tiff", ".webp"]:
            item_actual_media_type = "image"
            if file_extension == ".gif": item_actual_media_type = "gif"
        elif api_media_type == "video" or file_extension in [".ogv", ".webm", ".mp4", ".mov", ".mpeg", ".mpg"]:
            item_actual_media_type = "video"
        elif api_media_type == "audio" or file_extension in [".ogg", ".oga", ".wav", ".mp3", ".flac", ".opus", ".mid"]:
            item_actual_media_type = "audio"

        if media_type != "all":
            if media_type == "image" and item_actual_media_type not in ["image", "gif"]: continue
            elif media_type == "gif" and item_actual_media_type != "gif": continue
            elif media_type == "video" and item_actual_media_type != "video": continue
            elif media_type == "audio" and item_actual_media_type != "audio": continue

        clean_original_filename = "".join(c if c.isalnum() else "_" for c in os.path.splitext(filename_part)[0])[:50]
        final_filename = f"wikimedia_oauth_{smart_query_name_base}_{clean_original_filename}{file_extension}"
        final_filename = "_".join(filter(None, final_filename.split('_')))

        description = ""
        if img_info.get("extmetadata"):
            if img_info["extmetadata"].get("ObjectName", {}).get("value"):
                description = img_info["extmetadata"]["ObjectName"]["value"]
            elif img_info["extmetadata"].get("ImageDescription", {}).get("value"):
                description = img_info["extmetadata"]["ImageDescription"]["value"]
        title_for_display = description or original_filename_title

        found_items.append({
            "id": page_id,
            "title": title_for_display,
            "url": file_url,
            "type": item_actual_media_type,
            "filename": final_filename,
            "platform": "wikimedia_oauth", # Differentiate platform name
            "size_bytes": size_bytes # Add the size
        })
    return {"items": found_items, "error": None, "status_message": None if found_items else f"Wikimedia OAuth: No items extracted for '{query[:50]}'"}


def search_wikimedia_oauth_media(query, limit=5, output_dir="wikimedia_oauth_media", media_type="all",
                                 api_timeout=DEFAULT_API_TIMEOUT, download_timeout=DEFAULT_DOWNLOAD_TIMEOUT):
    """
    Searches Wikimedia Commons (OAuth) and downloads them.
    """
    listed_items_data = list_wikimedia_oauth_media(query, list_limit=limit, media_type=media_type, api_timeout=api_timeout)
    listed_items = []

    if isinstance(listed_items_data, dict):
        listed_items = listed_items_data.get("items", [])
        if listed_items_data.get("error"):
            print(listed_items_data["error"])
        elif not listed_items and listed_items_data.get("status_message"):
            print(listed_items_data["status_message"])
        elif not listed_items and not listed_items_data.get("error"):
             print(f"Wikimedia OAuth: No items found or extracted for query '{query}'.")
    else: # Should not happen if list_wikimedia_oauth_media is consistent
        print(f"Wikimedia OAuth: Unexpected data from list function for '{query}'.")

    if not listed_items:
        return []

    downloaded_files_list = []
    for i, item_to_dl in enumerate(listed_items):
        if i >= limit:
            break
        print(f"Attempting to download Wikimedia OAuth item: {item_to_dl['title']} (Type: {item_to_dl['type']}) from {item_to_dl['url']}")
        download_path = download_file(item_to_dl['url'], output_dir, item_to_dl['filename'], timeout=download_timeout)
        if download_path:
            downloaded_files_list.append(download_path)
    return downloaded_files_list


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download media from Wikimedia Commons using OAuth.")
    parser.add_argument("query", type=str, help="Search query.")
    parser.add_argument("--limit", type=int, default=5, help="Max items to download.")
    parser.add_argument("--output_dir", type=str, default="wikimedia_oauth_media", help="Output directory.")
    parser.add_argument("--media_type", type=str, default="all", choices=["image", "video", "audio", "all", "gif"], help="Media type.")
    parser.add_argument("--api_timeout", type=int, default=DEFAULT_API_TIMEOUT, help="API call timeout.")
    parser.add_argument("--download_timeout", type=int, default=DEFAULT_DOWNLOAD_TIMEOUT, help="File download timeout.")
    args = parser.parse_args()

    print(f"\n--- Listing Wikimedia OAuth for '{args.query}' (type: {args.media_type}, limit: {args.limit}) ---")
    list_result = list_wikimedia_oauth_media(args.query, args.limit, args.media_type, args.api_timeout)

    if list_result.get("error"):
        print(f"Error listing: {list_result['error']}")
    elif not list_result.get("items") and list_result.get("status_message"):
        print(f"Status listing: {list_result['status_message']}")
    elif list_result.get("items"):
        print(f"Found {len(list_result['items'])} items for listing:")
        for item in list_result['items']:
            print(f"  - Title: {item['title']} ({item['type']}), URL: {item['url']}")
    else:
        print("No items found or an unknown issue occurred during listing (OAuth).")

    print(f"\n--- Downloading from Wikimedia OAuth for '{args.query}' (type: {args.media_type}, limit: {args.limit}) ---")
    downloaded_paths = search_wikimedia_oauth_media(
        args.query, args.limit, args.output_dir, args.media_type, args.api_timeout, args.download_timeout
    )
    if downloaded_paths:
        print(f"Wikimedia OAuth: Successfully downloaded {len(downloaded_paths)} files.")
    print("\nWikimedia OAuth CLI test process complete.")
