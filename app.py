from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import os
import sys
import time # For delays or unique naming if needed

# Add the current directory to sys.path to allow importing local modules
sys.path.append(os.path.dirname(os.path.realpath(__file__)))

from media_downloader_tool import (
    SUPPORTED_PLATFORMS,
    download_selected_item, # Re-usable for downloading specific items
    # Direct search_X functions might be too CLI-oriented with their print statements.
    # We'll primarily use list_X_media functions and then download_selected_item.
)

# Import listing functions from individual downloaders
from giphy_downloader import list_giphy_media, GIPHY_API_KEY, DEFAULT_DOWNLOAD_TIMEOUT as GIPHY_TIMEOUT
from morbotron_scraper import list_morbotron_media, DEFAULT_DOWNLOAD_TIMEOUT as MORBOTRON_TIMEOUT
from wikimedia_scraper import list_wikimedia_media, DEFAULT_DOWNLOAD_TIMEOUT as WIKIMEDIA_TIMEOUT
from pixabay_scraper import list_pixabay_videos, PIXABAY_API_KEY, DEFAULT_DOWNLOAD_TIMEOUT as PIXABAY_TIMEOUT
from frinkiac_scraper import list_frinkiac_media, DEFAULT_DOWNLOAD_TIMEOUT as FRINKIAC_TIMEOUT
from mixkit_scraper import list_mixkit_videos, DEFAULT_DOWNLOAD_TIMEOUT as MIXKIT_TIMEOUT
from wikimedia_oauth_scraper import list_wikimedia_oauth_media, DEFAULT_DOWNLOAD_TIMEOUT as WIKIMEDIA_OAUTH_TIMEOUT
# from comb_io_scraper import list_comb_io_media # If it becomes available

app = Flask(__name__)
app.secret_key = os.urandom(24) # For session management, flash messages, etc.

# Jinja filter for human-readable file sizes
def human_readable_size(size_bytes, precision=1):
    """Converts bytes to a human-readable string (KB, MB, GB)."""
    if size_bytes is None or not isinstance(size_bytes, (int, float)) or size_bytes < 0:
        return "N/A"
    if size_bytes == 0:
        return "0 B"

    units = ['B', 'KB', 'MB', 'GB', 'TB']
    power = 0
    temp_size = float(size_bytes)

    while temp_size >= 1024 and power < len(units) -1 :
        temp_size /= 1024
        power += 1

    return f"{temp_size:.{precision}f} {units[power]}"

app.jinja_env.filters['human_readable_size'] = human_readable_size

# Configuration
# Using a relative path for downloads within the app's instance folder or a dedicated static subfolder
DOWNLOAD_BASE_DIR = os.path.join(app.instance_path, 'downloads')
if not os.path.exists(DOWNLOAD_BASE_DIR):
    os.makedirs(DOWNLOAD_BASE_DIR)

app.config['DOWNLOAD_FOLDER'] = DOWNLOAD_BASE_DIR


# Helper to get platform default timeout - useful for UI display or logic
def get_platform_default_timeout(platform):
    if platform == "giphy": return GIPHY_TIMEOUT
    if platform == "morbotron": return MORBOTRON_TIMEOUT
    if platform == "wikimedia": return WIKIMEDIA_TIMEOUT
    if platform == "wikimedia_oauth": return WIKIMEDIA_OAUTH_TIMEOUT
    if platform == "pixabay": return PIXABAY_TIMEOUT
    if platform == "frinkiac": return FRINKIAC_TIMEOUT
    if platform == "mixkit": return MIXKIT_TIMEOUT
    # if platform == "comb_io": return COMBIO_TIMEOUT # Placeholder
    return 10 # Generic default

@app.route('/', methods=['GET'])
def index():
    warnings = []
    if GIPHY_API_KEY == "YOUR_GIPHY_API_KEY_HERE":
        warnings.append("Giphy API key is not set in giphy_downloader.py. Giphy searches will not work.")
    if PIXABAY_API_KEY == "YOUR_PIXABAY_API_KEY_HERE":
        warnings.append("Pixabay API key is not set in pixabay_downloader.py. Pixabay searches will not work.")

    return render_template('index.html',
                           platforms=SUPPORTED_PLATFORMS, # SUPPORTED_PLATFORMS from media_downloader_tool.py will have all
                           media_types=["all", "image", "gif", "video", "audio", "sticker"],
                           warnings=warnings if warnings else None)

