import logging
import os
import time
from dataclasses import dataclass

import uvicorn
import blacksheep

from yanic.ytdl import youtube_info, youtube_download, Opts, Info

logging.basicConfig(level=logging.NOTSET)
logger = logging.getLogger("  ")


async def _log_res_time(req: blacksheep.Request, handler):
    start_sec = time.time()

    res: blacksheep.Response = await handler(req)

    end_sec = time.time()
    spent_ms = round((end_sec - start_sec) * 1000)

    logger.info(f"{req.method} {req.path} {res.status} - {spent_ms} ms")

    return res


app = blacksheep.Application()


@blacksheep.get("/health")
def _health() -> blacksheep.Response:
    return blacksheep.no_content()


@dataclass
class _InfoReq:
    url: str
    opts: Opts = None


@blacksheep.post("/info")
def _info(req: blacksheep.FromJSON[_InfoReq]) -> blacksheep.Response:
    try:
        info = youtube_info(req.value.url, req.value.opts)
        return blacksheep.json(info, status=200)
    except Exception as err:
        return blacksheep.text(str(err), status=422)


@blacksheep.get("/info")
def _get_info(url: blacksheep.FromQuery[str]) -> blacksheep.Response:
    try:
        info = youtube_info(url.value, opts=None)
        return blacksheep.json(info, status=200)
    except Exception as err:
        return blacksheep.text(str(err), status=422)


@dataclass
class _DownloadReq:
    info: Info
    opts: Opts = None


@blacksheep.post("/download")
def _download(req: blacksheep.FromJSON[_DownloadReq]) -> blacksheep.Response:
    try:
        youtube_download(req.value.info, req.value.opts)
        return blacksheep.json("ok", status=200)
    except Exception as err:
        return blacksheep.text(str(err), status=422)


app.middlewares.append(_log_res_time)


def main() -> None:
    port = int(os.environ.get('PORT', '8006'))
    uvicorn.run(
        app="yanic.server:app",
        port=port,
        limit_max_requests=10_000,
        access_log=False,
        log_level=logging.INFO,
        workers=12,
    )
