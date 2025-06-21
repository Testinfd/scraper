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
from morbotron_downloader import list_morbotron_media, DEFAULT_DOWNLOAD_TIMEOUT as MORBOTRON_TIMEOUT
from wikimedia_downloader import list_wikimedia_media, DEFAULT_DOWNLOAD_TIMEOUT as WIKIMEDIA_TIMEOUT
# from comb_io_downloader import list_comb_io_media # If it becomes available

app = Flask(__name__)
app.secret_key = os.urandom(24) # For session management, flash messages, etc.

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
    # if platform == "comb_io": return COMBIO_TIMEOUT # Placeholder
    return 10 # Generic default

@app.route('/', methods=['GET'])
def index():
    if GIPHY_API_KEY == "YOUR_GIPHY_API_KEY_HERE":
        giphy_warning = "Giphy API key is not set. Giphy searches will not work. Please set it in giphy_downloader.py."
    else:
        giphy_warning = None
    return render_template('index.html',
                           platforms=SUPPORTED_PLATFORMS,
                           media_types=["all", "image", "gif", "video", "audio", "sticker"],
                           giphy_warning=giphy_warning)

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
        elif platform == 'morbotron':
             # Morbotron is image only mostly
            mt = "image" if media_type not in ["image", "all"] else media_type
            if media_type == "all" or media_type == "image":
                platform_results = list_morbotron_media(query, limit_per_platform * 2, mt, api_call_timeout)
        elif platform == 'wikimedia':
            platform_results = list_wikimedia_media(query, limit_per_platform * 2, media_type, api_call_timeout)
        # elif platform == 'comb_io':
            # platform_results = list_comb_io_media(query, limit_per_platform * 2, media_type, api_call_timeout)

        all_results.extend(platform_results)
        time.sleep(0.5) # Small delay between platform API calls

    # Sanitize query for use as part of a directory name, if needed later for organizing downloads
    safe_query_name = "".join(c if c.isalnum() else "_" for c in query[:50]).strip('_') or "search"

    return render_template('results.html',
                           query=query,
                           results=all_results[:limit_per_platform * len(selected_platforms)], # Global limit on displayed items
                           limit_per_platform=limit_per_platform, # For information
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
