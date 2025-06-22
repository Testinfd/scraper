import requests
import os
import argparse
import json

# Observed internal API endpoint for Mixkit. This might change without notice.
MIXKIT_API_URL = "https://mixkit.co/api/v1/items"
# Base URL for constructing some links if needed, or for Referer header
MIXKIT_BASE_URL = "https://mixkit.co"

DEFAULT_DOWNLOAD_TIMEOUT = 20  # seconds (videos can be larger)
DEFAULT_API_TIMEOUT = 15 # seconds

def download_file(url, folder_name, file_name, timeout=DEFAULT_DOWNLOAD_TIMEOUT):
    """Downloads a file from a URL into a specified folder with a timeout."""
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)

    # Mixkit CDN (assets.mixkit.co) might not need specific headers,
    # but it's good practice to send a generic User-Agent.
    headers = {
        'User-Agent': 'MediaDownloaderTool/1.0 Python-requests/X.Y.Z',
        'Referer': MIXKIT_BASE_URL # Sometimes helpful for CDNs
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

def list_mixkit_videos(query, list_limit=25, api_timeout=DEFAULT_API_TIMEOUT, **kwargs):
    """
    Searches Mixkit for videos using its observed internal API and returns a list of item details.
    kwargs may include 'media_type' but this function is video-specific.
    """
    params = {
        "search": query,
        "types": "video", # Explicitly searching for videos
        "sort_by": "relevance",
        "page": 1,
        "per_page": max(3, min(list_limit, 100)) # API seems to cap per_page, e.g. at 100
    }
    headers = {
        'User-Agent': 'MediaDownloaderTool/1.0 Python-requests/X.Y.Z',
        'Referer': f"{MIXKIT_BASE_URL}/free-stock-video/search/?q={query}", # Mimic browser referer
        'X-Requested-With': 'XMLHttpRequest' # Often used by internal APIs
    }

    try:
        response = requests.get(MIXKIT_API_URL, params=params, headers=headers, timeout=api_timeout)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.Timeout:
        print(f"Timeout during Mixkit API request for query: {query}")
        return []
    except requests.exceptions.RequestException as e:
        print(f"API request error for Mixkit query '{query}': {e}")
        if response is not None: print(f"Mixkit Response: {response.text}")
        return []
    except json.JSONDecodeError:
        print(f"Error decoding JSON from Mixkit: {response.text if 'response' in locals() else 'No response text'}")
        return []

    # Data structure is typically: {"items": [...], "total_items": ..., "total_pages": ...}
    if not data.get("items"):
        # print(f"No video results found for '{query}' on Mixkit.")
        return []

    found_items = []
    query_words = query.split()
    smart_query_name_base = "_".join(query_words[:2]).lower()
    smart_query_name_base = "".join(c if c.isalnum() else "_" for c in smart_query_name_base).strip('_')

    for item_data in data["items"][:list_limit]: # Apply overall list_limit
        item_id = item_data.get("id")
        title = item_data.get("name", f"Mixkit Video {item_id}")

        # Video URLs are often in 'previews' or a direct 'download_url' or similar key.
        # Example structure: item_data.get("previews", {}).get("mp4", {}).get("url")
        # Or sometimes item_data.get("downloadUrl")
        # Let's try to find a direct video URL. The API gives a "download_url" field.
        video_url = item_data.get("download_url")

        if not video_url:
            # Fallback: Check if there's a "url" field or inside "previews"
            if item_data.get("url") and item_data.get("url").endswith(".mp4"):
                 video_url = item_data.get("url")
            elif item_data.get("previews", {}).get("mp4", {}).get("url"):
                 video_url = item_data.get("previews", {}).get("mp4", {}).get("url")
            else: # Try to find any mp4 link in previews
                previews = item_data.get("previews", {})
                for key, val in previews.items():
                    if isinstance(val, dict) and val.get("url","").endswith(".mp4"):
                        video_url = val["url"]
                        break

        if not video_url:
            # print(f"Could not find video URL for Mixkit item: {title}")
            continue

        # Construct a filename
        file_extension = os.path.splitext(video_url.split('/')[-1].split('?')[0])[1] or ".mp4"
        final_filename = f"mixkit_{smart_query_name_base}_{item_id}{file_extension}"
        final_filename = "_".join(filter(None, final_filename.split('_')))

        # Preview image - often in 'thumbnail_url' or 'previews.jpg.url'
        preview_image_url = item_data.get("thumbnail_url")
        if not preview_image_url and item_data.get("previews",{}).get("jpg",{}).get("url"):
            preview_image_url = item_data.get("previews",{}).get("jpg",{}).get("url")

        found_items.append({
            "id": item_id,
            "title": title,
            "url": video_url, # Direct video URL
            "type": "video",
            "filename": final_filename,
            "platform": "mixkit",
            "preview_image_url": preview_image_url,
            "description": item_data.get("description_text", "")
        })

    return found_items


def search_mixkit_videos(query, limit=5, output_dir="mixkit_media", api_timeout=DEFAULT_API_TIMEOUT, download_timeout=DEFAULT_DOWNLOAD_TIMEOUT, **kwargs):
    """
    Searches Mixkit for videos and downloads them.
    """
    listed_items = list_mixkit_videos(query, list_limit=limit, api_timeout=api_timeout)

    if not listed_items:
        print(f"No videos found on Mixkit for query '{query}'.")
        return []

    downloaded_files = []
    for i, item in enumerate(listed_items):
        if i >= limit:
            break
        print(f"Downloading Mixkit video: {item['title']} ({item['url']})")
        download_path = download_file(item['url'], output_dir, item['filename'], timeout=download_timeout)
        if download_path:
            downloaded_files.append(download_path)

    return downloaded_files


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download videos from Mixkit.")
    parser.add_argument("query", type=str, help="Search query for Mixkit videos.")
    parser.add_argument("--limit", type=int, default=5, help="Maximum number of videos to download.")
    parser.add_argument("--output_dir", type=str, default="mixkit_media", help="Directory to save downloaded videos.")
    parser.add_argument("--api_timeout", type=int, default=DEFAULT_API_TIMEOUT, help="Timeout for API calls in seconds.")
    parser.add_argument("--download_timeout", type=int, default=DEFAULT_DOWNLOAD_TIMEOUT, help="Timeout for file downloads in seconds.")

    args = parser.parse_args()

    print(f"Searching Mixkit for '{args.query}' videos and downloading up to {args.limit} items to '{args.output_dir}'...")
    downloaded = search_mixkit_videos(
        args.query,
        args.limit,
        args.output_dir,
        api_timeout=args.api_timeout,
        download_timeout=args.download_timeout
    )
    if downloaded:
        print(f"Mixkit: Successfully downloaded {len(downloaded)} videos.")
    else:
        print("Mixkit: No videos downloaded.")
    print("Mixkit video download process complete.")
