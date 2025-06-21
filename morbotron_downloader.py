import requests
import os
import argparse
import json

MORBOTRON_SEARCH_API_URL = "https://morbotron.com/api/search"
MORBOTRON_IMAGE_URL_TEMPLATE = "https://morbotron.com/img/{episode}/{timestamp}.jpg"

def download_file(url, folder_name, file_name):
    """Downloads a file from a URL into a specified folder."""
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)

    headers = { # Morbotron might require a common User-Agent
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    response = requests.get(url, stream=True, headers=headers)
    response.raise_for_status()

    file_path = os.path.join(folder_name, file_name)

    with open(file_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f"Downloaded {file_name} to {folder_name}")
    return file_path

def search_morbotron(query, limit=5, output_dir="morbotron_media"):
    """
    Searches Morbotron for screencaps based on a quote and downloads them.
    """
    params = {"q": query}
    headers = { # Morbotron might require a common User-Agent for its API too
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    response = requests.get(MORBOTRON_SEARCH_API_URL, params=params, headers=headers)
    response.raise_for_status()

    try:
        results = response.json()
    except json.JSONDecodeError:
        print(f"Error decoding JSON from Morbotron: {response.text}")
        return

    if not results:
        print(f"No results found for '{query}' on Morbotron.")
        return

    downloaded_files = []
    for i, item in enumerate(results):
        if i >= limit:
            break

        try:
            episode = item.get("Episode")
            timestamp = item.get("Timestamp")
            frame_id = item.get("Id") # For more uniqueness if needed

            if not episode or timestamp is None: # Timestamp can be 0
                print(f"Missing Episode or Timestamp in item: {item}")
                continue

            image_url = MORBOTRON_IMAGE_URL_TEMPLATE.format(episode=episode, timestamp=timestamp)

            # Create a unique filename
            # Clean query for filename, max 30 chars
            clean_query = "".join(c if c.isalnum() else "_" for c in query[:30])
            file_name = f"morbotron_{clean_query}_{episode}_{timestamp}.jpg"

            download_path = download_file(image_url, output_dir, file_name)
            downloaded_files.append(download_path)

        except Exception as e:
            print(f"Error processing Morbotron item {item}: {e}")

    return downloaded_files

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download screencaps from Morbotron.")
    parser.add_argument("query", type=str, help="Search query (quote) for Morbotron.")
    parser.add_argument("--limit", type=int, default=5, help="Maximum number of screencaps to download.")
    parser.add_argument("--output_dir", type=str, default="morbotron_media", help="Directory to save downloaded screencaps.")

    args = parser.parse_args()

    print(f"Searching Morbotron for '{args.query}' and downloading up to {args.limit} screencaps to '{args.output_dir}'...")
    search_morbotron(args.query, args.limit, args.output_dir)
    print("Morbotron download process complete.")
