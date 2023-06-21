from asyncio.events import get_running_loop
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Optional, Dict, List

from yt_dlp import YoutubeDL
from yt_dlp.utils import MaxDownloadsReached

Opts = None | Dict[str, Optional[str] | int | List[Dict[str, str]]]
Info = Dict[str, Any]

_EXECUTOR = ThreadPoolExecutor(max_workers=100)


def _info(url: str, opts: Opts) -> Info:
    with YoutubeDL(opts) as ydl:
        return YoutubeDL.sanitize_info(ydl.extract_info(url, download=False))


def _download(info: Info, opts: Opts) -> None:
    try:
        with YoutubeDL(opts) as ydl:
            ydl.process_ie_result(info, download=True)
    except MaxDownloadsReached:
        return


async def youtube_info(url: str, opts: Opts) -> Info:
    return await get_running_loop().run_in_executor(_EXECUTOR, _info, url, opts)


async def youtube_download(info: Info, opts: Opts) -> None:
    return await get_running_loop().run_in_executor(_EXECUTOR, _download, info, opts)
