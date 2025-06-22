import requests
import os
import argparse
import json

WIKIMEDIA_API_URL = "https://commons.wikimedia.org/w/api.php"
DEFAULT_DOWNLOAD_TIMEOUT = 15  # seconds, slightly longer for potentially larger files

def download_file(url, folder_name, file_name, timeout=DEFAULT_DOWNLOAD_TIMEOUT):
    """Downloads a file from a URL into a specified folder with a timeout."""
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)

    headers = {
        'User-Agent': 'MediaDownloaderTool/1.0 (https://github.com/user/repo; user@example.com) Python-requests/X.Y.Z'
        # It's good practice to set a specific User-Agent for Wikimedia APIs
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

def search_wikimedia(query, limit=5, output_dir="wikimedia_media", media_type="all", timeout=DEFAULT_DOWNLOAD_TIMEOUT):
    """
    Searches Wikimedia Commons for media based on a query and downloads them.
    Supports media types: 'image', 'video', 'audio', 'all'.
    """
    # Determine generator and file type filters based on media_type
    # Wikimedia API uses `generator=search` (gsrsearch) for general search
    # and `prop=imageinfo&iiprop=url|mediatype|size` to get file details.
    # We can also use `filetype` parameter with `list=search` (srsearch)
    # but `generator=search` is often more flexible for keywords.

    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": 6,  # File namespace
        "gsrlimit": limit * 3 if media_type != "all" else limit,  # Request more to filter client-side, unless 'all'
        "prop": "imageinfo", # Using imageinfo is primary
        "iiprop": "url|mediatype|size|extmetadata",
        "iilimit": 1,
        "utf8": 1,
    }
    # Refined thinking: Category based filtering for video type is complex with general search.
    # It's better to search for the keyword and then check the mediatype of the results.
    # Adding a specific category like "Category:Videos" to gsrsearch can be done with "incategory:Videos"
    # Example: "gsrsearch": f"{query} incategory:Videos",
    # But this restricts search to items explicitly in that category.
    # For now, we will rely on post-search filtering by mediatype.

    # The list_wikimedia_media function now handles the API call and initial parsing.
    # search_wikimedia will call list_wikimedia_media and then download.
    # It needs to accept api_timeout for list_wikimedia_media and download_timeout for download_file.

    # Note: The original search_wikimedia had its own API call logic.
    # This will now be replaced by calling list_wikimedia_media.

    # Default api_timeout if not specified for backward compatibility or direct calls to search_wikimedia
    # However, the plan is to make all search_* functions take explicit api_timeout and download_timeout.
    # The `timeout` param in the original signature was ambiguous.
    # Let's rename `timeout` to `api_timeout_param` and add `download_timeout_param`.
    # For this diff, I'll modify the existing `search_wikimedia` signature and logic.

    # This function is being refactored. Original params: (query, limit=5, output_dir="wikimedia_media", media_type="all", timeout=DEFAULT_DOWNLOAD_TIMEOUT)
    # New params: (query, limit=5, output_dir="wikimedia_media", media_type="all", api_timeout=DEFAULT_DOWNLOAD_TIMEOUT, download_timeout=DEFAULT_DOWNLOAD_TIMEOUT)
    # The `timeout` parameter from the old signature is now `api_timeout` for the listing part.
    # `download_timeout` is a new parameter for the actual file downloads.

    # The 5th argument passed to search_wikimedia is 'timeout', which is intended for the API call.
    listed_items_data = list_wikimedia_media(query, limit, media_type, timeout)
    listed_items = listed_items_data.get("items", [])

    if listed_items_data.get("error"):
        print(listed_items_data["error"])
    elif not listed_items and listed_items_data.get("status_message"):
        print(listed_items_data["status_message"])
    elif not listed_items and not listed_items_data.get("error"):
         print(f"Wikimedia: No items found or extracted for query '{query}'.")

    if not listed_items:
        return []

    downloaded_files_list = []
    # list_wikimedia_media already applies media_type filtering and its own 'list_limit'
    # The 'limit' here is the number of files to actually download from that filtered list.
    for i, item_to_dl in enumerate(listed_items):
        if i >= limit: # Respect the download limit passed to search_wikimedia
            break

        # Note: item_to_dl already contains 'type', 'url', 'filename' from list_wikimedia_media
        print(f"Attempting to download Wikimedia item: {item_to_dl['title']} (Type: {item_to_dl['type']}) from {item_to_dl['url']}")
        # Pass the specific download_timeout to the download_file utility
        download_path = download_file(item_to_dl['url'], output_dir, item_to_dl['filename'], timeout=DEFAULT_DOWNLOAD_TIMEOUT)
        if download_path:
            downloaded_files_list.append(download_path)

    if not downloaded_files_list and not listed_items_data.get("error") and not (not listed_items and listed_items_data.get("status_message")):
        # This message is if items were listed but none downloaded successfully, and no prior error/status message was more specific
        print(f"No files of type '{media_type}' successfully downloaded for query '{query}' from Wikimedia (downloads may have failed).")

    return downloaded_files_list


