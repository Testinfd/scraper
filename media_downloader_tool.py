import argparse
import os

# Import functions from existing downloader scripts
from giphy_downloader import search_giphy
from morbotron_downloader import search_morbotron
# Comb.io is excluded due to API access issues:
# from comb_io_downloader import search_comb_io

def main():
    parser = argparse.ArgumentParser(description="Unified Media Downloader Tool.")
    parser.add_argument("query", type=str, help="Search query for media.")
    parser.add_argument(
        "--platforms",
        nargs="+",
        required=True,
        choices=["giphy", "morbotron"],
        help="List of platforms to search (e.g., giphy morbotron)."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Maximum number of items to download per platform."
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="downloaded_media",
        help="Base directory to save downloaded media. Platform-specific subfolders will be created."
    )

    args = parser.parse_args()

    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
        print(f"Created base output directory: {args.output_dir}")

    print(f"Starting media download process for query: '{args.query}'")
    print(f"Platforms: {', '.join(args.platforms)}")
    print(f"Limit per platform: {args.limit}")
    print(f"Base output directory: {args.output_dir}\n")

    if "giphy" in args.platforms:
        print("-" * 20)
        print("Processing Giphy...")
        giphy_output_subdir = os.path.join(args.output_dir, "giphy")
        if not os.path.exists(giphy_output_subdir):
            os.makedirs(giphy_output_subdir)

        try:
            print(f"Searching Giphy for '{args.query}' and downloading up to {args.limit} GIFs to '{giphy_output_subdir}'...")
            downloaded_giphy = search_giphy(args.query, args.limit, giphy_output_subdir)
            if downloaded_giphy:
                print(f"Giphy: Downloaded {len(downloaded_giphy)} files to {giphy_output_subdir}")
            else:
                print(f"Giphy: No files downloaded for '{args.query}'.")
        except Exception as e:
            print(f"Giphy: An error occurred: {e}")
        print("-" * 20 + "\n")

    if "morbotron" in args.platforms:
        print("-" * 20)
        print("Processing Morbotron...")
        morbotron_output_subdir = os.path.join(args.output_dir, "morbotron")
        if not os.path.exists(morbotron_output_subdir):
            os.makedirs(morbotron_output_subdir)

        # Note: Morbotron queries are typically quotes. The generic 'query' arg will be used.
        # Users should be mindful of this when querying Morbotron.
        try:
            print(f"Searching Morbotron for '{args.query}' and downloading up to {args.limit} screencaps to '{morbotron_output_subdir}'...")
            downloaded_morbotron = search_morbotron(args.query, args.limit, morbotron_output_subdir)
            if downloaded_morbotron:
                print(f"Morbotron: Downloaded {len(downloaded_morbotron)} files to {morbotron_output_subdir}")
            else:
                print(f"Morbotron: No files downloaded for '{args.query}'.")
        except Exception as e:
            print(f"Morbotron: An error occurred: {e}")
        print("-" * 20 + "\n")

    # Comb.io section would be here if it were functional
    # if "comb_io" in args.platforms:
    #     print("-" * 20)
    #     print("Processing Comb.io...")
    #     comb_io_output_subdir = os.path.join(args.output_dir, "comb_io")
    #     # ...
    #     print("-" * 20 + "\n")

    print("Unified media download process complete.")

if __name__ == "__main__":
    main()