@app.route('/search', methods=['POST'])
def search():
    query = request.form.get('query')
    selected_platforms = request.form.getlist('platforms')
    media_type = request.form.get('media_type', 'all')
    limit_per_platform = int(request.form.get('limit', 5))
    # Timeouts from form - assuming they are provided as strings
    api_call_timeout = int(request.form.get('api_call_timeout', 10))
    # download_timeout = int(request.form.get('download_timeout', get_platform_default_timeout('generic'))) # This needs to be per item

    if not query:
        return "Error: Search query is required.", 400
    if not selected_platforms:
        return "Error: At least one platform must be selected.", 400

    all_results = []
    # For web, better to fetch a decent number for display then let user pick (or paginate)
    # The 'limit' from UI can mean items to *display* per platform before selection,
    # or items to *download* if it's direct.
    # Let's assume 'limit' is for how many items to list from each source initially.

    for platform in selected_platforms:
        platform_results = []
        if platform == 'giphy':
            if GIPHY_API_KEY != "YOUR_GIPHY_API_KEY_HERE":
                platform_results = list_giphy_media(query, limit_per_platform * 2, media_type, api_call_timeout)
            else:
                print("Skipping Giphy search in web UI: API key not set.")
        elif platform == 'morbotron':
            mt = "image" if media_type not in ["image", "all"] else media_type
            if media_type == "all" or media_type == "image":
                platform_results = list_morbotron_media(query, limit_per_platform * 2, mt, api_call_timeout)
        elif platform == 'wikimedia':
            platform_results = list_wikimedia_media(query, limit_per_platform * 2, media_type, api_call_timeout)
        elif platform == 'wikimedia_oauth':
            platform_results = list_wikimedia_oauth_media(query, limit_per_platform * 2, media_type, api_call_timeout)
        elif platform == 'pixabay':
            if PIXABAY_API_KEY != "YOUR_PIXABAY_API_KEY_HERE":
                if media_type == "all" or media_type == "video":
                    platform_results = list_pixabay_videos(query, limit_per_platform * 2, api_timeout=api_call_timeout)
                # else: print(f"WebUI: Pixabay skipped, wrong media type '{media_type}'")
            else:
                print("Skipping Pixabay search in web UI: API key not set.")
        elif platform == 'frinkiac':
            if media_type == "all" or media_type == "image": # Frinkiac is image specific
                platform_results = list_frinkiac_media(query, limit_per_platform * 2, api_timeout=api_call_timeout)
            # else: print(f"WebUI: Frinkiac skipped, wrong media type '{media_type}'")
        elif platform == 'mixkit':
            if media_type == "all" or media_type == "video": # Mixkit is video specific (for this downloader)
                platform_results = list_mixkit_videos(query, limit_per_platform * 2, api_timeout=api_call_timeout)
            # else: print(f"WebUI: Mixkit skipped, wrong media type '{media_type}'")
        # elif platform == 'comb_io':
            # list_call_result = list_comb_io_media(query, limit_per_platform * 2, media_type, api_call_timeout)

        # Store structured results including errors/status
        current_platform_data = {"platform_name": platform, "items": [], "error": None, "status_message": None}
        if isinstance(platform_results, dict): # New return type
            current_platform_data["items"] = platform_results.get("items", [])
            current_platform_data["error"] = platform_results.get("error")
            current_platform_data["status_message"] = platform_results.get("status_message")
        elif isinstance(platform_results, list): # Old return type (fallback, should be phased out)
             current_platform_data["items"] = platform_results

        all_results.append(current_platform_data) # all_results is now a list of these dicts

        # Only extend the flat list for display if items exist, for the old results.html compatibility (will change)
        # For now, let's build a flat list for the results display, and a separate one for status
        # This will be simplified when results.html is updated.
        # flat_item_list.extend(current_platform_data["items"])

        time.sleep(0.5) # Small delay between platform API calls

    # Sanitize query for use as part of a directory name, if needed later for organizing downloads
    safe_query_name = "".join(c if c.isalnum() else "_" for c in query[:50]).strip('_') or "search"

    # Consolidate items from all platforms for display, respecting limit_per_platform for each
    display_items = []
    for res_block in all_results:
        items_from_platform = res_block.get('items', [])
        # Each platform's result (items_from_platform) might have up to (limit_per_platform * 2) items
        # We take up to limit_per_platform from these for final display from this specific platform
        display_items.extend(items_from_platform[:limit_per_platform])

    # The existing overall slice limit_per_platform * len(selected_platforms)
    # can still act as a total cap if desired, though now display_items is built
    # more equitably. If limit_per_platform=5 and 6 platforms selected,
    # display_items could have up to 30 items. The slice would be [:30], so it's consistent.
    # If the goal is strictly "up to X items from each platform, then cap total", this is fine.
    # If the goal was just "up to X items from each platform, show all of them", then the slice
    # may not be strictly needed if len(display_items) is already desired_max_items.
    # Let's keep the slice for now as it defines a clear overall maximum.

    return render_template('results.html',
                           query=query,
                           results_data=all_results, # Pass the structured data for status messages
                           display_items=display_items[:limit_per_platform * len(selected_platforms)], # Apply overall display limit
                           limit_per_platform=limit_per_platform, # For reference or other uses in template if any
                           safe_query_name=safe_query_name)


