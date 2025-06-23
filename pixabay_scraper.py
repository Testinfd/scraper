import requests
import os
import argparse
import json

PIXABAY_API_URL = "https://pixabay.com/api/videos/"
# Attempt to get API key from environment variable, otherwise use placeholder
PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY", "YOUR_PIXABAY_API_KEY_HERE")
DEFAULT_DOWNLOAD_TIMEOUT = 15  # seconds

def download_file(url, folder_name, file_name, timeout=DEFAULT_DOWNLOAD_TIMEOUT):
    """Downloads a file from a URL into a specified folder with a timeout."""
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)

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
        print(f"Downloaded {file_name} to {folder_name}")
        return file_path
    except requests.exceptions.Timeout:
        print(f"Timeout downloading {url} to {file_name}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error downloading {url} to {file_name}: {e}")
        return None

def list_pixabay_videos(query, list_limit=25, api_timeout=10, **kwargs):
    """
    Searches Pixabay for videos and returns a list of item details.
    kwargs may include 'media_type' but Pixabay video endpoint is specific.
    """
    if PIXABAY_API_KEY == "YOUR_PIXABAY_API_KEY_HERE":
        print("Pixabay API key is not set. Please set it in pixabay_downloader.py.")
        return []

    params = {
        "key": PIXABAY_API_KEY,
        "q": query,
        "video_type": "all", # or "film", "animation"
        "safesearch": "true",
        "per_page": max(3, min(list_limit, 200)), # API per_page is 3-200
        "page": 1
    }

    try:
        response = requests.get(PIXABAY_API_URL, params=params, timeout=api_timeout)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.Timeout:
        print(f"Timeout during Pixabay API request for query: {query}")
        return []
    except requests.exceptions.RequestException as e:
        # print(f"API request error for Pixabay query '{query}': {e}")
        return {"items": [], "error": f"Pixabay: API request error for '{query[:50]}': {e}", "status_message": None}
    except json.JSONDecodeError:
        # print(f"Error decoding JSON from Pixabay: {response.text if 'response' in locals() else 'No response text'}")
        return {"items": [], "error": f"Pixabay: Error decoding API response for '{query[:50]}'", "status_message": None}
    except Exception as e: # Catch other potential errors
        return {"items": [], "error": f"Pixabay: Unexpected error for '{query[:50]}': {e}", "status_message": None}


    if not data.get("hits"):
        return {"items": [], "error": None, "status_message": f"Pixabay: No results found for '{query[:50]}'"}

    found_items = []
    query_words = query.split()
    smart_query_name_base = "_".join(query_words[:2]).lower()
    smart_query_name_base = "".join(c if c.isalnum() else "_" for c in smart_query_name_base).strip('_')

    for hit in data["hits"][:list_limit]: # Apply overall list_limit after fetching per_page
        videos_data = hit.get("videos", {})
        chosen_video_rendition = None
        size_bytes = None
        video_thumbnail_url = None

        # Prefer medium quality, fallback to large, then small, and get its size and thumbnail.
        # Order of preference for rendition: medium, large, small, tiny
        preferred_renditions = ["medium", "large", "small", "tiny"]
        for rendition_key in preferred_renditions:
            rendition_data = videos_data.get(rendition_key)
            if rendition_data and rendition_data.get("url"):
                chosen_video_rendition = rendition_data
                break

        if not chosen_video_rendition:
            continue

        video_url = chosen_video_rendition.get("url")
        size_bytes = chosen_video_rendition.get("size")
        video_thumbnail_url = chosen_video_rendition.get("thumbnail")

        if not video_url: # Should not happen if chosen_video_rendition is set by now
            continue

        item_id = hit.get("id")
        tags = hit.get("tags", "")
        title = f"Pixabay Video {item_id} - {tags}" if tags else f"Pixabay Video {item_id}"

        # Filename from URL or construct one
        url_filename_part = video_url.split('/')[-1].split('?')[0] # Get filename from URL
        file_extension = os.path.splitext(url_filename_part)[1] or ".mp4" # Default to .mp4 if no ext

        final_filename = f"pixabay_{smart_query_name_base}_{item_id}{file_extension}"
        final_filename = "_".join(filter(None, final_filename.split('_')))

        found_items.append({
            "id": item_id,
            "title": title,
            "url": video_url,
            "type": "video", # Pixabay video endpoint returns videos
            "filename": final_filename,
            "platform": "pixabay",
            "size_bytes": size_bytes, # Add the size
            "preview_image_url": video_thumbnail_url # Use the correct thumbnail URL
        })
    return {"items": found_items, "error": None, "status_message": None if found_items else f"Pixabay: No items extracted after processing hits for '{query[:50]}'"}

