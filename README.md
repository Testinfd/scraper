# Unified Media Downloader Tool

## What is this?

This tool helps you search for and download media (like images, GIFs, and videos) from various online sources using a command-line interface (CLI) or a simple web page. Think of it as a personal assistant for finding and saving media for your projects or collection!

## Supported Sources

You can fetch media from:

*   **Giphy**: For GIFs, Stickers, and short Videos.
*   **Morbotron**: For screencaps from shows like The Simpsons and Futurama.
*   **Wikimedia Commons**: For a vast collection of images, videos, and audio.
*   **Pixabay**: For free stock videos.
*   **Frinkiac**: For The Simpsons screencaps searchable by quote.
*   **Mixkit**: For stock videos.
*   *(Comb.io is currently under maintenance for this tool).*

## Key Features

*   **One Tool, Many Sources**: Search Giphy, Morbotron, Wikimedia, etc., all at once.
*   **Command-Line Power**: Use it from your terminal for scripting and automation.
*   **Simple Web Interface**: Prefer clicking buttons? There's a basic web page for that too.
*   **Search Your Way**: Use multiple keywords or even a list of queries from a file.
*   **Filter by Type**: Look specifically for `image`, `gif`, `video`, `audio`, or `sticker`.
*   **Choose What You Download**: An interactive mode lets you preview and select items before downloading.
*   **Organized Downloads**: Files are saved neatly into folders based on your search and the source.
*   **Safe Filenames**: Downloaded files get sensible names.

## Setup: Getting Started

Follow these steps to get the tool running on your computer.

1.  **Get the Code:**
    *   If you have `git` installed, clone the repository:
        ```bash
        git clone <repository_url>
        cd <repository_directory>
        ```
    *   Alternatively, download the project files as a ZIP and extract them. You'll need all the `.py` files and the `templates` folder.

2.  **Python Version:**
    *   Make sure you have Python 3.7 or newer installed.

3.  **Install Required Libraries:**
    *   The project uses a few external Python libraries. These are listed in `requirements.txt`.
    *   It's highly recommended to use a Python virtual environment to keep dependencies for this project separate from others on your system.
        ```bash
        # Create a virtual environment (e.g., named 'venv')
        python -m venv venv

        # Activate it:
        # On Windows:
        # venv\Scripts\activate
        # On macOS/Linux:
        # source venv/bin/activate
        ```
    *   Once your virtual environment is active, install the libraries:
        ```bash
        pip install -r requirements.txt
        ```
        This will install `Flask`, `requests`, and `BeautifulSoup4`.