@app.route('/download', methods=['POST'])
def download():
    item_url = request.form.get('url')
    item_filename = request.form.get('filename')
    item_platform = request.form.get('platform')
    item_title = request.form.get('title') # For display
    item_type = request.form.get('type')   # For display

    # The query name could be part of the download path if we want to organize by query
    # For simplicity here, downloads from web will go into instance_path/downloads/platform/filename
    # query_context_dir = request.form.get('query_context_dir', 'general_downloads') # from hidden field if needed

    if not all([item_url, item_filename, item_platform]):
        return "Error: Missing item details for download.", 400

    # Use a fixed base output directory for web downloads for now
    # Each download will be in DOWNLOAD_BASE_DIR / platform_name / query_name / filename
    # For simplicity, let's put it in DOWNLOAD_BASE_DIR / platform / filename

    # Create the item object expected by download_selected_item
    item_details = {
        'url': item_url,
        'filename': item_filename,
        'platform': item_platform,
        'title': item_title, # Not strictly needed by download_selected_item but good to have
        'type': item_type    # Same as above
    }

    # Download timeout: use platform default for now, or could add a form field for it
    # For now, download_selected_item has its own logic for this using platform defaults.
    # We could pass a global override if we had one from the search form for downloads.
    # Let's assume no override for now, so it uses platform defaults.
    # download_timeout_override = request.form.get('download_timeout_override')
    # download_timeout_override = int(download_timeout_override) if download_timeout_override else None

    # The `download_selected_item` from media_downloader_tool saves to its own constructed path
    # based on the item's platform and filename. We need to ensure its base_output_dir is set correctly.
    # `download_selected_item` expects `base_output_dir` and it creates `base_output_dir/platform_name/`

    # For web, we want to serve the file, so it should be in a place Flask can access.
    # Let's make download_selected_item save it to app.config['DOWNLOAD_FOLDER'] structure.
    # The current `download_selected_item` in media_downloader_tool.py already does this:
    # platform_output_dir = os.path.join(base_output_dir, item['platform'])

    # Call the download function. It will save to app.config['DOWNLOAD_FOLDER']/platform/filename
    download_path = download_selected_item(item_details, app.config['DOWNLOAD_FOLDER'])

    if download_path:
        # Provide a link to download the file from the server's static/download directory
        # The file is now at app.config['DOWNLOAD_FOLDER']/item_platform/item_filename
        # We need to serve it. `send_from_directory` is good for this.
        # The path for send_from_directory is relative to the directory specified.
        # So, directory is app.config['DOWNLOAD_FOLDER']/item_platform
        # and filename is item_filename
        platform_specific_download_folder = os.path.join(app.config['DOWNLOAD_FOLDER'], item_platform)

        # Ensure the directory exists if download_selected_item didn't create it (it should)
        # if not os.path.exists(platform_specific_download_folder):
        #    os.makedirs(platform_specific_download_folder)

        # Check if file exists after download_selected_item reports success
        actual_file_path = os.path.join(platform_specific_download_folder, item_filename)
        if os.path.exists(actual_file_path):
             return send_from_directory(directory=platform_specific_download_folder,
                                       path=item_filename,  # Changed from filename= to path= for Flask 2.x
                                       as_attachment=True)
        else:
            # This case should ideally not happen if download_path was returned.
            return "Error: File not found on server after download attempt. Path: " + actual_file_path, 404

    else:
        return f"Error: Failed to download '{item_title}'.", 500


if __name__ == '__main__':
    # Create instance path if it doesn't exist
    if not os.path.exists(app.instance_path):
        os.makedirs(app.instance_path)
    app.run(debug=True)
