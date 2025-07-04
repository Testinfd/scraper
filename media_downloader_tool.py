import argparse
import os
import requests # Required for get_remote_file_size
import time

# Import functions from existing downloader scripts
from giphy_downloader import search_giphy, list_giphy_media, download_file as giphy_download_file, DEFAULT_DOWNLOAD_TIMEOUT as GIPHY_TIMEOUT
from morbotron_scraper import search_morbotron, list_morbotron_media, download_file as morbotron_download_file, DEFAULT_DOWNLOAD_TIMEOUT as MORBOTRON_TIMEOUT
from wikimedia_scraper import search_wikimedia, list_wikimedia_media, download_file as wikimedia_download_file, DEFAULT_DOWNLOAD_TIMEOUT as WIKIMEDIA_TIMEOUT
from pixabay_scraper import search_pixabay_videos, list_pixabay_videos, download_file as pixabay_download_file, DEFAULT_DOWNLOAD_TIMEOUT as PIXABAY_TIMEOUT
from frinkiac_scraper import search_frinkiac_media, list_frinkiac_media, download_file as frinkiac_download_file, DEFAULT_DOWNLOAD_TIMEOUT as FRINKIAC_TIMEOUT
from mixkit_scraper import search_mixkit_videos, list_mixkit_videos, download_file as mixkit_download_file, DEFAULT_DOWNLOAD_TIMEOUT as MIXKIT_TIMEOUT
from wikimedia_oauth_scraper import search_wikimedia_oauth_media, list_wikimedia_oauth_media, download_file as wikimedia_oauth_download_file, DEFAULT_DOWNLOAD_TIMEOUT as WIKIMEDIA_OAUTH_TIMEOUT
# Comb.io is currently excluded
# from comb_io_scraper import search_comb_io, list_comb_io_media, download_file as comb_io_download_file, DEFAULT_DOWNLOAD_TIMEOUT as COMBIO_TIMEOUT

SUPPORTED_PLATFORMS = ["giphy", "morbotron", "wikimedia", "wikimedia_oauth", "pixabay", "frinkiac", "mixkit"]

def get_remote_file_size(url, timeout=5):
    """
    Fetches the size of a remote file using a HEAD request.
    Returns size in bytes, or None if size cannot be determined or an error occurs.
    """
    try:
        response = requests.head(url, timeout=timeout, allow_redirects=True)
        response.raise_for_status()  # Raise an exception for bad status codes
        content_length = response.headers.get('Content-Length')
        if content_length:
            return int(content_length)
        else:
            # print(f"Warning: Content-Length header not found for {url}")
            return None
    except requests.exceptions.Timeout:
        # print(f"Timeout trying to get file size for {url}")
        return None
    except requests.exceptions.RequestException as e:
        # print(f"Error getting file size for {url}: {e}")
        return None
    except Exception as e:
        # print(f"Unexpected error getting file size for {url}: {e}")
        return None

