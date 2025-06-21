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

## Workflow Diagrams

### CLI Tool Workflow

```mermaid
graph TD
    A[User Executes media_downloader_tool.py with Args] --> B{Parse CLI Arguments};
    B --> C{Load Queries (Direct or from File)};
    C --> D[Loop Through Each Query];
    D --> E{Interactive Mode?};
    E -- Yes --> F[Fetch Media List from Platforms];
    F --> G[Display Found Items to User];
    G --> H[User Selects Items];
    H --> I[Download Selected Items];
    I --> J[Save to Output Directory];
    J --> K[Next Query or End];
    E -- No --> L[Call Direct Search & Download Functions for Platforms];
    L --> M[Download Items Directly];
    M --> J;
    D -- No More Queries --> K;
```

### Web Interface Workflow (Flask App)

```mermaid
graph TD
    subgraph User Browser
        U1[User Navigates to / URL]
        U2[User Submits Search Form to /search]
        U3[User Clicks Download Button on /results]
    end

    subgraph Flask Server (app.py)
        S1[Route: / - Renders index.html]
        S2[Route: /search - Handles Form]
        S3[Route: /download - Handles Download Request]

        S2A[Call list_X_media for selected platforms]
        S2B[Render results.html with found items]

        S3A[Call download_selected_item utility]
        S3B[File saved to server's download folder]
        S3C[Serve file using send_from_directory]
    end

    subgraph Downloader Modules
        DM1[list_X_media functions]
        DM2[download_file utilities]
    end

    U1 --> S1;
    U2 --> S2;
    S2 --> S2A;
    S2A --> DM1;
    DM1 --> S2A;
    S2A --> S2B;
    S2B --> U2_Results_PageDisplayed;

    U2_Results_PageDisplayed -- User clicks download --> U3;
    U3 --> S3;
    S3 --> S3A;
    S3A --> DM2;
    DM2 --> S3B;
    S3B --> S3C;
    S3C --> U3_File_Downloaded;
```

*(Diagrams are rendered by GitHub when viewing the README.md file.)*

## Web Interface Deployment

The provided web interface is a Flask (Python) application. Here are some important considerations for deployment:

*   **GitHub Pages Limitation**: GitHub Pages is designed for hosting **static websites** (HTML, CSS, JavaScript files). It cannot directly run Python backend code like a Flask application. Therefore, the Flask web interface in this project cannot be deployed directly to GitHub Pages.

*   **Suitable Hosting Platforms for Flask Apps**: To deploy the Flask web interface, you will need a hosting platform that supports Python web applications. Some popular options include:
    *   **PaaS (Platform as a Service)**:
        *   **Heroku**: Offers a free tier and is relatively easy to deploy Python/Flask apps.
        *   **PythonAnywhere**: Specifically designed for Python, also has a free tier for small projects.
        *   **Google App Engine**: Part of Google Cloud, scalable.
        *   **AWS Elastic Beanstalk**: Part of Amazon Web Services, highly scalable.
        *   **Microsoft Azure App Service**: Part of Microsoft Azure.
    *   **VPS (Virtual Private Server)**:
        *   Services like DigitalOcean, Linode, Vultr allow you to rent a virtual server where you can set up a Python environment, a web server (like Gunicorn or Waitress), and run your Flask app. This offers more control but requires more setup.
    *   **Containers**:
        *   You can containerize the Flask application using **Docker** and then deploy the container to services like AWS ECS, Google Kubernetes Engine (GKE), or Docker Hub with a cloud provider.

*   **General Deployment Steps (Conceptual)**:
    1.  **Prepare your app for production**:
        *   Use a production-grade WSGI server (e.g., Gunicorn, Waitress) instead of Flask's built-in development server (`app.run(debug=True)`).
        *   Set `DEBUG = False` in a production environment.
        *   Manage secret keys securely.
    2.  **Dependencies**: Ensure all dependencies are listed in a `requirements.txt` file (`pip freeze > requirements.txt`).
    3.  **Choose a hosting provider** from the options above (or others).
    4.  **Follow the provider's deployment guide**: Each platform will have specific instructions for deploying Python/Flask applications. This often involves:
        *   Pushing your code to a Git repository linked to the service (e.g., Heroku).
        *   Configuring environment variables (like API keys, if not hardcoded for personal use).
        *   Setting up a `Procfile` (common for Heroku, specifying how to run your app).

*   **Considerations for this Specific App**:
    *   **File Downloads**: The current web app saves downloaded media to the server's local filesystem (`instance/downloads`) and then serves them. Ensure your hosting solution provides persistent storage if you want these downloads to remain across deployments or server restarts. For ephemeral storage, this is fine, but files will be lost.
    *   **API Keys**: If deploying publicly, avoid committing API keys directly into your repository. Use environment variables provided by the hosting platform. (For this project, the Giphy API key is in `giphy_downloader.py`, which is not ideal for a public repo if it contains a real key).

This project's web interface is primarily intended for local use or deployment in a trusted environment due to its direct handling of file system operations and API keys.