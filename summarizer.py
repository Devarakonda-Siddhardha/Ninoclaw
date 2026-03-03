"""
URL and YouTube summarizer for Ninoclaw
"""
import re
import requests
from html.parser import HTMLParser


def extract_urls(text):
    """Extract all URLs from a message"""
    return re.findall(r'https?://[^\s]+', text)


def is_youtube(url):
    return re.search(r'(youtube\.com/watch|youtu\.be/)', url) is not None


def get_youtube_transcript(url):
    """Fetch transcript from a YouTube video"""
    from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled

    # Extract video ID
    match = re.search(r'(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})', url)
    if not match:
        return None, "Couldn't extract video ID from URL."

    video_id = match.group(1)
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        text = " ".join(entry["text"] for entry in transcript)
        return text[:12000], None  # Limit to avoid token overflow
    except (NoTranscriptFound, TranscriptsDisabled):
        return None, "No transcript available for this video (disabled or not generated)."
    except Exception as e:
        return None, f"Failed to fetch transcript: {e}"


class _TextExtractor(HTMLParser):
    """Simple HTML → plain text extractor"""
    def __init__(self):
        super().__init__()
        self.text_parts = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'nav', 'footer', 'header'):
            self._skip = True

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'nav', 'footer', 'header'):
            self._skip = False

    def handle_data(self, data):
        if not self._skip:
            stripped = data.strip()
            if stripped:
                self.text_parts.append(stripped)

    def get_text(self):
        return " ".join(self.text_parts)


def get_url_content(url):
    """Fetch and extract readable text from any URL"""
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        parser = _TextExtractor()
        parser.feed(resp.text)
        text = parser.get_text()
        return text[:12000], None  # Limit tokens
    except requests.RequestException as e:
        return None, f"Failed to fetch URL: {e}"


def build_summary_prompt(content, url, is_yt=False):
    source = "YouTube video" if is_yt else "webpage"
    return (
        f"Please summarize the following {source} content from {url}.\n"
        f"Give a clear, concise summary with key points. Use bullet points where helpful.\n\n"
        f"Content:\n{content}"
    )
