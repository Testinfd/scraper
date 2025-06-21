import requests
import os
import argparse

GIPHY_API_KEY = "YOUR_GIPHY_API_KEY_HERE"  # IMPORTANT: Replace with your Giphy API Key
GIPHY_SEARCH_URL = "https://api.giphy.com/v1/gifs/search"
DEFAULT_DOWNLOAD_TIMEOUT = 10 # seconds

def download_file(url, folder_name, file_name, timeout=DEFAULT_DOWNLOAD_TIMEOUT):
    """Downloads a file from a URL into a specified folder with a timeout."""
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)

    try:
        response = requests.get(url, stream=True, timeout=timeout)
        response.raise_for_status()  # Ensure we notice bad responses

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

def search_giphy(query, limit=5, output_dir="giphy_media", media_type="gif", timeout=DEFAULT_DOWNLOAD_TIMEOUT):
    """
    Searches Giphy for media based on a query and downloads them.
    Currently, Giphy API primarily returns GIFs.
    """
    if GIPHY_API_KEY == "YOUR_GIPHY_API_KEY_HERE":
        print("Giphy API key is not set. Please set it in giphy_downloader.py.")
        return []

    # Giphy API 'type' parameter can be 'gifs', 'stickers', 'text'. Defaulting to gifs.
    # For simplicity, we'll stick to 'gifs' as 'videos' isn't a direct search type in the same way.
    # The main media type filtering will be by file extension if different formats were available.
    search_type = "gifs"
    if media_type == "sticker":
        search_type = "stickers"
    # Note: Giphy API also has a video API, but it's different from the GIF search.
    # This function will focus on GIF-like media from the standard search endpoint.

    params = {
        "api_key": GIPHY_API_KEY,
        "q": query,
        "limit": limit,
        "offset": 0,
        "rating": "g",
        "lang": "en",
        # "type": search_type # This param is for search type (gifs, stickers, text) not file format
    }

    response = requests.get(GIPHY_SEARCH_URL, params=params, timeout=timeout)
    response.raise_for_status()
    data = response.json()

    if not data.get("data"):
        print(f"No results found for '{query}' on Giphy.")
        return []

    downloaded_files = []
    # Smart filename: use 1-2 words from query
    query_words = query.split()
    smart_query_name = "_".join(query_words[:2]).lower()
    smart_query_name = "".join(c if c.isalnum() else "_" for c in smart_query_name)


    for item in data["data"]:
        try:
            item_id = item.get("id")
            # Giphy's 'images' object has various formats.
            # 'original' is usually a large GIF.
            # 'original_mp4' is often available and smaller for animated content.
            # 'fixed_height_small' or 'preview_gif' for smaller previews.

            media_item_url = None
            file_extension = ".gif" # Default to .gif

            if media_type == "video" or media_type == "all": # Prioritize video if requested
                if item.get("images", {}).get("original_mp4", {}).get("mp4"):
                    media_item_url = item.get("images").get("original_mp4").get("mp4")
                    file_extension = ".mp4"
                elif item.get("images", {}).get("hd", {}).get("mp4"): # Some older items might have this
                     media_item_url = item.get("images").get("hd").get("mp4")
                     file_extension = ".mp4"

            if not media_item_url and (media_type == "gif" or media_type == "all" or media_type == "image"):
                # Fallback to gif if video not found or gif specifically requested
                media_item_url = item.get("images", {}).get("original", {}).get("url")
                file_extension = ".gif" # Ensure it's .gif
                # Giphy API also returns 'type' which can be 'gif', 'sticker', etc.
                # We could use item.get('type') to refine extension if needed, but URL often has it.

            if not media_item_url:
                print(f"Could not find suitable media URL for item ID {item_id} (type: {media_type})")
                continue

            # Smart Filename
            file_name = f"giphy_{smart_query_name}_{item_id}{file_extension}"

            download_path = download_file(media_item_url, output_dir, file_name, timeout=timeout)
            if download_path:
                downloaded_files.append(download_path)

        except Exception as e:
            print(f"Error processing Giphy item {item.get('id')}: {e}")

    return downloaded_files


