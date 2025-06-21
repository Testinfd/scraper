# Unified Media Downloader Tool

## Overview

This Python-based command-line tool allows you to search for and download media (images, GIFs, videos, audio) from various online platforms. It supports searching multiple platforms simultaneously, multiple keywords, filtering by media type, and offers both direct download and an interactive mode to select specific files.

## Features

*   **Multiple Platform Support**:
    *   Giphy (GIFs, Stickers, short Videos)
    *   Morbotron (TV Show Screencaps - e.g., The Simpsons, Futurama)
    *   Wikimedia Commons (Images, Videos, Audio)
    *   (Potentially Comb.io - currently facing API issues)
*   **Multiple Keyword Search**:
    *   Provide multiple search queries directly on the command line.
    *   Supply a text file containing a list of queries.
*   **Smart Filenaming**: Downloaded files are named using the query terms and original media identifiers for easy recognition.
*   **Media Type Filtering**: Specify the type of media you're looking for (e.g., `image`, `gif`, `video`, `audio`, `sticker`, or `all`).
*   **Interactive Mode**: List all found media items and choose interactively which ones to download.
*   **Organized Output**: Media is saved into a structured directory: `base_output_dir/query_term/platform_name/file.ext`.
*   **Configurable Timeouts**: Set timeouts for API calls and individual file downloads.
*   **Limit Control**: Specify the maximum number of items to download per query/platform.

## Prerequisites

*   Python 3.7+
*   `requests` library: Install it using pip:
    ```bash
    pip install requests
    ```

## Setup

1.  **Clone the repository (if applicable) or download the script files.**
    *   `media_downloader_tool.py` (main script)
    *   `giphy_downloader.py`
    *   `morbotron_downloader.py`
    *   `wikimedia_downloader.py`
    *   `comb_io_downloader.py` (optional, currently with issues)

2.  **Giphy API Key (Required for Giphy)**:
    *   To use Giphy, you need an API key. Visit the [Giphy Developers page](https://developers.giphy.com/) to create an app and get your API key.
    *   Open `giphy_downloader.py` and replace the placeholder `"YOUR_GIPHY_API_KEY_HERE"` with your actual API key:
        ```python
        GIPHY_API_KEY = "YOUR_ACTUAL_GIPHY_API_KEY"
        ```

## Usage

The main script is `media_downloader_tool.py`.

```bash
python media_downloader_tool.py [queries...] --platforms <platform_names...> [options]
```

### Arguments

*   `queries` (required unless `--query_file` is used): One or more search terms. If a term contains spaces, enclose it in quotes.
    *   Example: `"funny cat"` `dog`

*   `--platforms <platform_names...>` (required): A list of platforms to search.
    *   Choices: `giphy`, `morbotron`, `wikimedia`
    *   Example: `--platforms giphy wikimedia`

### Options

*   `--query_file <filepath>`: Path to a text file containing search queries, one query per line. This overrides queries provided directly on the command line.
    *   Example: `--query_file my_searches.txt`
    ```
    # my_searches.txt content:
    happy dance
    futurama bender
    historical map
    ```

*   `--limit <number>`: Maximum number of items to download per query, per platform (in direct mode), or total items to select from in interactive mode before applying further limits. Default: `5`.
    *   Example: `--limit 10`

*   `--output_dir <directory_path>`: Base directory to save downloaded media. Platform-specific and query-specific subfolders will be created within this directory. Default: `downloaded_media`.
    *   Example: `--output_dir ./my_collection`

*   `--media_type <type>`: Preferred type of media to download. Note that not all platforms support all types. Default: `all`.
    *   Choices: `all`, `image`, `gif`, `video`, `audio`, `sticker`
    *   `sticker`: Primarily for Giphy.
    *   `audio`: Primarily for Wikimedia Commons.
    *   `image`: For Morbotron (main type) and Wikimedia. Giphy GIFs can be considered images.
    *   Example: `--media_type video`

*   `--interactive`: If set, the tool will first list all found media items across the specified platforms for each query. You can then interactively choose which items to download by entering their numbers.
    *   Example: `--interactive`

*   `--download_timeout <seconds>`: Global timeout in seconds for downloading each media file. Overrides platform-specific default timeouts.
    *   Example: `--download_timeout 30` (wait up to 30s for a download)

*   `--api_call_timeout <seconds>`: Timeout in seconds for API search calls to each platform. Default: `10`.
    *   Example: `--api_call_timeout 15`

*   `-h`, `--help`: Show the help message and exit.

### Examples

1.  **Download 3 GIFs of "happy cats" from Giphy:**
    ```bash
    python media_downloader_tool.py "happy cats" --platforms giphy --media_type gif --limit 3
    ```

2.  **Download up to 5 images or videos related to "Futurama" from Morbotron and Wikimedia:**
    ```bash
    python media_downloader_tool.py "Futurama" --platforms morbotron wikimedia --media_type all --limit 5 --output_dir "tv_shows/futurama"
    ```

3.  **Interactively search for "space nebula" images on Wikimedia and "dancing alien" on Giphy, then choose what to download:**
    ```bash
    python media_downloader_tool.py "space nebula" "dancing alien" --platforms wikimedia giphy --media_type image --interactive
    ```
    *(Note: Giphy primarily serves GIFs/stickers; "image" for Giphy will fetch GIFs.)*

4.  **Use a query file to download various media:**
    ```bash
    python media_downloader_tool.py --query_file "search_terms.txt" --platforms morbotron wikimedia --limit 2
    ```
    *(Assuming `search_terms.txt` exists with one search term per line.)*

## Output Structure

Downloaded media will be saved in the following structure:

```
<output_dir>/
├── <sanitized_query_1>/
│   ├── <platform_1>/
│   │   └── <platform_query_id_timestamp.ext>
│   │   └── ...
│   ├── <platform_2>/
│   │   └── <platform_query_id_timestamp.ext>
│   │   └── ...
├── <sanitized_query_2>/
│   ├── <platform_1>/
│   │   └── ...
...
```

*   `<output_dir>`: The directory specified by `--output_dir` (default: `downloaded_media`).
*   `<sanitized_query_X>`: The search query, sanitized to be a valid directory name.
*   `<platform_X>`: Name of the platform (e.g., `giphy`, `morbotron`, `wikimedia`).
*   Filenames are generated to be descriptive, usually including the platform, parts of the query, and a unique ID or timestamp.

## Error Handling & Timeouts

*   The tool includes basic error handling for API requests and downloads (e.g., network issues, timeouts).
*   If a platform's API is unavailable or returns an error, the tool will report it and continue with other platforms/queries.
*   `--api_call_timeout` controls how long the script waits for a response from the platform's search API.
*   `--download_timeout` controls how long the script waits for an individual file to download. If not set, platform-specific defaults are used (typically 10-15 seconds).

## Future Enhancements (Potential)

*   **Comb.io Integration**: Resolve API access issues to re-enable Comb.io.
*   **Web Interface**: A simple web UI for easier searching and downloading (would require additional libraries like Flask/Streamlit and different deployment).
*   **Advanced Filtering**: More granular filtering options (e.g., by image size, video duration - if APIs support it).
*   **Configuration File**: For API keys and default settings.
*   **Unit Tests**: For increased reliability.

## Contributing

Contributions are welcome! If you'd like to add features, fix bugs, or improve documentation, please feel free to fork the repository and submit a pull request.

*(Diagrams are not easily representable in this text-based README. A visual workflow could be: User Input -> Main Tool -> Platform Lister -> User Selection (if interactive) -> Platform Downloader -> Files Saved)*