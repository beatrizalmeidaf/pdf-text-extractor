"""Low-latency client for Apache Tika Server.

Why not `tika.parser.from_buffer`? It opens a new TCP connection per call, probes
the port before every request and goes through `/rmeta` (JSON-wrapped XHTML).
Talking to `/tika` directly over a keep-alive session halves the latency of a
warm server (≈29 ms -> ≈14 ms for a one-page PDF on a laptop).

The server is found in this order:
1. `PTE_TIKA_URL` (e.g. `http://tika:9998` in docker compose) — used as is;
2. a server already listening on localhost:9998;
3. a server we start ourselves from `PTE_TIKA_JAR` or the jar cached by `tika-python`
   (downloaded on first use), then warmed up so the first real request is fast.
"""

from __future__ import annotations

import atexit
import logging
import os
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass

import requests

log = logging.getLogger("pdf_text_api.tika")

DEFAULT_URL = "http://127.0.0.1:9998"
# JVM flags for a short-request server: class-data sharing for startup, throughput GC.
DEFAULT_JAVA_OPTS = "-Xshare:auto -XX:+UseParallelGC"
# Smallest valid PDF with one line of text — used to JIT-warm the PDF parser.
_WARMUP_PDF = (
    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 50]/Contents 4 0 R"
    b"/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
    b"4 0 obj<</Length 36>>stream\nBT /F1 12 Tf 10 20 Td (warm up) Tj ET\nendstream endobj\n"
    b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
    b"trailer<</Root 1 0 R>>\n%%EOF\n"
)


class TikaUnavailableError(RuntimeError):
    code = "tika_unavailable"
    status = 503


@dataclass
class TikaResponse:
    status: int
    xhtml: str
    elapsed_ms: float


class TikaClient:
    def __init__(self, url: str | None = None, timeout: float = 300):
        self.url = (url or os.environ.get("PTE_TIKA_URL") or DEFAULT_URL).rstrip("/")
        self.external = bool(url or os.environ.get("PTE_TIKA_URL"))
        self.timeout = timeout
        self._local = threading.local()
        self._lock = threading.Lock()
        self._process: subprocess.Popen | None = None
        self._ready = False

    # ------------------------------------------------------------------ lifecycle
    @property
    def session(self) -> requests.Session:
        # requests.Session isn't guaranteed thread-safe: one per thread, all keep-alive.
        s = getattr(self._local, "session", None)
        if s is None:
            s = self._local.session = requests.Session()
            s.headers["Connection"] = "keep-alive"
        return s

    def is_up(self) -> bool:
        try:
            return self.session.get(f"{self.url}/version", timeout=1.5).ok
        except requests.RequestException:
            return False

    def ensure_started(self, warmup: bool = True) -> None:
        if self._ready:
            return
        with self._lock:
            if self._ready:
                return
            if not self.is_up():
                if self.external:
                    raise TikaUnavailableError(f"Tika Server não responde em {self.url}")
                self._start_local()
            if warmup:
                self._warmup()
            self._ready = True

    def _start_local(self) -> None:
        java = shutil.which("java")
        if not java:
            raise TikaUnavailableError(
                "Java não encontrado. Instale um JRE 11+ ou aponte PTE_TIKA_URL "
                "para um Tika Server."
            )
        jar = _find_or_download_jar()
        port = self.url.rsplit(":", 1)[-1]
        opts = os.environ.get("PTE_TIKA_JAVA_OPTS", DEFAULT_JAVA_OPTS).split()
        cmd = [java, *opts, "-jar", jar, "--host", "127.0.0.1", "--port", port]
        log.info("starting Tika Server: %s", " ".join(cmd))
        self._process = subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL
        )
        atexit.register(self.stop)
        deadline = time.monotonic() + float(os.environ.get("PTE_TIKA_STARTUP_S", 90))
        while time.monotonic() < deadline:
            if self._process.poll() is not None:
                raise TikaUnavailableError("O processo do Tika Server terminou ao iniciar.")
            if self.is_up():
                return
            time.sleep(0.25)
        raise TikaUnavailableError("Tika Server não iniciou a tempo.")

    def _warmup(self, rounds: int = 3) -> None:
        started = time.perf_counter()
        for _ in range(rounds):
            try:
                self.parse(_WARMUP_PDF, ensure=False)
            except Exception:  # noqa: BLE001 - warm-up is best effort
                return
        log.info("Tika warm-up: %.0f ms", (time.perf_counter() - started) * 1000)

    def stop(self) -> None:
        if self._process and self._process.poll() is None:
            self._process.terminate()
        self._process = None
        self._ready = False

    # ------------------------------------------------------------------ requests
    def parse(
        self,
        data: bytes,
        *,
        password: str | None = None,
        ocr: str = "no_ocr",
        ocr_language: str | None = None,
        marked_content: bool = False,
        content_type: str | None = None,
        ensure: bool = True,
    ) -> TikaResponse:
        """PUT the document to `/tika` and return its XHTML.

        `ocr`: "no_ocr" (fastest), "auto", "ocr_only" or "ocr_and_text" — OCR needs
        Tesseract on the Tika server (the Docker image ships it).
        `marked_content`: use the PDF's tag tree (headings, lists, tables) if it has one.
        """
        if ensure:
            self.ensure_started()
        headers = {
            "Accept": "text/html",
            "X-Tika-PDFOcrStrategy": ocr,
            "X-Tika-PDFspacingTolerance": "2.0",
            "X-Tika-PDFextractInlineImages": "false",
            "X-Tika-PDFextractAnnotationText": "true",
            "X-Tika-PDFenableAutoSpace": "true",
            "X-Tika-PDFsortByPosition": "false",
        }
        if marked_content:
            headers["X-Tika-PDFextractMarkedContent"] = "true"
        if ocr != "no_ocr" and ocr_language:
            headers["X-Tika-OCRLanguage"] = ocr_language
        if password:
            headers["Password"] = password
        if content_type:
            headers["Content-Type"] = content_type
        started = time.perf_counter()
        try:
            resp = self.session.put(
                f"{self.url}/tika", data=data, headers=headers, timeout=self.timeout
            )
        except requests.ConnectionError:
            # Server died or keep-alive socket went stale: reconnect once.
            self._ready = False
            self._local.session = None
            if not ensure:
                raise
            self.ensure_started(warmup=False)
            resp = self.session.put(
                f"{self.url}/tika", data=data, headers=headers, timeout=self.timeout
            )
        except requests.RequestException as exc:
            raise TikaUnavailableError(f"Falha ao falar com o Tika Server: {exc}") from None
        resp.encoding = "utf-8"
        return TikaResponse(resp.status_code, resp.text, (time.perf_counter() - started) * 1000)


def _find_or_download_jar() -> str:
    jar = os.environ.get("PTE_TIKA_JAR")
    if jar and os.path.isfile(jar):
        return jar
    # Reuse the jar cached by tika-python (same version pinning, same checksum logic).
    from tika import tika as tk

    path = os.path.join(tk.TikaJarPath, "tika-server.jar")
    if not os.path.isfile(path):
        log.info("downloading Tika Server %s (one time)…", tk.TikaVersion)
        tk.getRemoteJar(tk.TikaServerJar, path)
    return path


_default: TikaClient | None = None
_default_lock = threading.Lock()


def get_client() -> TikaClient:
    global _default
    if _default is None:
        with _default_lock:
            if _default is None:
                _default = TikaClient()
    return _default
