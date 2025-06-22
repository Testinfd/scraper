import requests
import os
import argparse
import json

COMB_IO_SEARCH_API_URL = "https://comb.io/api/v1/caption/search"
DEFAULT_DOWNLOAD_TIMEOUT = 10 # seconds

def download_file(url, folder_name, file_name, timeout=DEFAULT_DOWNLOAD_TIMEOUT):
    """Downloads a file from a URL into a specified folder with a timeout."""
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)

    headers = { # Mimic a browser User-Agent
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
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

def search_comb_io(query, limit=5, output_dir="comb_io_media", media_type="gif", timeout=DEFAULT_DOWNLOAD_TIMEOUT):
    """
    Searches Comb.io for media (GIFs or videos) based on a query and downloads them.
    Note: Comb.io API stability and access can be an issue.
    """
    params = {
        "q": query,
        "tagName": "",
        "showId": "",
        "comicId": "",
        "skip": 0,
        "take": limit, # Request slightly more if we filter, but API might cap it. For now, direct limit.
        "imgOnly": "false", # Seems to accept gifs/videos
        "exact": "false",
        "safe": "true" # Keep safe search on
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://comb.io/', # Simpler Referer
        'X-Requested-With': 'XMLHttpRequest'
    }

    try:
        response = requests.get(COMB_IO_SEARCH_API_URL, params=params, headers=headers, timeout=timeout)
        response.raise_for_status()
        results = response.json()
    except requests.exceptions.Timeout:
        print(f"Timeout during Comb.io API request for query: {query}")
        return []
    except requests.exceptions.RequestException as e:
        print(f"API request error for Comb.io query '{query}': {e}")
        return []
    except json.JSONDecodeError:
        print(f"Error decoding JSON from Comb.io: {response.text if 'response' in locals() else 'No response text'}")
        return []


    if not results or not isinstance(results, list) or len(results) == 0 :
        print(f"No results found for '{query}' on Comb.io, or unexpected response format.")
        return []

    downloaded_files = []
    count = 0
    # Smart filename: use 1-2 words from query
    query_words = query.split()
    smart_query_name = "_".join(query_words[:2]).lower()
    smart_query_name = "".join(c if c.isalnum() else "_" for c in smart_query_name)

    for item in results:
        if count >= limit:
            break

        try:
            item_id = item.get("id")
            # show_name = item.get("show_name", "UnknownShow").replace(" ", "_")
            # content_slug = item.get("content", "no_caption")[:20].replace(" ", "_").isalnum() or "caption"

            media_url = None
            file_extension = ""

            # Prioritize requested media type
            if media_type == "video" or (media_type == "all" and item.get("video_url")):
                media_url = item.get("video_url")
                file_extension = ".mp4"
            elif media_type == "gif" or (media_type == "all" and item.get("gif_url")):
                media_url = item.get("gif_url")
                file_extension = ".gif"
            elif media_type == "image": # Comb.io doesn't typically serve static images like jpg/png via these fields
                print(f"Comb.io item {item_id} does not directly provide static images in expected fields for query '{query}'. Skipping.")
                continue


            if not media_url:
                # print(f"Could not find {media_type} URL for Comb.io item ID {item_id} (query: {query})")
                continue

            # Smart Filename
            file_name = f"comb_{smart_query_name}_{item_id}{file_extension}"

            download_path = download_file(media_url, output_dir, file_name, timeout=timeout)
            if download_path:
                downloaded_files.append(download_path)
                count += 1

        except Exception as e:
            print(f"Error processing Comb.io item {item.get('id')}: {e}")

    return downloaded_files

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download media from Comb.io.")
    parser.add_argument("query", type=str, help="Search query for Comb.io.")
    parser.add_argument("--limit", type=int, default=5, help="Maximum number of items to download.")
    parser.add_argument("--output_dir", type=str, default="comb_io_media", help="Directory to save downloaded media.")
    parser.add_argument("--media_type", type=str, default="gif", choices=["gif", "video"], help="Type of media to download (gif or video).")

    args = parser.parse_args()

    print(f"Searching Comb.io for '{args.query}' ({args.media_type}s) and downloading up to {args.limit} items to '{args.output_dir}'...")
    search_comb_io(args.query, args.limit, args.output_dir, args.media_type)
    print("Comb.io download process complete.")
