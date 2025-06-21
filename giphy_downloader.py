import requests
import os
import argparse

GIPHY_API_KEY = "YOUR_GIPHY_API_KEY_HERE"  # IMPORTANT: Replace with your Giphy API Key
GIPHY_SEARCH_URL = "https://api.giphy.com/v1/gifs/search"

def download_file(url, folder_name, file_name):
    """Downloads a file from a URL into a specified folder."""
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)

    response = requests.get(url, stream=True)
    response.raise_for_status()  # Ensure we notice bad responses

    file_path = os.path.join(folder_name, file_name)

    with open(file_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f"Downloaded {file_name} to {folder_name}")
    return file_path

def search_giphy(query, limit=5, output_dir="giphy_media"):
    """
    Searches Giphy for GIFs based on a query and downloads them.
    """
    params = {
        "api_key": GIPHY_API_KEY,
        "q": query,
        "limit": limit,
        "offset": 0,
        "rating": "g",  # Default to G-rated content, can be changed
        "lang": "en"
    }

    response = requests.get(GIPHY_SEARCH_URL, params=params)
    response.raise_for_status()
    data = response.json()

    if not data.get("data"):
        print(f"No results found for '{query}' on Giphy.")
        return

    downloaded_files = []
    for item in data["data"]:
        try:
            gif_id = item.get("id")
            # Prefer original mp4 for smaller size if available, else original gif
            # Using 'original' GIF version for now for simplicity, can be refined
            original_gif_url = item.get("images", {}).get("original", {}).get("url")

            if not original_gif_url:
                print(f"Could not find original GIF URL for item ID {gif_id}")
                continue

            # Create a somewhat unique filename
            file_extension = ".gif" # Assume .gif, could parse from URL if more robust
            file_name = f"giphy_{query.replace(' ', '_')}_{gif_id}{file_extension}"

            download_path = download_file(original_gif_url, output_dir, file_name)
            downloaded_files.append(download_path)

        except Exception as e:
            print(f"Error processing Giphy item {item.get('id')}: {e}")

    return downloaded_files

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download GIFs from Giphy.")
    parser.add_argument("query", type=str, help="Search query for Giphy.")
    parser.add_argument("--limit", type=int, default=5, help="Maximum number of GIFs to download.")
    parser.add_argument("--output_dir", type=str, default="giphy_media", help="Directory to save downloaded GIFs.")

    args = parser.parse_args()

    print(f"Searching Giphy for '{args.query}' and downloading up to {args.limit} GIFs to '{args.output_dir}'...")
    search_giphy(args.query, args.limit, args.output_dir)
    print("Giphy download process complete.")
