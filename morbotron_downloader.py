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

def search_morbotron(query, limit=5, output_dir="morbotron_media", media_type="image",
                     api_timeout=DEFAULT_API_TIMEOUT, download_timeout=DEFAULT_DOWNLOAD_TIMEOUT): # Added api_timeout, download_timeout
    """
    Searches Morbotron for screencaps (images) based on a quote and downloads them.
    Handles new dict return from list_morbotron_media.
    """
    # list_morbotron_media will handle the media_type check and return an error/status if incompatible.
    listed_items_data = list_morbotron_media(query, limit, media_type, api_timeout)
    listed_items = listed_items_data.get("items", [])

    if listed_items_data.get("error"):
        print(listed_items_data["error"])
    elif not listed_items and listed_items_data.get("status_message"):
        print(listed_items_data["status_message"])
    elif not listed_items and not listed_items_data.get("error"): # Generic message if no items and no specific status
        print(f"Morbotron: No images found or extracted for query '{query}'.")

    if not listed_items:
        return []

    downloaded_paths = []
    for i, item_to_dl in enumerate(listed_items):
        # The number of items in listed_items is already capped by 'limit' in list_morbotron_media's processing.
        # However, an additional explicit limit check here for direct downloads is fine.
        if i >= limit:
            break
        print(f"Downloading Morbotron image: {item_to_dl['title']} from {item_to_dl['url']}")
        dl_path = download_file(item_to_dl['url'], output_dir, item_to_dl['filename'], timeout=download_timeout)
        if dl_path:
            downloaded_paths.append(dl_path)
    return downloaded_paths


# DEFAULT_API_TIMEOUT for consistency with other modules
DEFAULT_API_TIMEOUT = 10

def list_morbotron_media(query, limit=25, media_type="image", api_timeout=DEFAULT_API_TIMEOUT): # Changed timeout to api_timeout
    """
    Searches Morbotron for screencaps (images) based on a quote and returns a dictionary
    with 'items', 'error', and 'status_message'.
    """
    if media_type not in ["image", "all"]:
        # print(f"Morbotron primarily provides images. Requested: {media_type}.")
        return {"items": [], "error": None, "status_message": f"Morbotron: Media type '{media_type}' not supported (only image/all)."}

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
        # print(f"API request error for Morbotron query '{query}': {e}")
        return {"items": [], "error": f"Morbotron: API request error for '{query[:50]}': {e}", "status_message": None}
    except json.JSONDecodeError:
        # print(f"Error decoding JSON from Morbotron: {response.text if 'response' in locals() else 'No response text'}")
        return {"items": [], "error": f"Morbotron: Error decoding API response for '{query[:50]}'", "status_message": None}
    except Exception as e: # Catch other potential errors
        return {"items": [], "error": f"Morbotron: Unexpected error for '{query[:50]}': {e}", "status_message": None}

    if not results:
        # print(f"No results found for '{query}' on Morbotron.")
        return {"items": [], "error": None, "status_message": f"Morbotron: No results found for '{query[:50]}'"}

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

    return {"items": found_items, "error": None, "status_message": None if found_items else f"Morbotron: No items extracted for '{query[:50]}'"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download screencaps from Morbotron.")
    parser.add_argument("query", type=str, help="Search query (quote) for Morbotron.")
    parser.add_argument("--limit", type=int, default=5, help="Maximum number of screencaps to download.")
    parser.add_argument("--output_dir", type=str, default="morbotron_media", help="Directory to save downloaded screencaps.")
    parser.add_argument("--media_type", type=str, default="image", choices=["image", "all"], help="Type of media.")
    parser.add_argument("--api_timeout", type=int, default=DEFAULT_API_TIMEOUT, help="Timeout for API calls in seconds.")
    parser.add_argument("--download_timeout", type=int, default=DEFAULT_DOWNLOAD_TIMEOUT, help="Timeout for file downloads in seconds.")

    args = parser.parse_args()

    # Test listing
    print(f"\n--- Listing Morbotron for '{args.query}' (limit: {args.limit}) ---")
    # Note: list_morbotron_media's media_type param is mainly for the check, actual API doesn't filter by it.
    list_result = list_morbotron_media(args.query, args.limit, args.media_type, args.api_timeout)
    if list_result.get("error"):
        print(f"Error listing: {list_result['error']}")
    elif not list_result.get("items") and list_result.get("status_message"):
        print(f"Status listing: {list_result['status_message']}")
    elif list_result.get("items"):
        print(f"Found {len(list_result['items'])} items for listing:")
        for item in list_result['items']:
            print(f"  - Title: {item['title']}, URL: {item['url']}")
    else:
        print("No items found or an unknown issue occurred during listing.")

    # Test downloading
    print(f"\n--- Downloading from Morbotron for '{args.query}' (limit: {args.limit}) ---")

    # Refactor search_morbotron to accept api_timeout and download_timeout
    # And to handle the new dict return from list_morbotron_media

    # First, let's define the refactored search_morbotron (this is unusual to do in __main__, but for the diff)
    def search_morbotron_refactored(query, limit=5, output_dir="morbotron_media", media_type="image",
                                    api_timeout_param=DEFAULT_API_TIMEOUT, download_timeout_param=DEFAULT_DOWNLOAD_TIMEOUT):
        listed_items_data = list_morbotron_media(query, limit, media_type, api_timeout_param)
        listed_items = listed_items_data.get("items", [])

        if listed_items_data.get("error"):
            print(listed_items_data["error"])
        elif not listed_items and listed_items_data.get("status_message"):
            print(listed_items_data["status_message"])
        elif not listed_items and not listed_items_data.get("error"):
             print(f"Morbotron: No images found or extracted for query '{query}'.")

        if not listed_items:
            return []

        downloaded_paths_list = []
        for i, item_to_dl in enumerate(listed_items):
            if i >= limit: break # Should be redundant if list already limited but good check
            print(f"Downloading Morbotron image: {item_to_dl['title']} from {item_to_dl['url']}")
            dl_path = download_file(item_to_dl['url'], output_dir, item_to_dl['filename'], timeout=download_timeout_param)
            if dl_path:
                downloaded_paths_list.append(dl_path)
        return downloaded_paths_list

    # Now call the refactored version for testing
    downloaded_paths = search_morbotron_refactored(
        args.query,
        args.limit,
        args.output_dir,
        args.media_type,
        api_timeout_param=args.api_timeout,
        download_timeout_param=args.download_timeout
    )

    if downloaded_paths:
        print(f"Morbotron: Successfully downloaded {len(downloaded_paths)} files.")
    # else: search_morbotron_refactored prints its own status/errors.

    print("\nMorbotron CLI test process complete.")
