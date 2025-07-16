import requests
from urllib.parse import urlparse
import os
import mimetypes
from slugify import slugify
from structlog import get_logger
import random, secrets, string

logger = get_logger()


def random_alphanumeric(length=8):

    characters = string.ascii_letters + string.digits
    random_string = ''.join(secrets.choice(characters) for _ in range(length))
    return random_string


def get_mime_type(url):
    try:
        # Send a HEAD request to get headers without downloading the whole file
        response = requests.head(url, allow_redirects=True)
        
        # Check if the request was successful
        response.raise_for_status()
        
        # Extract the Content-Type header
        content_type = response.headers.get('Content-Type')
        
        # If Content-Type is not found, try to guess from the file extension
        if not content_type:
            extension = get_file_extension(url)
            content_type = mimetypes.guess_type(extension)[0]
        
        return content_type or "Unknown"
    except requests.RequestException as e:
        return f"Error: {str(e)}"

def get_file_extension(url):
    # Parse the URL and extract the path
    parsed_url = urlparse(url)
    path = parsed_url.path
    
    # Get the file extension (including the dot)
    file_extension = os.path.splitext(path)[1]
    
    return file_extension.lower()

# Initialize mimetypes database
mimetypes.init()

# Add some common audio and image MIME types that might be missing
additional_types = {
    '.mp3': 'audio/mpeg',
    '.wav': 'audio/wav',
    '.ogg': 'audio/ogg',
    '.flac': 'audio/flac',
    '.aac': 'audio/aac',
    '.webp': 'image/webp',
    '.tiff': 'image/tiff',
    '.svg': 'image/svg+xml'
}

for ext, mime_type in additional_types.items():
    mimetypes.add_type(mime_type, ext)


def generate_slug(name):
    try:
        name = f"{name} {random_alphanumeric()}"
        slug_name = slugify(name)
        return slug_name
    except Exception as e:
        logger.error("Failed to generate_slug",e = str(e),name = name)
