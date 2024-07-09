import json
from dataclasses import dataclass
from typing import Any, Dict, Optional, Literal

from aiohttp import ClientSession, ClientResponse, RequestInfo
from multidict import CIMultiDict
from openapi_core import OpenAPI
from openapi_core.protocols import Request, Response

OpenApiDict = Dict[str, Any]


@dataclass
class RRequest:
    method: Literal["GET", "POST"]
    path: str
    json: Optional[Dict[str, Any]] = None
    headers: Optional[Dict[str, Any]] = None


@dataclass
class _AioReq(Request):
    req: RequestInfo
    data: bytes

    @property
    def host_url(self) -> str:
        return f"http://{self.req.url.host}:{self.req.url.port}"

    @property
    def path(self) -> str:
        return self.req.url.path

    @property
    def method(self) -> str:
        return self.req.method.lower()

    @property
    def body(self) -> Optional[bytes]:
        return self.data

    @property
    def content_type(self) -> str:
        return self.req.headers["Content-Type"]


@dataclass
class _AioRes(Response):
    res: ClientResponse
    body: bytes

    @property
    def data(self) -> bytes:
        return self.body

    @property
    def status_code(self) -> int:
        return self.res.status

    @property
    def content_type(self) -> str:
        return self.res.content_type or ""

    @property
    def headers(self) -> CIMultiDict[str]:
        return CIMultiDict(self.res.headers)


class Responsible:
    openapi: OpenAPI
    client: ClientSession

    def __init__(self, session: ClientSession, openapi: OpenApiDict):
        self.client = session
        self.openapi = OpenAPI.from_dict(openapi)

    async def check(self, req: RRequest, status: int) -> ClientResponse:
        async with self.client.request(req.method, req.path, headers=req.headers, json=req.json) as res:
            self.openapi.validate_response(
                request=_AioReq(req=res.request_info, data=json.dumps(req.json).encode("utf-8")),
                response=_AioRes(res, body=await res.read()),
            )

            assert res.status == status, f"expected {status} but got {res.status}"

            return res