# Generic download function for interactive mode, using platform-specific downloaders
def download_selected_item(item, base_output_dir, download_timeout_override=None):
    # Ensure base_output_dir itself exists, though platform_output_dir creation is handled below
    if not os.path.exists(base_output_dir):
        try:
            os.makedirs(base_output_dir)
        except OSError as e:
            print(f"Error creating base directory {base_output_dir}: {e}")
            return None # Cannot proceed if base dir creation fails

    platform_output_dir = os.path.join(base_output_dir, item['platform'])
    if not os.path.exists(platform_output_dir):
        os.makedirs(platform_output_dir)

    print(f"Downloading '{item['title']}' ({item['type']}) from {item['platform']} to {platform_output_dir}...")

    actual_timeout = download_timeout_override # Global override takes precedence
    if actual_timeout is None: # If no global override, use platform default
        if item['platform'] == 'giphy': actual_timeout = GIPHY_TIMEOUT
        elif item['platform'] == 'morbotron': actual_timeout = MORBOTRON_TIMEOUT
        elif item['platform'] == 'wikimedia': actual_timeout = WIKIMEDIA_TIMEOUT
        elif item['platform'] == 'wikimedia_oauth': actual_timeout = WIKIMEDIA_OAUTH_TIMEOUT
        elif item['platform'] == 'pixabay': actual_timeout = PIXABAY_TIMEOUT
        elif item['platform'] == 'frinkiac': actual_timeout = FRINKIAC_TIMEOUT
        elif item['platform'] == 'mixkit': actual_timeout = MIXKIT_TIMEOUT
        # elif item['platform'] == 'comb_io': actual_timeout = COMBIO_TIMEOUT
        else: actual_timeout = 10 # A generic fallback

    downloader_function = None
    if item['platform'] == 'giphy': downloader_function = giphy_download_file
    elif item['platform'] == 'morbotron': downloader_function = morbotron_download_file
    elif item['platform'] == 'wikimedia': downloader_function = wikimedia_download_file
    elif item['platform'] == 'wikimedia_oauth': downloader_function = wikimedia_oauth_download_file
    elif item['platform'] == 'pixabay': downloader_function = pixabay_download_file
    elif item['platform'] == 'frinkiac': downloader_function = frinkiac_download_file
    elif item['platform'] == 'mixkit': downloader_function = mixkit_download_file
    # elif item['platform'] == 'comb_io': downloader_function = comb_io_download_file

    if downloader_function:
        return downloader_function(item['url'], platform_output_dir, item['filename'], timeout=actual_timeout)
    else:
        print(f"Error: No downloader function found for platform {item['platform']}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Unified Media Downloader Tool.")
    parser.add_argument(
        "queries",
        type=str,
        nargs='+', # Accept one or more queries
        help="Search query or queries for media. Multiple queries can be separated by spaces, or provide a list of keywords/phrases in a file (see --query_file)."
    )
    parser.add_argument(
        "--query_file",
        type=str,
        help="Path to a text file containing search queries, one per line. If provided, 'queries' argument is ignored."
    )
    parser.add_argument(
        "--platforms",
        nargs="+",
        required=True,
        choices=SUPPORTED_PLATFORMS,
        help=f"List of platforms to search (e.g., {' '.join(SUPPORTED_PLATFORMS)})."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Maximum number of items to download per query per platform."
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="downloaded_media",
        help="Base directory to save downloaded media. Platform-specific subfolders will be created."
    )
    parser.add_argument(
        "--media_type",
        type=str,
        default="all",
        choices=["all", "image", "gif", "video", "audio", "sticker"], # Expanded choices
        help="Preferred type of media to download (e.g., all, image, gif, video, audio). Note: 'sticker' is Giphy specific, 'audio' is Wikimedia specific."
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="If set, list found media and ask for confirmation before downloading each item."
    )
    parser.add_argument(
        "--download_timeout",
        type=int,
        default=None, # Will use platform-specific defaults if not set
        help="Global timeout in seconds for downloading each media file. Overrides platform defaults."
    )
    parser.add_argument(
        "--api_call_timeout", # separate timeout for API calls vs downloads
        type=int,
        default=10,
        help="Timeout in seconds for API search calls."
    )


    args = parser.parse_args()

    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
        print(f"Created base output directory: {args.output_dir}")

    search_queries = []
    if args.query_file:
        try:
            with open(args.query_file, 'r') as f:
                search_queries = [line.strip() for line in f if line.strip()]
            if not search_queries:
                print(f"Query file {args.query_file} is empty or contains no valid queries.")
                return
            print(f"Loaded {len(search_queries)} queries from {args.query_file}.")
        except FileNotFoundError:
            print(f"Error: Query file '{args.query_file}' not found.")
            return
    else:
        search_queries = args.queries

    if not search_queries:
        print("No search queries provided.")
        return

    for query_idx, current_query in enumerate(search_queries):
        print(f"\nProcessing query {query_idx + 1}/{len(search_queries)}: '{current_query}'")
        print(f"Platforms: {', '.join(args.platforms)}")
        print(f"Limit per platform: {args.limit}")
        print(f"Media type: {args.media_type}")
        print(f"Base output directory: {args.output_dir}")
        print(f"Interactive mode: {'On' if args.interactive else 'Off'}")
        print(f"Download timeout: {args.download_timeout if args.download_timeout is not None else 'Platform default'}")
        print(f"API call timeout: {args.api_call_timeout}s\n")

        # Sanitize query for directory name
        safe_query_dir_name = "".join(c if c.isalnum() else "_" for c in current_query[:50]).strip('_')
        query_specific_output_dir = os.path.join(args.output_dir, safe_query_dir_name if safe_query_dir_name else "default_query")
        if not os.path.exists(query_specific_output_dir):
            os.makedirs(query_specific_output_dir)
            # print(f"Created query-specific output directory: {query_specific_output_dir}")

        all_found_media_items = []

        # --- Listing Phase (for interactive mode or if we always want to list first) ---
        if args.interactive:
            print(f"--- Discovering media for '{current_query}' (interactive mode) ---")
            # Fetch lists of media items from each platform
            if "giphy" in args.platforms:
                all_found_media_items.extend(list_giphy_media(current_query, args.limit * 2, args.media_type, args.api_call_timeout))
            if "morbotron" in args.platforms:
                mt = "image" if args.media_type not in ["image", "all"] else args.media_type # Frinkiac/Morbotron are image specific
                if args.media_type == "all" or args.media_type == "image":
                     all_found_media_items.extend(list_morbotron_media(current_query, args.limit * 2, mt, args.api_call_timeout))
            if "wikimedia" in args.platforms:
                all_found_media_items.extend(list_wikimedia_media(current_query, args.limit * 2, args.media_type, args.api_call_timeout))
            if "wikimedia_oauth" in args.platforms:
                all_found_media_items.extend(list_wikimedia_oauth_media(current_query, args.limit * 2, args.media_type, args.api_call_timeout))
            if "pixabay" in args.platforms:
                # Pixabay downloader currently only supports video type via its video API
                if args.media_type == "all" or args.media_type == "video":
                    all_found_media_items.extend(list_pixabay_videos(current_query, args.limit * 2, api_timeout=args.api_call_timeout))
                elif args.interactive: # only print if interactive and type mismatch
                    print(f"Pixabay: Skipping as it only supports 'video' or 'all' media type for listing, not '{args.media_type}'.")
            if "frinkiac" in args.platforms:
                mt = "image" if args.media_type not in ["image", "all"] else args.media_type
                if args.media_type == "all" or args.media_type == "image": # Frinkiac is image specific
                    all_found_media_items.extend(list_frinkiac_media(current_query, args.limit * 2, api_timeout=args.api_call_timeout))
                elif args.interactive:
                    print(f"Frinkiac: Skipping as it only supports 'image' or 'all' media type for listing, not '{args.media_type}'.")
            if "mixkit" in args.platforms:
                # Mixkit downloader currently only supports video type
                if args.media_type == "all" or args.media_type == "video":
                    all_found_media_items.extend(list_mixkit_videos(current_query, args.limit * 2, api_timeout=args.api_call_timeout))
                elif args.interactive:
                     print(f"Mixkit: Skipping as it only supports 'video' or 'all' media type for listing, not '{args.media_type}'.")
            # Add other platforms (comb_io) here if they become active

            if not all_found_media_items:
                print(f"No media found for '{current_query}' across selected platforms with type '{args.media_type}'.")
                continue # Next query

            print(f"\n--- Found {len(all_found_media_items)} potential items for '{current_query}' ---")
            for idx, item in enumerate(all_found_media_items):
                print(f"{idx + 1}. [{item['platform']}] {item['title']} ({item['type']}) - {item['url']}")

            print("\nEnter numbers of items to download (e.g., 1 3 5), 'all', or 'none':")
            user_choice = input("> ").strip().lower()

            selected_items_to_download = []
            if user_choice == 'none':
                print("No items selected for download.")
            elif user_choice == 'all':
                selected_items_to_download = all_found_media_items[:args.limit * len(args.platforms)] # Respect overall limit
                print(f"Selected all {len(selected_items_to_download)} items (up to limit).")
            else:
                try:
                    selected_indices = [int(i) - 1 for i in user_choice.split()]
                    for i in selected_indices:
                        if 0 <= i < len(all_found_media_items):
                            selected_items_to_download.append(all_found_media_items[i])
                        else:
                            print(f"Warning: Invalid item number {i + 1} skipped.")
                    # Apply overall limit if many items selected
                    selected_items_to_download = selected_items_to_download[:args.limit * len(args.platforms)]

                except ValueError:
                    print("Invalid input. No items selected for download.")

            downloaded_count_for_query = 0
            for item_to_dl in selected_items_to_download:
                if downloaded_count_for_query >= args.limit * len(args.platforms): # Global limit for this query
                    print("Reached download limit for this query.")
                    break
                # Pass query_specific_output_dir for this item's platform
                platform_specific_dl_dir = os.path.join(query_specific_output_dir, item_to_dl['platform'])

                if download_selected_item(item_to_dl, query_specific_output_dir, args.download_timeout):
                    downloaded_count_for_query +=1

            print(f"--- Interactive download for '{current_query}' complete. Downloaded {downloaded_count_for_query} items. ---")

        else: # --- Direct Download Phase (not interactive) ---
            print(f"--- Downloading media directly for '{current_query}' ---")
            if "giphy" in args.platforms:
                print("-" * 20)
                print(f"Processing Giphy for '{current_query}'...")
                giphy_output_subdir = os.path.join(query_specific_output_dir, "giphy")
                try:
                    m_type = args.media_type if args.media_type not in ["image", "audio"] else "all"
                    downloaded_count = search_giphy(current_query, args.limit, giphy_output_subdir, m_type, args.api_call_timeout)
                    if downloaded_count: print(f"Giphy: Downloaded {len(downloaded_count)} files.")
                    else: print(f"Giphy: No files downloaded for '{current_query}'.")
                except Exception as e: print(f"Giphy Error: {e}")
                print("-" * 20 + "\n"); time.sleep(1)

            if "morbotron" in args.platforms:
                print("-" * 20)
                print(f"Processing Morbotron for '{current_query}'...")
                morbotron_output_subdir = os.path.join(query_specific_output_dir, "morbotron")
                try:
                    # Morbotron is image specific
                    if args.media_type == "all" or args.media_type == "image":
                        downloaded_count = search_morbotron(current_query, args.limit, morbotron_output_subdir, "image", args.api_call_timeout)
                        if downloaded_count: print(f"Morbotron: Downloaded {len(downloaded_count)} files.")
                        else: print(f"Morbotron: No files downloaded for '{current_query}'.")
                    else: print(f"Morbotron: Skipping as it only supports 'image' or 'all' media type, not '{args.media_type}'.")
                except Exception as e: print(f"Morbotron Error: {e}")
                print("-" * 20 + "\n"); time.sleep(1)

            if "wikimedia" in args.platforms:
                print("-" * 20)
                print(f"Processing Wikimedia for '{current_query}'...")
                wikimedia_output_subdir = os.path.join(query_specific_output_dir, "wikimedia")
                try:
                    m_type = args.media_type if args.media_type != "sticker" else "all" # Wikimedia supports various types
                    downloaded_count = search_wikimedia(current_query, args.limit, wikimedia_output_subdir, m_type, args.api_call_timeout)
                    if downloaded_count: print(f"Wikimedia: Downloaded {len(downloaded_count)} files.")
                    else: print(f"Wikimedia: No files downloaded for '{current_query}'.")
                except Exception as e: print(f"Wikimedia Error: {e}")
                print("-" * 20 + "\n"); time.sleep(1)

            if "wikimedia_oauth" in args.platforms:
                print("-" * 20)
                print(f"Processing Wikimedia OAuth for '{current_query}'...")
                wikimedia_oauth_output_subdir = os.path.join(query_specific_output_dir, "wikimedia_oauth")
                try:
                    m_type = args.media_type if args.media_type != "sticker" else "all" # Wikimedia supports various types
                    downloaded_count = search_wikimedia_oauth_media(current_query, args.limit, wikimedia_oauth_output_subdir, m_type, args.api_call_timeout, args.download_timeout or WIKIMEDIA_OAUTH_TIMEOUT)
                    if downloaded_count: print(f"Wikimedia OAuth: Downloaded {len(downloaded_count)} files.")
                    else: print(f"Wikimedia OAuth: No files downloaded for '{current_query}'.")
                except Exception as e: print(f"Wikimedia OAuth Error: {e}")
                print("-" * 20 + "\n"); time.sleep(1)

            if "pixabay" in args.platforms:
                print("-" * 20)
                print(f"Processing Pixabay for '{current_query}'...")
                pixabay_output_subdir = os.path.join(query_specific_output_dir, "pixabay")
                try:
                    # Pixabay (this module) is video specific
                    if args.media_type == "all" or args.media_type == "video":
                        downloaded_count = search_pixabay_videos(current_query, args.limit, pixabay_output_subdir, api_timeout=args.api_call_timeout, download_timeout=args.download_timeout or PIXABAY_TIMEOUT)
                        if downloaded_count: print(f"Pixabay: Downloaded {len(downloaded_count)} files.")
                        else: print(f"Pixabay: No files downloaded for '{current_query}'.")
                    else: print(f"Pixabay: Skipping as it only supports 'video' or 'all' media type, not '{args.media_type}'.")
                except Exception as e: print(f"Pixabay Error: {e}")
                print("-" * 20 + "\n"); time.sleep(1)

            if "frinkiac" in args.platforms:
                print("-" * 20)
                print(f"Processing Frinkiac for '{current_query}'...")
                frinkiac_output_subdir = os.path.join(query_specific_output_dir, "frinkiac")
                try:
                    # Frinkiac is image specific
                    if args.media_type == "all" or args.media_type == "image":
                        downloaded_count = search_frinkiac_media(current_query, args.limit, frinkiac_output_subdir, api_timeout=args.api_call_timeout, download_timeout=args.download_timeout or FRINKIAC_TIMEOUT)
                        if downloaded_count: print(f"Frinkiac: Downloaded {len(downloaded_count)} files.")
                        else: print(f"Frinkiac: No files downloaded for '{current_query}'.")
                    else: print(f"Frinkiac: Skipping as it only supports 'image' or 'all' media type, not '{args.media_type}'.")
                except Exception as e: print(f"Frinkiac Error: {e}")
                print("-" * 20 + "\n"); time.sleep(1)

            if "mixkit" in args.platforms:
                print("-" * 20)
                print(f"Processing Mixkit for '{current_query}'...")
                mixkit_output_subdir = os.path.join(query_specific_output_dir, "mixkit")
                try:
                    # Mixkit (this module) is video specific
                    if args.media_type == "all" or args.media_type == "video":
                        downloaded_count = search_mixkit_videos(current_query, args.limit, mixkit_output_subdir, api_timeout=args.api_call_timeout, download_timeout=args.download_timeout or MIXKIT_TIMEOUT)
                        if downloaded_count: print(f"Mixkit: Downloaded {len(downloaded_count)} files.")
                        else: print(f"Mixkit: No files downloaded for '{current_query}'.")
                    else: print(f"Mixkit: Skipping as it only supports 'video' or 'all' media type, not '{args.media_type}'.")
                except Exception as e: print(f"Mixkit Error: {e}")
                print("-" * 20 + "\n"); time.sleep(1)

            # Add Comb.io direct download here if reactivated

    print("\nUnified media download process complete for all queries.")

if __name__ == "__main__":
    main()
