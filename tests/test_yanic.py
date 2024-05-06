import asyncio
import json
import os
from multiprocessing import Process
from random import randrange
from typing import Optional

import pytest
import uvicorn
from aiohttp import ClientSession

from responsible import OpenAPI, RRequest, Responsible


def _start_server(port: int):
    uvicorn.run(app="yanic.server:app", port=port, access_log=False, workers=4)


@pytest.fixture(scope="module")
def server() -> int:
    port = randrange(8000, 9000)

    proc = Process(target=_start_server, args=[port])
    proc.start()

    yield port

    proc.terminate()


@pytest.fixture(scope='module')
async def client(server) -> ClientSession:
    async with ClientSession(f"http://localhost:{server}") as sess:
        for _ in range(10):
            try:
                await sess.get("/health")
                break
            except Exception:
                await asyncio.sleep(0.1)
        yield sess


@pytest.fixture(scope='module')
def openapi() -> OpenAPI:
    with open(next(filter(os.path.exists, ["openapi.json", "../openapi.json"]))) as f:
        return json.load(f)


@pytest.fixture(scope='module')
def responsible(client, openapi) -> Responsible:
    return Responsible(client, openapi)


SKIP_ANDROID = {
    'youtube': {
        'player_client': ['ios', 'web'],
    },
}


def info_opts(ext: str, proxy: Optional[str] = None):
    return {
        "format": f"bestaudio[ext={ext}]/best[ext={ext}]",
        "proxy": proxy,
        "extractor_retries": 0,
        'extractor_args': SKIP_ANDROID,
    }


def download_opts(file: str, proxy: Optional[str] = None):
    _, ext = os.path.splitext(file)
    ext = ext[1:]

    return {
        "format": f"bestaudio[ext={ext}]/best[ext={ext}]",
        'postprocessors': [
            {
                'key': 'FFmpegExtractAudio',
            }
        ],
        "outtmpl": file,
        "max_downloads": 1,
        "proxy": proxy,
        "extractor_retries": 0,
        'extractor_args': SKIP_ANDROID,
    }


def playlist_opts(proxy: Optional[str] = None, limit: int = 500):
    return {
        "proxy": proxy,
        "extract_flat": "in_playlist",
        "playlistend": limit,
        "extractor_retries": 0,
        "extractor_args": {
            "youtubetab": {"approximate_date": "True"},
        },
    }


@pytest.mark.asyncio_cooperative
async def test_incomplete_youtube_id(responsible):
    req = RRequest("POST", "/info",
                   json={"url": "https://www.youtube.com/watch?v=bigXuLv7lN", "opts": info_opts("m4a")})
    res = await responsible.check(req, status=422)

    assert "Incomplete YouTube ID" in await res.text()


@pytest.mark.asyncio_cooperative
async def test_has_abr(responsible):
    req = RRequest("POST", "/info", json={
        "url": "https://www.youtube.com/watch?v=bigXuLv7lNE",
        "opts": info_opts("m4a")
    })
    res = await responsible.check(req, status=200)

    info = await res.json()
    assert "abr" in info


@pytest.mark.asyncio_cooperative
async def test_instagram_tv(responsible):
    req = RRequest("POST", "/info", json={"url": "https://www.instagram.com/tv/CCwKLP8oAbB", "opts": info_opts("mp4")})
    res = await responsible.check(req, status=200)
    info = await res.json()
    assert len(info["formats"]) > 0


@pytest.mark.asyncio_cooperative
async def test_invalid_download(responsible):
    req = RRequest("POST", "/download", json={"info": {}, "opts": {}})
    res = await responsible.check(req, status=422)
    assert 'extractor' in await res.text()


@pytest.mark.asyncio_cooperative
async def test_download(tmp_path_factory, responsible):
    tmp_path = tmp_path_factory.mktemp("tmp")
    resp = await responsible.check(
        RRequest(
            "POST",
            "/info",
            json={"url": "https://www.youtube.com/watch?v=UO_QuXr521I", "opts": info_opts(ext="m4a")},
        ),
        status=200
    )

    file = os.path.join(tmp_path, "out.m4a")
    await responsible.check(
        RRequest("POST", "/download", json={"info": await resp.json(), "opts": download_opts(file=file)}),
        status=200,
    )

    assert os.listdir(tmp_path) == [os.path.basename(file)]
    assert os.path.getsize(file) in range(23000, 24000)


@pytest.mark.asyncio_cooperative
async def test_info_no_url(responsible):
    await responsible.check(RRequest("GET", "/info"), status=400)
    await responsible.check(RRequest("POST", "/info"), status=400)
    await responsible.check(RRequest("POST", "/info", json={}), status=400)


@pytest.mark.asyncio_cooperative
async def test_playlist_not_found(responsible):
    req = RRequest(
        "POST",
        "/info",
        json={
            "url": 'https://www.youtube.com/playlist?list=PLle1CIlgXbgsPYNCGyJN1V6uM-clgnC2Y',
            "opts": playlist_opts(),
        }
    )
    resp = await responsible.check(req, status=422)
    assert 'playlist does not exist' in await resp.text()


@pytest.mark.asyncio_cooperative
async def test_smallest_playlist(responsible):
    req = RRequest(
        "POST",
        "/info",
        json={
            "url": 'https://www.youtube.com/playlist?list=PLdJo8g6QW5jbOPhBUj5ferM3FDkmmTHnp',
            "opts": playlist_opts(),
        },
    )
    resp = await responsible.check(req, status=200)
    b = await resp.json()

    entries = b['entries']
    assert len(entries) == 2
    assert all(isinstance(x['timestamp'], int) for x in entries)
