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
    json: Any = None
    headers: Optional[Dict[str, Any]] = None


@dataclass
class __AioReq(Request):
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
class __AioRes(Response):
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


async def _responsible(
        openapi: OpenAPI,
        session: ClientSession,
        req: RRequest,
        status: int,
) -> ClientResponse:
    async with session.request(req.method, req.path, headers=req.headers, json=req.json) as res:
        openapi.validate_response(
            request=__AioReq(req=res.request_info, data=json.dumps(req.json).encode("utf-8")),
            response=__AioRes(res, body=await res.read()),
        )

        assert res.status == status, f"expected {status} but got {res.status}"

        return res


class Responsible:
    openapi: OpenAPI
    client: ClientSession

    def __init__(self, session: ClientSession, openapi: OpenApiDict):
        self.client = session
        self.openapi = OpenAPI.from_dict(openapi)
        self.openapi.check_spec()

    async def check(self, req: RRequest, status: int) -> ClientResponse:
        """TODO flatten req struct"""
        return await _responsible(self.openapi, self.client, req, status)
