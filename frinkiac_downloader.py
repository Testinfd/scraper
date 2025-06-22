import requests
import os
import argparse
import json
import random

# Frinkiac uses these base URLs. No API key seems to be needed.
FRINKIAC_API_SEARCH_URL = "https://frinkiac.com/api/search"
FRINKIAC_API_CAPTION_URL = "https://frinkiac.com/api/caption" # To get nearby frames for context if needed
FRINKIAC_IMAGE_URL_TEMPLATE = "https://frinkiac.com/img/{episode}/{timestamp}.jpg"
FRINKIAC_GIF_URL_TEMPLATE = "https://frinkiac.com/gif/{episode}/{timestamp_start}/{timestamp_end}.gif" # For potential future GIF use

DEFAULT_DOWNLOAD_TIMEOUT = 10  # seconds
DEFAULT_API_TIMEOUT = 10 # seconds

# Morbotron (for Futurama, Rick and Morty) has a similar API structure.
# This downloader will be specific to Frinkiac (The Simpsons).

def download_file(url, folder_name, file_name, timeout=DEFAULT_DOWNLOAD_TIMEOUT):
    """Downloads a file from a URL into a specified folder with a timeout."""
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
    headers = {'User-Agent': 'MediaDownloaderTool/1.0 Python-requests/X.Y.Z'}
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

def list_frinkiac_media(query_quote, list_limit=25, api_timeout=DEFAULT_API_TIMEOUT, **kwargs):
    """
    Searches Frinkiac for screencaps based on a quote and returns a list of item details.
    kwargs are not used but included for consistency.
    """
    params = {"q": query_quote}
    headers = {'User-Agent': 'MediaDownloaderTool/1.0 Python-requests/X.Y.Z'}

    try:
        # First, search for frames matching the quote
        search_response = requests.get(FRINKIAC_API_SEARCH_URL, params=params, headers=headers, timeout=api_timeout)
        search_response.raise_for_status()
        search_results = search_response.json()
    except requests.exceptions.Timeout:
        print(f"Timeout during Frinkiac search API request for quote: {query_quote}")
        return []
    except requests.exceptions.RequestException as e:
        print(f"API request error for Frinkiac search query '{query_quote}': {e}")
        return []
    except json.JSONDecodeError:
        print(f"Error decoding JSON from Frinkiac search: {search_response.text if 'search_response' in locals() else 'No response text'}")
        return []

    if not search_results:
        # print(f"No direct frame matches found for '{query_quote}' on Frinkiac.")
        return []

    found_items = []
    # Sanitize query for filename
    query_words = query_quote.split()
    smart_query_name_base = "_".join(query_words[:2]).lower()
    smart_query_name_base = "".join(c if c.isalnum() else "_" for c in smart_query_name_base).strip('_')

    # The search_results is a list of frames. Each frame is a dict like: {"Id": int, "Episode": "S01E01", "Timestamp": int}
    # For each matched frame, we can also fetch caption details to get the exact subtitle.

    # Limit the number of initial frames to process to avoid too many API calls for captions
    # We might fetch captions for list_limit * 2 frames and then select the best ones or let user choose

    frames_to_process = search_results[:list_limit * 2] # Get more to have some variety

    for frame in frames_to_process:
        if len(found_items) >= list_limit:
            break

        episode = frame.get("Episode")
        timestamp = frame.get("Timestamp")

        if not episode or timestamp is None:
            continue

        # Fetch caption data to get the subtitle for better title/description
        caption_text = query_quote # Fallback to original query
        try:
            caption_params = {"e": episode, "t": timestamp}
            caption_response = requests.get(FRINKIAC_API_CAPTION_URL, params=caption_params, headers=headers, timeout=api_timeout)
            caption_response.raise_for_status()
            caption_data = caption_response.json()

            # Subtitle for the exact frame
            exact_subtitle = ""
            for sub in caption_data.get("Subtitles", []):
                if sub.get("RepresentativeTimestamp") == timestamp or sub.get("StartTimestamp") <= timestamp <= sub.get("EndTimestamp"):
                    exact_subtitle = sub.get("Content", "")
                    break
            if not exact_subtitle and caption_data.get("Subtitles"): # Fallback to first subtitle if exact not found
                 exact_subtitle = caption_data.get("Subtitles")[0].get("Content","")

            if exact_subtitle:
                caption_text = exact_subtitle

        except Exception as e:
            # print(f"Could not fetch caption for Frinkiac frame {episode}/{timestamp}: {e}")
            # Continue with the original quote as title basis
            pass


        image_url = FRINKIAC_IMAGE_URL_TEMPLATE.format(episode=episode, timestamp=timestamp)
        item_id = f"{episode}_{timestamp}"

        title = f"Frinkiac: {caption_text[:80]}" # Truncate long subtitles for title
        if len(caption_text) > 80: title += "..."

        file_extension = ".jpg"
        final_filename = f"frinkiac_{smart_query_name_base}_{item_id}{file_extension}"
        final_filename = "_".join(filter(None, final_filename.split('_')))

        found_items.append({
            "id": item_id,
            "title": title,
            "url": image_url, # This is the image URL
            "type": "image",
            "filename": final_filename,
            "platform": "frinkiac",
            "episode": episode,
            "timestamp": timestamp,
            "subtitle": caption_text # Full subtitle
        })

    return found_items[:list_limit] # Ensure final list adheres to list_limit


def search_frinkiac_media(query_quote, limit=5, output_dir="frinkiac_media", api_timeout=DEFAULT_API_TIMEOUT, download_timeout=DEFAULT_DOWNLOAD_TIMEOUT, **kwargs):
    """
    Searches Frinkiac for screencaps by quote and downloads them.
    """
    listed_items = list_frinkiac_media(query_quote, list_limit=limit, api_timeout=api_timeout)

    if not listed_items:
        print(f"No images found on Frinkiac for quote '{query_quote}'.")
        return []

    downloaded_files = []
    for i, item in enumerate(listed_items): # list_frinkiac_media already respects its internal limit
        if i >= limit: # Redundant if list_frinkiac_media returns exactly 'limit' items, but safe
            break
        print(f"Downloading Frinkiac image: {item['title']} from {item['url']}")
        download_path = download_file(item['url'], output_dir, item['filename'], timeout=download_timeout)
        if download_path:
            downloaded_files.append(download_path)

    return downloaded_files

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download screencaps from Frinkiac based on quotes.")
    parser.add_argument("quote", type=str, help="Search quote for Frinkiac.")
    parser.add_argument("--limit", type=int, default=5, help="Maximum number of images to download.")
    parser.add_argument("--output_dir", type=str, default="frinkiac_media", help="Directory to save downloaded images.")
    parser.add_argument("--api_timeout", type=int, default=DEFAULT_API_TIMEOUT, help="Timeout for API calls in seconds.")
    parser.add_argument("--download_timeout", type=int, default=DEFAULT_DOWNLOAD_TIMEOUT, help="Timeout for file downloads in seconds.")

    args = parser.parse_args()

    print(f"Searching Frinkiac for quote '{args.quote}' and downloading up to {args.limit} images to '{args.output_dir}'...")
    downloaded = search_frinkiac_media(
        args.quote,
        args.limit,
        args.output_dir,
        api_timeout=args.api_timeout,
        download_timeout=args.download_timeout
    )
    if downloaded:
        print(f"Frinkiac: Successfully downloaded {len(downloaded)} images.")
    else:
        print("Frinkiac: No images downloaded.")
    print("Frinkiac image download process complete.")
