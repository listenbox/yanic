from typing import Any, Dict, List, TypedDict

from yt_dlp import YoutubeDL
from yt_dlp.utils import MaxDownloadsReached


class Postprocessor(TypedDict, total=False):
    key: str


class YoutubeTab(TypedDict, total=False):
    approximate_date: str


class ExtractorArgs(TypedDict, total=False):
    youtubetab: YoutubeTab


class Opts(TypedDict, total=False):
    format: str
    extractor_retries: int
    proxy: str | None
    outtmpl: str
    max_downloads: int
    extract_flat: str
    playlistend: int
    postprocessors: List[Postprocessor]
    extractor_args: ExtractorArgs


class Info(TypedDict, total=False):
    webpage_url: str
    abr: int
    formats: List[Dict[str, Any]]


def youtube_info(url: str, opts: Opts) -> Info:
    with YoutubeDL(opts) as ydl:
        return YoutubeDL.sanitize_info(ydl.extract_info(url, download=False))


def youtube_download(info: Info, opts: Opts) -> None:
    try:
        with YoutubeDL(opts) as ydl:
            ydl.process_ie_result(info, download=True)
    except MaxDownloadsReached:
        # success
        return
