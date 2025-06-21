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

    # Media type filtering:
    # Wikimedia's `mediatype` can be 'BITMAP', 'DRAWING', 'AUDIO', 'VIDEO', 'MULTIMEDIA', 'OFFICE', 'TEXT', 'UNKNOWN'
    # We map our simplified media_type to these.
    # This filtering will happen client-side after fetching results, as direct API filtering by these types in gsrsearch is tricky.

    print(f"Searching Wikimedia Commons for '{query}' (type: {media_type})...")
    try:
        response = requests.get(WIKIMEDIA_API_URL, params=params, timeout=timeout)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.Timeout:
        print(f"Timeout during Wikimedia API request for query: {query}")
        return []
    except requests.exceptions.RequestException as e:
        print(f"API request error for Wikimedia query '{query}': {e}")
        return []
    except json.JSONDecodeError:
        print(f"Error decoding JSON from Wikimedia: {response.text if 'response' in locals() else 'No response text'}")
        return []

    if "error" in data:
        print(f"Wikimedia API Error: {data['error'].get('info', 'Unknown error')}")
        return []
    if not data.get("query", {}).get("pages"):
        print(f"No results found for '{query}' on Wikimedia Commons.")
        return []

    downloaded_files = []
    processed_count = 0

    query_words = query.split()
    smart_query_name = "_".join(query_words[:2]).lower()
    smart_query_name = "".join(c if c.isalnum() else "_" for c in smart_query_name)

    for page_id, page_data in data["query"]["pages"].items():
        if processed_count >= limit:
            break

        if "imageinfo" not in page_data or not page_data["imageinfo"]:
            # print(f"No imageinfo for page {page_id}, title {page_data.get('title')}")
            continue

        img_info = page_data["imageinfo"][0]
        api_media_type = img_info.get("mediatype", "UNKNOWN").lower()
        file_url = img_info.get("url")
        original_filename = page_data.get("title", f"File_{page_id}").replace("File:", "") # Get original filename
        file_extension = os.path.splitext(original_filename)[1].lower()

        if not file_url:
            # print(f"No URL for page {page_id}")
            continue

        # Filter by media type
        # Filter by media type more robustly
        type_matched = False
        if media_type == "all":
            type_matched = True
        elif media_type == "image":
            if api_media_type in ["bitmap", "drawing"] or \
               file_extension in [".jpg", ".jpeg", ".png", ".gif", ".svg", ".tiff", ".webp"]:
                type_matched = True
        elif media_type == "video":
            if api_media_type == "video" or \
               file_extension in [".ogv", ".webm", ".mp4", ".mov", ".mpeg", ".mpg"]:
                type_matched = True
        elif media_type == "audio":
            if api_media_type == "audio" or \
               file_extension in [".ogg", ".oga", ".wav", ".mp3", ".flac", ".opus", ".mid"]:
                type_matched = True

        if not type_matched:
            # print(f"Skipping {original_filename} (api_type: {api_media_type}, ext: {file_extension}) due to media_type mismatch for '{media_type}'")
            continue

        # Smart Filename: use query + original filename (cleaned)
        # Remove "File:" prefix if present from title for filename part
        filename_part = page_data.get("title", f"File_{page_id}")
        if filename_part.startswith("File:"):
            filename_part = filename_part[5:]

        clean_original_filename = "".join(c if c.isalnum() else "_" for c in os.path.splitext(filename_part)[0])[:50]
        # Ensure smart_query_name does not start or end with _ if it's short
        final_smart_query_name = smart_query_name.strip('_')

        final_filename = f"wikimedia_{final_smart_query_name}_{clean_original_filename}{file_extension}"
        # Replace multiple underscores with a single one
        final_filename = "_".join(filter(None, final_filename.split('_')))


        print(f"Attempting to download: {original_filename} (Type: {api_media_type}) from {file_url}")
        download_path = download_file(file_url, output_dir, final_filename, timeout=timeout)
        if download_path:
            downloaded_files.append(download_path)
            processed_count += 1

    if not downloaded_files:
        print(f"No files of type '{media_type}' downloaded for query '{query}'.")
    return downloaded_files


def list_wikimedia_media(query, list_limit=25, media_type="all", timeout=DEFAULT_DOWNLOAD_TIMEOUT):
    """
    Searches Wikimedia Commons for media and returns a list of item details.
    """
    params = {
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": query, "gsrnamespace": 6,
        "gsrlimit": list_limit, # How many search results to fetch for listing
        "prop": "imageinfo", "iiprop": "url|mediatype|size|extmetadata",
        "iilimit": 1, "utf8": 1,
    }

    # print(f"Listing Wikimedia Commons for '{query}' (type: {media_type})...")
    try:
        response = requests.get(WIKIMEDIA_API_URL, params=params, timeout=timeout)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.Timeout:
        print(f"Timeout during Wikimedia API (list) request for query: {query}")
        return []
    except requests.exceptions.RequestException as e:
        print(f"API request error for Wikimedia (list) query '{query}': {e}")
        return []
    except json.JSONDecodeError:
        print(f"Error decoding JSON from Wikimedia (list): {response.text if 'response' in locals() else 'No response text'}")
        return []

    if "error" in data:
        # print(f"Wikimedia API Error (list): {data['error'].get('info', 'Unknown error')}")
        return []
    if not data.get("query", {}).get("pages"):
        # print(f"No results found for '{query}' on Wikimedia Commons (list).")
        return []

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

    return found_items


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download media from Wikimedia Commons.")
    parser.add_argument("query", type=str, help="Search query for Wikimedia Commons.")
    parser.add_argument("--limit", type=int, default=5, help="Maximum number of items to download.")
    parser.add_argument("--output_dir", type=str, default="wikimedia_media", help="Directory to save downloaded media.")
    parser.add_argument(
        "--media_type",
        type=str,
        default="all",
        choices=["image", "video", "audio", "all"],
        help="Type of media to download (image, video, audio, all)."
    )
    parser.add_argument("--timeout", type=int, default=DEFAULT_DOWNLOAD_TIMEOUT, help="Download timeout in seconds.")

    args = parser.parse_args()

    print(f"Searching Wikimedia Commons for '{args.query}' (type: {args.media_type}) and downloading up to {args.limit} items to '{args.output_dir}'...")
    downloaded = search_wikimedia(args.query, args.limit, args.output_dir, args.media_type, args.timeout)
    if downloaded:
        print(f"Wikimedia Commons: Successfully downloaded {len(downloaded)} files.")
    else:
        print("Wikimedia Commons: No files downloaded for the specified criteria.")
    print("Wikimedia Commons download process complete.")
