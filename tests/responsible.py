import base64
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Literal

import aiohttp
import validators
from aiohttp import ClientSession
from multidict import CIMultiDictProxy

Ref = Dict[Literal["$ref"], Any]
Schema = Dict[Literal["type"] | str, Any]
SchemaOrRef = Schema | Ref
Refs = Dict[str, Schema]
OpenAPI = Dict[str, Any]


@dataclass
class RRequest:
    method: Literal["GET", "POST"]
    path: str
    json: Any = None
    headers: Optional[Dict[str, Any]] = None


@dataclass
class RResponse:
    status: int
    headers: CIMultiDictProxy[str]
    body: Any


async def responsible(
        open_api: OpenAPI,
        session: aiohttp.ClientSession,
        req: RRequest,
        status: int,
) -> aiohttp.ClientResponse:
    async with session.request(req.method, req.path, headers=req.headers, json=req.json) as res:
        assert res.status == status

        res_schema = find_response_schema(open_api, req.path, req.method, status)

        body: Dict[str, Any] | str = \
            await res.json() if "application/json" in res.headers["content-type"] else await res.text()

        errors = validate_response(
            open_api["components"]["schemas"],
            res_schema,
            RResponse(status=res.status, headers=res.headers, body=body),
        )

        if errors:
            raise Exception(errors)

        return res


class Responsible:
    openapi: OpenAPI
    client: ClientSession

    def __init__(self, session: ClientSession, openapi: OpenAPI):
        self.client = session
        self.openapi = openapi

    async def check(self, req: RRequest, status: int) -> aiohttp.ClientResponse:
        """TODO flatten req struct"""
        return await responsible(self.openapi, self.client, req, status)


def find_response_schema(openapi: OpenAPI, path: str, method: str, status: int) -> Dict[str, Any]:
    return openapi["paths"][path][method.lower()]["responses"][str(status)]


@dataclass
class VErr:
    path: str
    what: str
    expected: str | int | List[str] | None = None
    actual: str | int | List[str] | None = None


def is_ref(d: SchemaOrRef) -> bool:
    return "$ref" in d


def validate_response(refs: Refs, res_schema: Dict[str, Any], res: RResponse) -> List[VErr]:
    """
    Validate a response against an OpenAPI response object
    :param refs: OpenAPI schema references
    :param res_schema: {
        "headers": { "Content-Type": { "schema": {...}, "required": true },
        "content": { "application/json": { "schema": {...} } }}
     }
    :param res: RResponse
    :return:
    """
    errs: List[VErr] = []

    path = "res"

    if "headers" in res_schema:
        header_keys: List[str] = list(res.headers.keys())

        for header_k, header_schema in res_schema["headers"].items():
            if header_k not in res.headers:
                if "required" in header_schema and header_schema["required"]:
                    errs.append(VErr(path, what="required", expected=header_k, actual=header_keys))
            else:
                value = res.headers[header_k]
                errs.extend(validate(refs, f"{path}.headers.{header_k}", header_schema, v=value))

    if "content" in res_schema and res_schema["content"]:
        res_mime = res.headers["Content-Type"]
        res_mime_in_schema = next((k for k in res_schema["content"].keys() if res_mime.startswith(k)), None)

        if res_mime_in_schema:
            # TODO check content-type
            schema = res_schema["content"][res_mime_in_schema]["schema"]
            errs.extend(validate(refs, f"{path}.body", schema, v=res.body))
        else:
            errs.append(VErr(path, what="mime", expected=list(res_schema["content"].keys()), actual=res_mime))

    return errs


def is_base_64(s: str) -> bool:
    try:
        return base64.b64encode(base64.b64decode(s)) == s
    except ValueError:
        return False