4.  **API Keys (Important!):**
    *   Some services require an API key to let you access their content.
    *   **Giphy API Key**:
        *   Go to the [Giphy Developers page](https://developers.giphy.com/) and create an account (or log in) to get an API key.
        *   **Set this key as an environment variable named `GIPHY_API_KEY`**.
            *   **macOS/Linux (temporary for current session):**
                ```bash
                export GIPHY_API_KEY="YOUR_ACTUAL_GIPHY_API_KEY"
                ```
                (To make it permanent, add this line to your shell's profile file, like `~/.bashrc` or `~/.zshrc`, then source it or open a new terminal.)
            *   **Windows (temporary for current session in Command Prompt):**
                ```bash
                set GIPHY_API_KEY="YOUR_ACTUAL_GIPHY_API_KEY"
                ```
            *   **Windows (temporary for current session in PowerShell):**
                ```bash
                $env:GIPHY_API_KEY="YOUR_ACTUAL_GIPHY_API_KEY"
                ```
                (For permanent setting on Windows, search for "environment variables" in system settings.)
        *   The Giphy part of the tool will not work without this key. The provided key `fqVxYjMvmpUS6ltig5MEfv0vMBP6HzFn` can be used for testing.
    *   **Pixabay API Key**:
        *   Visit the [Pixabay API page](https://pixabay.com/api/docs/) to get a free API key.
        *   **Set this key as an environment variable named `PIXABAY_API_KEY`**.
            *   Follow the same method as for the Giphy key (e.g., `export PIXABAY_API_KEY="YOUR_KEY"`).
        *   Pixabay search will not work without this.
    *   **Other Services (Frinkiac, Morbotron, Mixkit, Wikimedia):** These currently use web scraping or public APIs that don't require a personal key setup from your side.

5.  **File List (for reference):**
    *   `media_downloader_tool.py`: The main command-line script.
    *   `app.py`: The Flask web application.
    *   `templates/`: Folder containing HTML for the web app (`index.html`, `results.html`).
    *   `giphy_downloader.py`: Handles Giphy.
    *   `morbotron_scraper.py`: Handles Morbotron.
    *   `wikimedia_scraper.py`: Handles Wikimedia Commons.
    *   `pixabay_scraper.py`: Handles Pixabay.
    *   `frinkiac_scraper.py`: Handles Frinkiac.
    *   `mixkit_scraper.py`: Handles Mixkit.
    *   `comb_io_scraper.py`: (Currently not fully functional).
    *   `requirements.txt`: Lists Python libraries needed.

## How to Use

You have two ways to use this tool:

### 1. Command-Line Interface (CLI)

Open your terminal or command prompt. If you created a virtual environment, make sure it's activated.

The basic command structure is:
```bash
python media_downloader_tool.py "your search query" --platforms <platform1> <platform2> [options]
```

**Arguments & Options:**

*   `queries` (required unless `--query_file` is used): The search term(s). If a term has spaces, put it in quotes (e.g., `"funny cat"`). You can list multiple queries.
*   `--platforms <platform_names...>` (required): Which sites to search.
    *   Choices: `giphy`, `morbotron`, `wikimedia`, `pixabay`, `frinkiac`, `mixkit`
    *   Example: `--platforms giphy wikimedia`
*   `--query_file <filepath>`: Path to a text file with one search query per line.
    *   Example: `--query_file my_searches.txt`
*   `--limit <number>`: Max items to download per query/platform. Default: `5`.
*   `--output_dir <directory_path>`: Where to save files. Default: `downloaded_media`.
    *   Example: `--output_dir ./my_cool_media`
*   `--media_type <type>`: Type of media. Default: `all`.
    *   Choices: `all`, `image`, `gif`, `video`, `audio`, `sticker`
*   `--interactive`: Shows a list of found items and asks you to pick which ones to download.
*   `--download_timeout <seconds>`: Max time (seconds) to wait for a single file to download.
*   `--api_call_timeout <seconds>`: Max time (seconds) to wait for a response from a platform's search. Default: `10`.
*   `-h`, `--help`: Shows all commands and options.

**CLI Examples:**

1.  **Download 3 GIFs of "happy cats" from Giphy:**
    ```bash
    python media_downloader_tool.py "happy cats" --platforms giphy --media_type gif --limit 3
    ```

2.  **Search Morbotron and Frinkiac for "excellent" quotes/images, interactively choose 2:**
    ```bash
    python media_downloader_tool.py "excellent" --platforms morbotron frinkiac --interactive --limit 2
    ```

3.  **Download videos related to "nature" from Pixabay and Mixkit, save to `my_videos` folder:**
    ```bash
    python media_downloader_tool.py "nature" --platforms pixabay mixkit --media_type video --output_dir my_videos
    ```

### 2. Web Interface

This provides a simpler, graphical way to search and download.

1.  **Start the Web App:**
    *   Open your terminal, navigate to the project directory, and activate your virtual environment if you have one.
    *   Run:
        ```bash
        python app.py
        ```
    *   You should see a message like `* Running on http://127.0.0.1:5000/`.

2.  **Use in Your Browser:**
    *   Open your web browser (like Chrome, Firefox, etc.) and go to the address shown (usually `http://127.0.0.1:5000`).
    *   You'll see a page where you can:
        *   Type your search query.
        *   Select which platforms to search.
        *   Choose the media type.
        *   Set how many results to show per platform.
        *   Click "Search".
    *   The results will appear on a new page. Each item will have a title, a preview (if possible), and information about its source.
    *   Click the "Download" button next to any item you want to save. Your browser will download it.

**Where do files from the web interface go?**
When you click download in the web interface, the file is first downloaded to a temporary folder on the server (the computer running `app.py`, inside a folder like `instance/downloads`) and then sent to your browser. Your browser will typically save it to your default "Downloads" folder.

## Output Structure (CLI)

When using the command-line tool, downloaded media is saved like this:

```
<output_dir>/
├── <your_search_query_as_folder_name>/
│   ├── <platform_name>/
│   │   └── <filename.ext>
│   │   └── ...
│   ├── <another_platform_name>/
│   │   └── <filename.ext>
...
```
*   `<output_dir>`: The folder you specified with `--output_dir` (or `downloaded_media` by default).
*   `<your_search_query_as_folder_name>`: The search term, made safe for folder names.
*   `<platform_name>`: e.g., `giphy`, `morbotron`.

## Troubleshooting & Notes

*   **No Giphy/Pixabay results?** Double-check your `GIPHY_API_KEY` and `PIXABAY_API_KEY` environment variables are correctly set and that the keys themselves are valid.
*   **Web Scraping**: Services like Frinkiac, Morbotron, and Mixkit are accessed by web scraping. If these sites change their structure, the tool might stop working for them until it's updated.
*   **Timeouts**: If you're on a slow connection, you might need to increase `--download_timeout` or `--api_call_timeout`.
*   **Flask Web App is for Local Use**: The `app.py` web interface is mainly for running on your own computer. Deploying it to a public web server requires additional steps and security considerations.

## Contributing

Found a bug or have an idea for an improvement? Contributions are welcome!

---

This README aims to be simple and direct. Let me know if anything is unclear!
