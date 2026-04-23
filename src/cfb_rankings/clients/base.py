from __future__ import annotations

import json
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class JsonApiClient:
    def __init__(
        self,
        base_url: str,
        headers: dict[str, str] | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.headers = {"User-Agent": "cfb-rankings-site/0.1"} | (headers or {})

    def get_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{self.base_url}/{path.lstrip('/')}"
        if params:
            filtered_params = {key: value for key, value in params.items() if value is not None}
            query_string = urlencode(filtered_params, doseq=True)
            if query_string:
                url = f"{url}?{query_string}"

        attempt = 0
        max_attempts = 5
        while True:
            request = Request(url, headers=self.headers, method="GET")
            try:
                with urlopen(request, timeout=self.timeout_seconds) as response:
                    body = response.read().decode("utf-8")
                    return json.loads(body) if body else None
            except HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                if exc.code in {429, 500, 502, 503, 504, 520, 521, 522, 523, 524, 525, 526} and attempt < max_attempts - 1:
                    time.sleep(1.5 * (2**attempt))
                    attempt += 1
                    continue
                raise RuntimeError(f"HTTP {exc.code} for {url}: {detail}") from exc
            except URLError as exc:
                if _is_permission_denied_network_error(exc):
                    raise RuntimeError(
                        f"Network access is blocked for {url}: {exc}. "
                        "Failing fast instead of retrying because this environment appears to be offline or restricted."
                    ) from exc
                if attempt < max_attempts - 1:
                    time.sleep(1.5 * (2**attempt))
                    attempt += 1
                    continue
                raise RuntimeError(f"Network error for {url}: {exc}") from exc


def _is_permission_denied_network_error(exc: URLError) -> bool:
    text = str(exc)
    return "WinError 10013" in text or "forbidden by its access permissions" in text