def validate_str(path: str, schema: Schema, v: str) -> List[VErr]:
    """
    Validate a string against OpenAPI schema

    :param path: path in the dictionary
    :param schema: OpenAPI Schema
    :param v: value to validate
    """

    errs: List[VErr] = []
    fmt: Optional[str] = None

    if "format" in schema:
        fmt = schema["format"]

    if fmt == "uri" and not validators.url(v):
        errs.append(VErr(path, what="format", expected=fmt))

    if fmt == "email" and not validators.email(v):
        errs.append(VErr(path, what="format", expected=fmt))

    if fmt == "ipv4" and not validators.ipv4(v):
        errs.append(VErr(path, what="format", expected=fmt))

    if fmt == "ipv6" and not validators.ipv6(v):
        errs.append(VErr(path, what="format", expected=fmt))

    if fmt == "uuid" and not validators.uuid(v):
        errs.append(VErr(path, what="format", expected=fmt))

    if fmt == "hostname" and not validators.domain(v):
        errs.append(VErr(path, what="format", expected=fmt))

    if fmt == "date":
        try:
            datetime.fromisoformat(v)
        except ValueError:
            errs.append(VErr(path, what="format", expected=fmt))

    if fmt == "date-time":
        try:
            datetime.fromisoformat(v)
        except ValueError:
            errs.append(VErr(path, what="format", expected=fmt))

    if fmt == "byte" and not is_base_64(v):
        errs.append(VErr(path, what="format", expected=fmt))

    if "pattern" in schema and not re.match(schema["pattern"], v):
        errs.append(VErr(path, what="pattern", expected=schema["pattern"]))

    if "minLength" in schema and len(v) < schema["minLength"]:
        errs.append(VErr(path, what="minLength", expected=schema["minLength"], actual=len(v)))

    if "maxLength" in schema and len(v) > schema["maxLength"]:
        errs.append(VErr(path, what="maxLength", expected=schema["maxLength"], actual=len(v)))

    if "enum" in schema and v not in schema["enum"]:
        errs.append(VErr(path, what="enum", expected=schema["enum"], actual=v))

    return errs


def to_schema(refs: Refs, sor: SchemaOrRef) -> Schema:
    """TODO test"""
    if is_ref(sor):
        return refs[sor["$ref"].split("/")[-1]]
    return sor


def validate_obj(refs: Refs, path: str, schema: Schema, obj: Dict[str, Any]) -> List[VErr]:
    """
    Validate an object against an OpenAPI schema

    :param refs: OpenAPI schema references
    :param path: path in the dictionary
    :param schema: {"type": "object", "properties": {...}, "required": ["property1", "property2", ...]}
    :param obj: an object
    """

    errs: List[VErr] = []

    if "properties" in schema:
        for schema_k, schema_or_ref in schema["properties"].items():
            if schema_k not in obj:
                if "required" in schema and schema_k in schema["required"]:
                    errs.append(VErr(path, what="required", expected=schema_k))
            else:
                errs.extend(validate(refs, f"{path}.{schema_k}", schema_or_ref, v=obj[schema_k]))

    return errs


def validate_arr(refs: Refs, path: str, schema: Dict[str, Any], v: List[Any]) -> List[VErr]:
    raise Exception("TODO")


def validate(refs: Refs, path: str, schema_or_ref: SchemaOrRef, v: Optional[Any]) -> List[VErr]:
    schema = to_schema(refs, schema_or_ref)

    if "type" not in schema:
        if v is None:
            if "nullable" in schema and schema["nullable"]:
                return []
            else:
                return [VErr(path, what="nullable", actual=v)]
        else:
            return []

    s_type: str = schema["type"]
    v_type = type(v)
    v_type_str = str(v_type)

    if s_type == "string":
        if v_type is str:
            return validate_str(path, schema, v)
        else:
            return [VErr(path, what="type", expected=s_type, actual=v_type_str)]

    elif s_type == "object":
        if v_type is dict:
            return validate_obj(refs, path, schema, v)
        else:
            return [VErr(path, what="type", expected=s_type, actual=v_type_str)]

    elif s_type == "array":
        if v_type is list:
            return validate_arr(refs, path, schema, v)
        else:
            return [VErr(path, what="type", expected=s_type, actual=v_type_str)]

    raise Exception(f"Unknown type {s_type}")