def search_pixabay_videos(query, limit=5, output_dir="pixabay_media", api_timeout=10, download_timeout=DEFAULT_DOWNLOAD_TIMEOUT, **kwargs):
    """
    Searches Pixabay for videos and downloads them.
    """
    listed_items_data = list_pixabay_videos(query, list_limit=limit, api_timeout=api_timeout)

    if isinstance(listed_items_data, dict): # Check if it's a dict (success or error dict)
        listed_items = listed_items_data.get("items", [])
        if listed_items_data.get("error"):
            print(listed_items_data["error"])
        elif not listed_items and listed_items_data.get("status_message"):
            print(listed_items_data["status_message"])
        elif not listed_items and not listed_items_data.get("error"): # This case might be redundant if status_message always covers no items
            print(f"Pixabay: No videos found or extracted for query '{query}'.")
    elif isinstance(listed_items_data, list) and not listed_items_data: # It's an empty list (API key issue from list_pixabay_videos)
        listed_items = []
        # The message "Pixabay API key is not set..." is already printed by list_pixabay_videos.
        # Adding a specific message for search_pixabay_videos context.
        print(f"Pixabay: Skipping download for '{query}' as no items were listed (check API key or query).")
    else: # Unexpected return type or structure
        listed_items = []
        print(f"Pixabay: Unexpected data structure from list_pixabay_videos for query '{query}'. Cannot process.")

    if not listed_items: # This condition is met if API key is missing, or no items found, or error.
        return []

    downloaded_files = []
    for i, item in enumerate(listed_items): # list is already limited by list_pixabay_videos logic
        if i >= limit: # Ensure we don't download more than 'limit'
            break
        print(f"Downloading Pixabay video: {item['title']} from {item['url']}")
        download_path = download_file(item['url'], output_dir, item['filename'], timeout=download_timeout)
        if download_path:
            downloaded_files.append(download_path)

    return downloaded_files


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download videos from Pixabay.")
    parser.add_argument("query", type=str, help="Search query for Pixabay videos.")
    parser.add_argument("--limit", type=int, default=5, help="Maximum number of videos to download.")
    parser.add_argument("--output_dir", type=str, default="pixabay_media", help="Directory to save downloaded videos.")
    parser.add_argument("--api_timeout", type=int, default=10, help="Timeout for API calls in seconds.")
    parser.add_argument("--download_timeout", type=int, default=DEFAULT_DOWNLOAD_TIMEOUT, help="Timeout for file downloads in seconds.")

    args = parser.parse_args()

    if PIXABAY_API_KEY == "YOUR_PIXABAY_API_KEY_HERE":
        print("Please set your PIXABAY_API_KEY in pixabay_downloader.py to run this script.")
    else:
        print(f"Searching Pixabay for '{args.query}' videos and downloading up to {args.limit} items to '{args.output_dir}'...")
        downloaded = search_pixabay_videos(
            args.query,
            args.limit,
            args.output_dir,
            api_timeout=args.api_timeout,
            download_timeout=args.download_timeout
        )
        if downloaded:
            print(f"Pixabay: Successfully downloaded {len(downloaded)} videos.")
        else:
            print("Pixabay: No videos downloaded.")
        print("Pixabay video download process complete.")
