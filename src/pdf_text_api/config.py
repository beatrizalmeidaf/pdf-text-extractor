"""Runtime settings, read from environment variables prefixed with PTE_."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _int(name: str, default: int) -> int:
    value = os.environ.get(f"PTE_{name}")
    return int(value) if value not in (None, "") else default


def _list(name: str, default: str = "") -> list[str]:
    raw = os.environ.get(f"PTE_{name}", default)
    return [item.strip() for item in raw.split(",") if item.strip()]


def _bool(name: str, default: bool) -> bool:
    value = os.environ.get(f"PTE_{name}")
    return default if value is None else value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    max_file_mb: int = 100
    max_pages: int = 5000
    workers: int = field(default_factory=lambda: max(1, os.cpu_count() or 1))
    max_concurrent_jobs: int = 0  # 0 = workers * 4
    request_timeout_s: int = 120
    parallel_threshold: int = 16  # pages; above this, layout is split across worker processes
    api_keys: frozenset[str] = frozenset()
    rate_limit_per_minute: int = 0  # 0 = off
    cors_origins: tuple[str, ...] = ("*",)
    enable_ui: bool = True
    cache_entries: int = 64  # identical uploads + options are answered from memory
    cache_mb: int = 256

    @property
    def max_file_bytes(self) -> int:
        return self.max_file_mb * 1024 * 1024

    @property
    def job_limit(self) -> int:
        return self.max_concurrent_jobs or self.workers * 4

    @classmethod
    def from_env(cls) -> Settings:
        defaults = cls()
        return cls(
            max_file_mb=_int("MAX_FILE_MB", defaults.max_file_mb),
            max_pages=_int("MAX_PAGES", defaults.max_pages),
            workers=_int("WORKERS", defaults.workers),
            max_concurrent_jobs=_int("MAX_CONCURRENT_JOBS", 0),
            request_timeout_s=_int("REQUEST_TIMEOUT_S", defaults.request_timeout_s),
            parallel_threshold=_int("PARALLEL_THRESHOLD", defaults.parallel_threshold),
            api_keys=frozenset(_list("API_KEYS")),
            rate_limit_per_minute=_int("RATE_LIMIT_PER_MINUTE", 0),
            cors_origins=tuple(_list("CORS_ORIGINS", "*")),
            enable_ui=_bool("ENABLE_UI", True),
            cache_entries=_int("CACHE_ENTRIES", defaults.cache_entries),
            cache_mb=_int("CACHE_MB", defaults.cache_mb),
        )