# Renamed 'timeout' to 'api_timeout' for clarity
def list_wikimedia_media(query, list_limit=25, media_type="all", api_timeout=DEFAULT_DOWNLOAD_TIMEOUT):
    """
    Searches Wikimedia Commons for media and returns a dictionary
    with 'items', 'error', and 'status_message'.
    """
    params = {
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": query, "gsrnamespace": 6,
        # Fetch more for listing to allow client-side filtering up to list_limit effectively
        "gsrlimit": list_limit * 3 if media_type != "all" else list_limit,
        "prop": "imageinfo", "iiprop": "url|mediatype|size|extmetadata",
        "iilimit": 1, "utf8": 1,
    }

    try:
        response = requests.get(WIKIMEDIA_API_URL, params=params, timeout=api_timeout) # Use api_timeout
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.Timeout:
        #print(f"Timeout during Wikimedia API (list) request for query: {query}")
        return {"items": [], "error": f"Wikimedia: API timeout for '{query[:50]}'", "status_message": None}
    except requests.exceptions.RequestException as e:
        # print(f"API request error for Wikimedia (list) query '{query}': {e}")
        return {"items": [], "error": f"Wikimedia: API request error for '{query[:50]}': {e}", "status_message": None}
    except json.JSONDecodeError:
        # print(f"Error decoding JSON from Wikimedia (list): {response.text if 'response' in locals() else 'No response text'}")
        return {"items": [], "error": f"Wikimedia: Error decoding API response for '{query[:50]}'", "status_message": None}
    except Exception as e: # Catch other potential errors
        return {"items": [], "error": f"Wikimedia: Unexpected error for '{query[:50]}': {e}", "status_message": None}


    if "error" in data:
        # print(f"Wikimedia API Error (list): {data['error'].get('info', 'Unknown error')}")
        return {"items": [], "error": f"Wikimedia API Error: {data['error'].get('info', 'Unknown error')}", "status_message": None}
    if not data.get("query", {}).get("pages"):
        # print(f"No results found for '{query}' on Wikimedia Commons (list).")
        return {"items": [], "error": None, "status_message": f"Wikimedia: No results found for '{query[:50]}'"}

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
        original_filename_title = page_data.get("title", f"File_{page_id}")

        filename_part = original_filename_title
        if filename_part.startswith("File:"):
            filename_part = filename_part[5:]

        file_extension = os.path.splitext(filename_part)[1].lower()
        if not file_extension and api_media_type == "drawing" and "svg" in img_info.get("mime", ""):
            file_extension = ".svg" # Try to infer for SVG if not in filename
        elif not file_extension: # if still no extension, try to get from URL (less reliable)
            file_extension = os.path.splitext(file_url.split('/')[-1])[1].lower()


        if not file_url:
            continue

        item_actual_media_type = "unknown"
        if api_media_type in ["bitmap", "drawing"] or file_extension in [".jpg", ".jpeg", ".png", ".gif", ".svg", ".tiff", ".webp"]:
            item_actual_media_type = "image"
            if file_extension == ".gif": item_actual_media_type = "gif" # more specific
        elif api_media_type == "video" or file_extension in [".ogv", ".webm", ".mp4", ".mov", ".mpeg", ".mpg"]:
            item_actual_media_type = "video"
        elif api_media_type == "audio" or file_extension in [".ogg", ".oga", ".wav", ".mp3", ".flac", ".opus", ".mid"]:
            item_actual_media_type = "audio"

        # Filter by requested media_type
        if media_type != "all":
            if media_type == "image" and item_actual_media_type not in ["image", "gif"]: continue
            elif media_type == "gif" and item_actual_media_type != "gif": continue
            elif media_type == "video" and item_actual_media_type != "video": continue
            elif media_type == "audio" and item_actual_media_type != "audio": continue
            # Note: "sticker" type is not applicable to wikimedia in this context

        clean_original_filename = "".join(c if c.isalnum() else "_" for c in os.path.splitext(filename_part)[0])[:50]
        final_filename = f"wikimedia_{smart_query_name_base}_{clean_original_filename}{file_extension}"
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
            "platform": "wikimedia"
        })

    return {"items": found_items, "error": None, "status_message": None if found_items else f"Wikimedia: No items extracted for '{query[:50]}'"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download media from Wikimedia Commons.")
    parser.add_argument("query", type=str, help="Search query for Wikimedia Commons.")
    parser.add_argument("--limit", type=int, default=5, help="Maximum number of items to download.")
    parser.add_argument("--output_dir", type=str, default="wikimedia_media", help="Directory to save downloaded media.")
    parser.add_argument(
        "--media_type", type=str, default="all",
        choices=["image", "video", "audio", "all", "gif"], # Added gif for consistency, maps to image
        help="Type of media to download."
    )
    # Renamed --timeout to --api_timeout and added --download_timeout
    parser.add_argument("--api_timeout", type=int, default=DEFAULT_DOWNLOAD_TIMEOUT, help="API call timeout in seconds. (Note: Wikimedia uses one timeout for both in search_wikimedia)") # DEFAULT_DOWNLOAD_TIMEOUT was the old default here
    parser.add_argument("--download_timeout", type=int, default=DEFAULT_DOWNLOAD_TIMEOUT, help="File download timeout in seconds.")


    args = parser.parse_args()

    # Test listing
    print(f"\n--- Listing Wikimedia for '{args.query}' (type: {args.media_type}, limit: {args.limit}) ---")
    # list_wikimedia_media uses 'timeout' for its API call.
    list_result = list_wikimedia_media(args.query, args.limit, args.media_type, args.api_timeout)
    if list_result.get("error"):
        print(f"Error listing: {list_result['error']}")
    elif not list_result.get("items") and list_result.get("status_message"):
        print(f"Status listing: {list_result['status_message']}")
    elif list_result.get("items"):
        print(f"Found {len(list_result['items'])} items for listing:")
        for item in list_result['items']:
            print(f"  - Title: {item['title']} ({item['type']}), URL: {item['url']}")
    else:
        print("No items found or an unknown issue occurred during listing.")

    # Test downloading
    print(f"\n--- Downloading from Wikimedia for '{args.query}' (type: {args.media_type}, limit: {args.limit}) ---")
    # search_wikimedia needs to be refactored to accept api_timeout and download_timeout and handle new dict
    # For now, its internal call to list_wikimedia_media will use the old single 'timeout' param.
    # Let's refactor search_wikimedia.

    def search_wikimedia_refactored(query, limit=5, output_dir="wikimedia_media", media_type="all",
                                   api_timeout_param=DEFAULT_DOWNLOAD_TIMEOUT, download_timeout_param=DEFAULT_DOWNLOAD_TIMEOUT):
        # list_wikimedia_media expects a single 'timeout' for its API call. We'll use api_timeout_param for that.
        listed_items_data = list_wikimedia_media(query, limit, media_type, api_timeout_param)
        listed_items = listed_items_data.get("items", [])

        if listed_items_data.get("error"):
            print(listed_items_data["error"])
        elif not listed_items and listed_items_data.get("status_message"):
            print(listed_items_data["status_message"])
        elif not listed_items and not listed_items_data.get("error"):
            print(f"Wikimedia: No items found or extracted for query '{query}'.")

        if not listed_items:
            return []

        downloaded_paths_list = []
        for i, item_to_dl in enumerate(listed_items):
            if i >= limit: break
            print(f"Downloading Wikimedia item: {item_to_dl['title']} from {item_to_dl['url']}")
            dl_path = download_file(item_to_dl['url'], output_dir, item_to_dl['filename'], timeout=download_timeout_param)
            if dl_path:
                downloaded_paths_list.append(dl_path)
        return downloaded_paths_list

    downloaded_paths = search_wikimedia_refactored(
        args.query,
        args.limit,
        args.output_dir,
        args.media_type,
        api_timeout_param=args.api_timeout,
        download_timeout_param=args.download_timeout
    )

    if downloaded_paths:
        print(f"Wikimedia: Successfully downloaded {len(downloaded_paths)} files.")
    # else: search_wikimedia_refactored prints its own status/errors.

    print("\nWikimedia CLI test process complete.")
