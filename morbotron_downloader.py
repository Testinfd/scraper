import requests
import os
import argparse
import json

MORBOTRON_SEARCH_API_URL = "https://morbotron.com/api/search"
MORBOTRON_IMAGE_URL_TEMPLATE = "https://morbotron.com/img/{episode}/{timestamp}.jpg"
DEFAULT_DOWNLOAD_TIMEOUT = 10 # seconds

def download_file(url, folder_name, file_name, timeout=DEFAULT_DOWNLOAD_TIMEOUT):
    """Downloads a file from a URL into a specified folder with a timeout."""
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)

    headers = { # Morbotron might require a common User-Agent
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

def search_morbotron(query, limit=5, output_dir="morbotron_media", media_type="image", timeout=DEFAULT_DOWNLOAD_TIMEOUT):
    """
    Searches Morbotron for screencaps (images) based on a quote and downloads them.
    The 'media_type' parameter is included for consistency but Morbotron primarily provides JPG images.
    """
    if media_type not in ["image", "all"]:
        print(f"Morbotron only supports 'image' or 'all' media types. Requested: {media_type}. Defaulting to 'image'.")
        # No specific filtering needed as Morbotron API returns image data directly.

    params = {"q": query}
    headers = { # Morbotron might require a common User-Agent for its API too
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    response = requests.get(MORBOTRON_SEARCH_API_URL, params=params, headers=headers, timeout=timeout) # Added timeout to API call as well
    response.raise_for_status()

    try:
        results = response.json()
    except json.JSONDecodeError:
        print(f"Error decoding JSON from Morbotron: {response.text}")
        return []

    if not results:
        print(f"No results found for '{query}' on Morbotron.")
        return []

    downloaded_files = []
    # Smart filename: use 1-2 words from query
    query_words = query.split()
    smart_query_name = "_".join(query_words[:2]).lower()
    smart_query_name = "".join(c if c.isalnum() else "_" for c in smart_query_name)

    for i, item in enumerate(results):
        if i >= limit:
            break

        try:
            episode = item.get("Episode")
            timestamp = item.get("Timestamp")
            # frame_id = item.get("Id") # For more uniqueness if needed

            if not episode or timestamp is None: # Timestamp can be 0
                print(f"Missing Episode or Timestamp in item: {item}")
                continue

            image_url = MORBOTRON_IMAGE_URL_TEMPLATE.format(episode=episode, timestamp=timestamp)
            file_extension = ".jpg" # Morbotron is consistently jpg

            # Smart Filename
            file_name = f"morbotron_{smart_query_name}_{episode}_{timestamp}{file_extension}"

            download_path = download_file(image_url, output_dir, file_name, timeout=timeout)
            if download_path:
                downloaded_files.append(download_path)

        except Exception as e:
            print(f"Error processing Morbotron item {item}: {e}")

    return downloaded_files


def list_morbotron_media(query, limit=25, media_type="image", timeout=DEFAULT_DOWNLOAD_TIMEOUT):
    """
    Searches Morbotron for screencaps (images) based on a quote and returns a list of item details.
    """
    if media_type not in ["image", "all"]:
        # print(f"Morbotron primarily provides images. Requested: {media_type}.")
        return [] # Only proceed if image is acceptable

    params = {"q": query}
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        response = requests.get(MORBOTRON_SEARCH_API_URL, params=params, headers=headers, timeout=timeout)
        response.raise_for_status()
        results = response.json()
    except requests.exceptions.Timeout:
        print(f"Timeout during Morbotron API request for query: {query}")
        return []
    except requests.exceptions.RequestException as e:
        print(f"API request error for Morbotron query '{query}': {e}")
        return []
    except json.JSONDecodeError:
        print(f"Error decoding JSON from Morbotron: {response.text if 'response' in locals() else 'No response text'}")
        return []

    if not results:
        # print(f"No results found for '{query}' on Morbotron.")
        return []

    found_items = []
    query_words = query.split()
    smart_query_name_base = "_".join(query_words[:2]).lower()
    smart_query_name_base = "".join(c if c.isalnum() else "_" for c in smart_query_name_base)

    # Morbotron API returns a list of results, limit is applied by iterating
    for i, item in enumerate(results):
        if i >= limit: # Apply limit to the number of items listed
            break

        episode = item.get("Episode")
        timestamp = item.get("Timestamp")

        if not episode or timestamp is None:
            continue

        image_url = MORBOTRON_IMAGE_URL_TEMPLATE.format(episode=episode, timestamp=timestamp)
        file_extension = ".jpg"

        title = f"Morbotron Screencap - S{episode} T{timestamp}" # Example title
        file_name = f"morbotron_{smart_query_name_base}_{episode}_{timestamp}{file_extension}"

        found_items.append({
            "id": f"{episode}_{timestamp}", # Unique ID for Morbotron item
            "title": title,
            "url": image_url,
            "type": "image", # Morbotron is always image
            "filename": file_name,
            "platform": "morbotron"
        })

    return found_items


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download screencaps from Morbotron.")
    parser.add_argument("query", type=str, help="Search query (quote) for Morbotron.")
    parser.add_argument("--limit", type=int, default=5, help="Maximum number of screencaps to download.")
    parser.add_argument("--output_dir", type=str, default="morbotron_media", help="Directory to save downloaded screencaps.")

    args = parser.parse_args()

    print(f"Searching Morbotron for '{args.query}' and downloading up to {args.limit} screencaps to '{args.output_dir}'...")
    search_morbotron(args.query, args.limit, args.output_dir)
    print("Morbotron download process complete.")
