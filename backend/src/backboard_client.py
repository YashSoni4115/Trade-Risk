"""
Backboard.io Client
===================
Thin REST client wrapper for Backboard.io collections.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import logging
from typing import Any, Dict, Optional, Callable, Tuple
from urllib import request, error, parse

from .config import BACKBOARD_BASE_URL, BACKBOARD_API_KEY, DEFAULT_BACKBOARD_TIMEOUT, DEFAULT_BACKBOARD_MAX_RETRIES

logger = logging.getLogger(__name__)


class BackboardError(Exception):
    """Generic Backboard client error."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class BackboardNotFound(BackboardError):
    """Backboard resource not found."""


@dataclass
class BackboardResponse:
    status_code: int
    data: Dict[str, Any]


Transport = Callable[[request.Request, float], Tuple[int, bytes]]


def _default_transport(req: request.Request, timeout: float) -> Tuple[int, bytes]:
    with request.urlopen(req, timeout=timeout) as resp:
        return resp.getcode(), resp.read()


class BackboardClient:
    """
    Thin REST client for Backboard.io collections.

    Collection endpoints assumed:
    - POST   /collections/{collection}/documents
    - GET    /collections/{collection}/documents/{id}
    - PATCH  /collections/{collection}/documents/{id}
    - PUT    /collections/{collection}/documents/{id}
    - POST   /collections/{collection}/query
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = DEFAULT_BACKBOARD_TIMEOUT,
        max_retries: int = DEFAULT_BACKBOARD_MAX_RETRIES,
        transport: Optional[Transport] = None,
    ) -> None:
        self.base_url = (base_url or BACKBOARD_BASE_URL).rstrip("/")
        self.api_key = api_key or BACKBOARD_API_KEY
        self.timeout = timeout
        self.max_retries = max_retries
        self._transport = transport or _default_transport

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _request(
        self,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> BackboardResponse:
        if not self.base_url:
            raise BackboardError("BACKBOARD_BASE_URL is not configured")

        url = f"{self.base_url}{path}"
        if params:
            url = f"{url}?{parse.urlencode(params)}"

        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = request.Request(url, data=data, method=method, headers=self._headers())

        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                status_code, raw = self._transport(req, self.timeout)
                if 200 <= status_code < 300:
                    payload = json.loads(raw.decode("utf-8")) if raw else {}
                    return BackboardResponse(status_code=status_code, data=payload)

                if status_code in (502, 503, 504) and attempt < self.max_retries:
                    continue

                if status_code == 404:
                    raise BackboardNotFound("Resource not found", status_code=status_code)

                raise BackboardError("Backboard request failed", status_code=status_code)
            except error.HTTPError as http_err:
                status_code = http_err.code
                if status_code in (502, 503, 504) and attempt < self.max_retries:
                    last_error = http_err
                    continue
                if status_code == 404:
                    raise BackboardNotFound("Resource not found", status_code=status_code)
                raise BackboardError("Backboard request failed", status_code=status_code)
            except error.URLError as url_err:
                last_error = url_err
                if attempt < self.max_retries:
                    continue
                raise BackboardError("Backboard request failed")

        raise BackboardError(str(last_error) if last_error else "Backboard request failed")

    def create(self, collection: str, document: Dict[str, Any]) -> Dict[str, Any]:
        resp = self._request("POST", f"/collections/{collection}/documents", body=document)
        return resp.data

    def get(self, collection: str, document_id: str) -> Optional[Dict[str, Any]]:
        try:
            resp = self._request("GET", f"/collections/{collection}/documents/{document_id}")
            return resp.data
        except BackboardNotFound:
            return None

    def query(self, collection: str, filters: Dict[str, Any]) -> Dict[str, Any]:
        resp = self._request("POST", f"/collections/{collection}/query", body=filters)
        return resp.data

    def update(self, collection: str, document_id: str, document: Dict[str, Any]) -> Dict[str, Any]:
        resp = self._request("PATCH", f"/collections/{collection}/documents/{document_id}", body=document)
        return resp.data

    def upsert(self, collection: str, document_id: str, document: Dict[str, Any]) -> Dict[str, Any]:
        resp = self._request("PUT", f"/collections/{collection}/documents/{document_id}", body=document)
        return resp.data