def list_giphy_media(query, limit=25, media_type="gif", timeout=DEFAULT_DOWNLOAD_TIMEOUT):
    """
    Searches Giphy for media based on a query and returns a list of media item details.
    """
    if GIPHY_API_KEY == "YOUR_GIPHY_API_KEY_HERE":
        print("Giphy API key is not set. Please set it in giphy_downloader.py.")
        return []

    search_type = "gifs"
    if media_type == "sticker":
        search_type = "stickers"

    params = {
        "api_key": GIPHY_API_KEY,
        "q": query,
        "limit": limit, # Fetch more for listing, actual download limit applied later
        "offset": 0,
        "rating": "g",
        "lang": "en",
    }

    try:
        response = requests.get(GIPHY_SEARCH_URL, params=params, timeout=timeout)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.Timeout:
        print(f"Timeout during Giphy API request for query: {query}")
        return []
    except requests.exceptions.RequestException as e:
        print(f"API request error for Giphy query '{query}': {e}")
        return []
    except json.JSONDecodeError:
        print(f"Error decoding JSON from Giphy: {response.text if 'response' in locals() else 'No response text'}")
        return []

    if not data.get("data"):
        # print(f"No results found for '{query}' on Giphy.") # Less verbose for listing
        return []

    found_items = []
    query_words = query.split()
    smart_query_name_base = "_".join(query_words[:2]).lower()
    smart_query_name_base = "".join(c if c.isalnum() else "_" for c in smart_query_name_base)

    for item in data["data"]:
        item_id = item.get("id")
        title = item.get("title") or f"Giphy {item_id}"

        media_item_url = None
        file_extension = ".gif"
        item_actual_media_type = "gif" # Giphy's 'type' field (gif, sticker, etc.)

        if item.get("type") == "sticker" and (media_type == "sticker" or media_type == "all"):
             media_item_url = item.get("images", {}).get("original", {}).get("url") # Stickers are usually gifs
             file_extension = ".gif" # or could be webp sometimes
             item_actual_media_type = "sticker"
        elif (media_type == "video" or media_type == "all"):
            if item.get("images", {}).get("original_mp4", {}).get("mp4"):
                media_item_url = item.get("images").get("original_mp4").get("mp4")
                file_extension = ".mp4"
                item_actual_media_type = "video"
            elif item.get("images", {}).get("hd", {}).get("mp4"):
                 media_item_url = item.get("images").get("hd").get("mp4")
                 file_extension = ".mp4"
                 item_actual_media_type = "video"

        if not media_item_url and (media_type == "gif" or media_type == "all" or media_type == "image"):
            media_item_url = item.get("images", {}).get("original", {}).get("url")
            file_extension = ".gif"
            item_actual_media_type = "gif"
            if item.get("type") == "sticker": # if it's a sticker but gif was requested
                item_actual_media_type = "sticker"


        if media_item_url:
            # Filter based on requested media_type vs what we found
            if media_type != "all":
                if media_type == "gif" and item_actual_media_type not in ["gif", "sticker"]: # sticker can be a gif
                    continue
                if media_type == "sticker" and item_actual_media_type != "sticker":
                    continue
                if media_type == "video" and item_actual_media_type != "video":
                    continue

            file_name = f"giphy_{smart_query_name_base}_{item_id}{file_extension}"
            found_items.append({
                "id": item_id,
                "title": title,
                "url": media_item_url,
                "type": item_actual_media_type, # gif, video, sticker
                "filename": file_name,
                "platform": "giphy"
            })
    return found_items


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download GIFs from Giphy.")
    parser.add_argument("query", type=str, help="Search query for Giphy.")
    parser.add_argument("--limit", type=int, default=5, help="Maximum number of GIFs to download.")
    parser.add_argument("--output_dir", type=str, default="giphy_media", help="Directory to save downloaded GIFs.")

    args = parser.parse_args()

    print(f"Searching Giphy for '{args.query}' and downloading up to {args.limit} GIFs to '{args.output_dir}'...")
    search_giphy(args.query, args.limit, args.output_dir)
    print("Giphy download process complete.")
