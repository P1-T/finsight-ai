from __future__ import annotations

import ipaddress
import json
import threading
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class _Window:
    starts_at: float
    count: int


class RequestRateLimitMiddleware:
    """Small per-process fixed-window limiter for public, costly API routes.

    The limiter is intentionally in-memory for the single-task demo deployment.
    When running behind the ECS Gateway ALB, set TRUST_PROXY_HEADERS=true and
    allow inbound traffic to the task only from that load balancer. The ALB's
    default X-Forwarded-For append mode places its verified client address last.
    """

    WINDOW_SECONDS = 60
    MAX_TRACKED_CLIENTS = 10_000
    PRUNE_EVERY_REQUESTS = 128

    def __init__(
        self,
        app: Any,
        *,
        chat_requests_per_minute: int = 10,
        company_search_requests_per_minute: int = 60,
        trust_proxy_headers: bool = False,
    ) -> None:
        self.app = app
        self.limits = {
            ("POST", "/api/chat/stream"): max(1, chat_requests_per_minute),
            ("GET", "/api/companies/search"): max(1, company_search_requests_per_minute),
        }
        self.trust_proxy_headers = trust_proxy_headers
        self._windows: dict[tuple[str, str], _Window] = {}
        self._lock = threading.Lock()
        self._requests_seen = 0

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        route_key = (scope.get("method", "").upper(), scope.get("path", ""))
        limit = self.limits.get(route_key)
        if limit is None:
            await self.app(scope, receive, send)
            return

        client_ip = self._client_ip(scope)
        allowed, retry_after = self._allow(client_ip, route_key[1], limit)
        if not allowed:
            body = json.dumps(
                {
                    "detail": "Request limit reached. Please wait before trying again.",
                    "retry_after_seconds": retry_after,
                },
                separators=(",", ":"),
            ).encode("utf-8")
            await send(
                {
                    "type": "http.response.start",
                    "status": 429,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"content-length", str(len(body)).encode("ascii")),
                        (b"retry-after", str(retry_after).encode("ascii")),
                        (b"cache-control", b"no-store"),
                    ],
                }
            )
            await send({"type": "http.response.body", "body": body})
            return

        await self.app(scope, receive, send)

    def _client_ip(self, scope: dict[str, Any]) -> str:
        peer = scope.get("client")
        peer_host = peer[0] if peer else "unknown"

        if self.trust_proxy_headers:
            for name, value in scope.get("headers", []):
                if name.lower() == b"x-forwarded-for":
                    forwarded_ips = value.decode("latin-1").split(",")
                    if forwarded_ips:
                        parsed = self._parse_ip(forwarded_ips[-1].strip())
                        if parsed is not None:
                            return parsed
                    break

        return self._parse_ip(peer_host) or "unknown"

    @staticmethod
    def _parse_ip(value: str) -> str | None:
        candidate = value.strip()
        if candidate.startswith("[") and "]" in candidate:
            candidate = candidate[1 : candidate.index("]")]
        else:
            # Support IPv4-with-port when a proxy is configured to include it.
            host, separator, port = candidate.rpartition(":")
            if separator and "." in host and port.isdigit():
                candidate = host
        try:
            return ipaddress.ip_address(candidate).compressed
        except ValueError:
            return None

    def _allow(self, client_ip: str, path: str, limit: int) -> tuple[bool, int]:
        now = time.monotonic()
        key = (client_ip, path)
        with self._lock:
            self._requests_seen += 1
            current = self._windows.get(key)

            if current is None:
                if len(self._windows) >= self.MAX_TRACKED_CLIENTS:
                    self._prune(now)
                if len(self._windows) >= self.MAX_TRACKED_CLIENTS:
                    return False, self.WINDOW_SECONDS
                self._windows[key] = _Window(starts_at=now, count=1)
                return True, 0

            elapsed = now - current.starts_at
            if elapsed >= self.WINDOW_SECONDS:
                current.starts_at = now
                current.count = 1
                return True, 0

            if current.count >= limit:
                retry_after = max(1, int(self.WINDOW_SECONDS - elapsed + 0.999))
                return False, retry_after

            current.count += 1
            if self._requests_seen % self.PRUNE_EVERY_REQUESTS == 0:
                self._prune(now)
            return True, 0

    def _prune(self, now: float) -> None:
        expired = [
            key
            for key, window in self._windows.items()
            if now - window.starts_at >= self.WINDOW_SECONDS
        ]
        for key in expired:
            self._windows.pop(key, None)
