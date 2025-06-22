import requests
import os
import argparse
import json

PIXABAY_API_URL = "https://pixabay.com/api/videos/"
# IMPORTANT: Replace with your Pixabay API Key
PIXABAY_API_KEY = "YOUR_PIXABAY_API_KEY_HERE"
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
        print(f"API request error for Pixabay query '{query}': {e}")
        return []
    except json.JSONDecodeError:
        print(f"Error decoding JSON from Pixabay: {response.text if 'response' in locals() else 'No response text'}")
        return []

    if not data.get("hits"):
        return []

    found_items = []
    query_words = query.split()
    smart_query_name_base = "_".join(query_words[:2]).lower()
    smart_query_name_base = "".join(c if c.isalnum() else "_" for c in smart_query_name_base).strip('_')

    for hit in data["hits"][:list_limit]: # Apply overall list_limit after fetching per_page
        video_info = hit.get("videos", {})
        # Prefer medium quality, fallback to large, then small.
        video_url = None
        if video_info.get("medium", {}).get("url"):
            video_url = video_info["medium"]["url"]
        elif video_info.get("large", {}).get("url"):
            video_url = video_info["large"]["url"]
        elif video_info.get("small", {}).get("url"):
            video_url = video_info["small"]["url"]

        if not video_url:
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
            "preview_image_url": hit.get("picture_id") # This is just an ID, not full URL. Actual preview: `https://i.vimeocdn.com/video/{picture_id}_295x166.jpg` but this is for Vimeo.
                                                     # Pixabay API gives direct preview image in `userImageURL` for user, or `webformatURL` for image search.
                                                     # For videos, the preview is often part of the video player, not a direct image URL in API.
                                                     # The video object itself contains `picture_id`.
                                                     # The actual preview URL seems to be `https://i.vimeocdn.com/video/[picture_id]_1920x1080.jpg` (example)
                                                     # Let's use a generic placeholder or the video URL itself for preview for now.
                                                     # Pixabay's own site uses a URL like: https://cdn.pixabay.com/vimeo/{VIMEO_VIDEO_ID_from_page_url}/?Expires=...&Key-Pair-Id=...&Signature=...
                                                     # The API provides `picture_id` which seems to be a vimeo thumbnail id.
                                                     # Example: "picture_id": "7110920_1920" -> https://i.vimeocdn.com/video/7110920_1920.jpg (this structure might work)
            "preview_image_url": f"https://i.vimeocdn.com/video/{hit.get('picture_id')}.jpg" if hit.get('picture_id') else None,


        })
    return found_items

def search_pixabay_videos(query, limit=5, output_dir="pixabay_media", api_timeout=10, download_timeout=DEFAULT_DOWNLOAD_TIMEOUT, **kwargs):
    """
    Searches Pixabay for videos and downloads them.
    """
    # media_type is implicitly "video" here

    listed_items = list_pixabay_videos(query, list_limit=limit, api_timeout=api_timeout)

    if not listed_items:
        print(f"No videos found on Pixabay for query '{query}'.")
        return []

    downloaded_files = []
    for i, item in enumerate(listed_items):
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
