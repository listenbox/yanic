from typing import Any, Optional, Dict, List

from yt_dlp import YoutubeDL
from yt_dlp.utils import MaxDownloadsReached

Opts = None | Dict[str, Optional[str] | int | List[Dict[str, str]]]
Info = Dict[str, Any]


def youtube_info(url: str, opts: Opts) -> Info:
    with YoutubeDL(opts) as ydl:
        return YoutubeDL.sanitize_info(ydl.extract_info(url, download=False))


def youtube_download(info: Info, opts: Opts) -> None:
    try:
        with YoutubeDL(opts) as ydl:
            ydl.process_ie_result(info, download=True)
    except MaxDownloadsReached:
        return
