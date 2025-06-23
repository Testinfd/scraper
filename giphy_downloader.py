import requests
import os
import argparse

# Attempt to get API key from environment variable, otherwise use placeholder
GIPHY_API_KEY = os.environ.get("GIPHY_API_KEY", "YOUR_GIPHY_API_KEY_HERE")
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
        # print(f"API request error for Giphy query '{query}': {e}")
        return {"items": [], "error": f"Giphy: API request error for '{query[:50]}': {e}", "status_message": None}
    except requests.exceptions.JSONDecodeError: # Corrected exception type
        # print(f"Error decoding JSON from Giphy: {response.text if 'response' in locals() else 'No response text'}")
        return {"items": [], "error": f"Giphy: Error decoding API response for '{query[:50]}'", "status_message": None}
    except Exception as e: # Catch other potential errors
        return {"items": [], "error": f"Giphy: Unexpected error for '{query[:50]}': {e}", "status_message": None}

    if not data.get("data"):
        # print(f"No results found for '{query}' on Giphy.") # Less verbose for listing
        return {"items": [], "error": None, "status_message": f"Giphy: No results found for '{query[:50]}'"}

    found_items = []
    query_words = query.split()
    smart_query_name_base = "_".join(query_words[:2]).lower()
    smart_query_name_base = "".join(c if c.isalnum() else "_" for c in smart_query_name_base)

    for item in data["data"]:
        item_id = item.get("id")
        title = item.get("title") or f"Giphy {item_id}"
        images_data = item.get("images", {})

        media_item_url = None
        file_extension = ".gif"  # Default
        item_actual_media_type = "gif"  # Default
        size_bytes = None
        selected_rendition_key = None # To fetch size from the correct rendition

        # Determine media type and URL, prioritize based on request
        if item.get("type") == "sticker" and (media_type == "sticker" or media_type == "all"):
            selected_rendition_key = "original"
            rendition_info = images_data.get(selected_rendition_key, {})
            media_item_url = rendition_info.get("url")
            size_bytes = rendition_info.get("size") # Sticker .gif often has 'size'
            file_extension = ".gif" # Stickers are often GIFs
            if "webp" in rendition_info and rendition_info.get("webp_size"): # Prefer webp if available and has size
                # This logic can be expanded if webp is a distinct preferred type
                pass
            item_actual_media_type = "sticker"

        elif (media_type == "video" or media_type == "all"):
            original_mp4_info = images_data.get("original_mp4", {})
            hd_mp4_info = images_data.get("hd", {})  # Older format

            if original_mp4_info.get("mp4"):
                selected_rendition_key = "original_mp4"
                media_item_url = original_mp4_info.get("mp4")
                size_bytes = original_mp4_info.get("mp4_size")  # Specific key for mp4 size
                file_extension = ".mp4"
                item_actual_media_type = "video"
            elif hd_mp4_info.get("mp4"):  # Fallback to HD if original_mp4 not present
                selected_rendition_key = "hd"
                media_item_url = hd_mp4_info.get("mp4")
                size_bytes = hd_mp4_info.get("size")  # HD might use generic 'size'
                file_extension = ".mp4"
                item_actual_media_type = "video"

        if not media_item_url and (media_type == "gif" or media_type == "all" or media_type == "image"):
            # Fallback to GIF if video not found/requested or sticker not primary
            original_gif_info = images_data.get("original", {})
            if original_gif_info.get("url"):
                selected_rendition_key = "original"
                media_item_url = original_gif_info.get("url")
                size_bytes = original_gif_info.get("size")
                file_extension = ".gif"
                item_actual_media_type = "gif"
                if item.get("type") == "sticker": # If it's a sticker but GIF was requested
                    item_actual_media_type = "sticker" # Keep its original type designation

        # Ensure size_bytes is integer if found as string
        if size_bytes is not None:
            try:
                size_bytes = int(size_bytes)
            except ValueError:
                # print(f"Warning: Could not convert size '{size_bytes}' to int for Giphy item {item_id}")
                size_bytes = None

        # If size_bytes is still None and we have a selected_rendition_key, try 'size' field for that rendition
        if size_bytes is None and selected_rendition_key:
            rendition_data = images_data.get(selected_rendition_key, {})
            if rendition_data.get("size"):
                try:
                    size_bytes = int(rendition_data.get("size"))
                except ValueError:
                    size_bytes = None


        if media_item_url:
            # Filter based on requested media_type vs what we found
            if media_type != "all":
                if media_type == "gif" and item_actual_media_type not in ["gif", "sticker"]:
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
                "type": item_actual_media_type,  # gif, video, sticker
                "filename": file_name,
                "platform": "giphy",
                "size_bytes": size_bytes # Add the size
            })
    return {"items": found_items, "error": None, "status_message": None if found_items else f"Giphy: No items matched criteria for '{query[:50]}'"}


if __name__ == "__main__":
    # Updated main for testing the new return type of list_giphy_media
    parser = argparse.ArgumentParser(description="Download media from Giphy.") # Changed "GIFs" to "media"
    parser.add_argument("query", type=str, help="Search query for Giphy.")
    parser.add_argument("--limit", type=int, default=5, help="Maximum number of items to download.")
    parser.add_argument("--output_dir", type=str, default="giphy_media", help="Directory to save downloaded media.")
    parser.add_argument("--media_type", type=str, default="gif", choices=["gif", "video", "sticker", "all"], help="Type of media to prefer.")
    parser.add_argument("--timeout", type=int, default=DEFAULT_DOWNLOAD_TIMEOUT, help="Download timeout in seconds.")


    args = parser.parse_args()

    if GIPHY_API_KEY == "YOUR_GIPHY_API_KEY_HERE":
        print("Please replace 'YOUR_GIPHY_API_KEY_HERE' with your actual Giphy API key in giphy_downloader.py")
    else:
        # Test listing
        print(f"\n--- Listing Giphy for '{args.query}' (type: {args.media_type}, limit: {args.limit}) ---")
        list_result = list_giphy_media(args.query, args.limit, args.media_type, args.timeout)
        if list_result.get("error"):
            print(f"Error listing: {list_result['error']}")
        elif not list_result.get("items") and list_result.get("status_message"):
            print(f"Status listing: {list_result['status_message']}")
        elif list_result.get("items"):
            print(f"Found {len(list_result['items'])} items for listing:")
            for item in list_result['items']:
                print(f"  - Title: {item['title']}, Type: {item['type']}, URL: {item['url']}")
        else:
            print("No items found or an unknown issue occurred during listing.")

        # Test downloading using search_giphy
        print(f"\n--- Downloading from Giphy for '{args.query}' (type: {args.media_type}, limit: {args.limit}) ---")
        downloaded_files = search_giphy(args.query, args.limit, args.output_dir, args.media_type, args.timeout)
        if downloaded_files:
            print(f"Giphy: Successfully downloaded {len(downloaded_files)} files to '{args.output_dir}'.")
        else:
            # search_giphy prints its own "No results found" or error during processing,
            # so this specific "else" might be redundant if search_giphy is verbose.
            print(f"Giphy: No files were downloaded for '{args.query}'. Check logs if items were expected.")

        print("\nGiphy CLI test process complete.")
