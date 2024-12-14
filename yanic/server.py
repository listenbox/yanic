import logging
import os
import time
from dataclasses import dataclass

import blacksheep
import uvicorn

from yanic.ytdl import Info, Opts, youtube_download, youtube_info

logging.basicConfig(level=logging.NOTSET)
logger = logging.getLogger("  ")


async def __log_res_time(req: blacksheep.Request, handler):
    start_sec = time.time()

    res: blacksheep.Response = await handler(req)

    end_sec = time.time()
    spent_ms = round((end_sec - start_sec) * 1000)

    logger.info(f"{req.method} {req.path} {res.status} - {spent_ms} ms")

    return res


app = blacksheep.Application()


@blacksheep.get("/health")
def __health() -> blacksheep.Response:
    return blacksheep.no_content()


@dataclass
class __InfoReq:
    url: str
    opts: Opts = None


@blacksheep.post("/info")
def __info(req: blacksheep.FromJSON[__InfoReq]) -> blacksheep.Response:
    try:
        info = youtube_info(req.value.url, req.value.opts)
        return blacksheep.json(info, status=200)
    except Exception as err:
        return blacksheep.text(str(err), status=422)


@blacksheep.get("/info")
def __get_info(url: blacksheep.FromQuery[str]) -> blacksheep.Response:
    try:
        info = youtube_info(url.value, opts=None)
        return blacksheep.json(info, status=200)
    except Exception as err:
        return blacksheep.text(str(err), status=422)


@dataclass
class __DownloadReq:
    info: Info
    opts: Opts = None


@blacksheep.post("/download")
def __download(req: blacksheep.FromJSON[__DownloadReq]) -> blacksheep.Response:
    try:
        youtube_download(req.value.info, req.value.opts)
        return blacksheep.json("ok", status=200)
    except Exception as err:
        logger.exception(
            req.value.info["webpage_url"]
            if "webpage_url" in req.value.info
            else req.value.info
        )
        return blacksheep.text(str(err), status=422)


app.middlewares.append(__log_res_time)


def main() -> None:
    port = int(os.environ.get("PORT", "8006"))
    uvicorn.run(
        app="yanic.server:app",
        port=port,
        limit_max_requests=25,
        access_log=False,
        log_level=logging.INFO,
        workers=25,
    )
