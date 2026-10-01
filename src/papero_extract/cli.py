"""Command line interface.

papero-extract extract artigo.pdf                       # Markdown no terminal
papero-extract extract artigo.pdf -o artigo.md --images # + pasta images/ ao lado
papero-extract extract artigo.pdf -f json -o artigo.json
papero-extract extract artigo.pdf -f csv -o tabelas.csv # só as tabelas
papero-extract extract contrato.docx -f text            # qualquer formato que o Tika lê
papero-extract extract artigo.pdf --fast                # só texto, via Tika (mais rápido)
papero-extract serve --port 8000
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import __version__
from .cleaning import CleanOptions
from .extractor import ExtractionError, extract, extract_text
from .render import tables_csv

FORMATS = ("markdown", "text", "json", "html", "csv")
_EXT = {".md": "markdown", ".txt": "text", ".json": "json", ".html": "html", ".csv": "csv"}


def _fast(args: argparse.Namespace) -> str:
    options = CleanOptions(
        remove_page_numbers=not args.raw,
        remove_headers_footers=not args.raw and not args.keep_headers,
        dehyphenate=args.dehyphenate,
        normalize_whitespace=not args.raw,
    )
    result = extract_text(args.file, pages=args.pages, password=args.password, clean=options)
    _report(f"{result.page_count} páginas, {result.elapsed_ms:.0f} ms (Tika)", args)
    if result.likely_scanned:
        _warn("pouco texto encontrado — o PDF parece escaneado; tente sem --fast (OCR).")
    if args.format == "json":
        return json.dumps(result.to_dict(include_pages=True), ensure_ascii=False, indent=2)
    return result.text


def _structured(args: argparse.Namespace) -> str:
    doc = extract(
        args.file,
        pages=args.pages,
        password=args.password,
        images=args.images,
        image_scale=args.image_scale,
        tables=not args.no_tables,
        formulas=not args.no_formulas,
        ocr=args.ocr,
        ocr_language=args.ocr_language,
        tika=not args.no_tika,
        workers=args.workers,
    )
    t = doc.timings
    split = (
        f" (Tika {t['tika_ms']:.0f} ms ‖ layout {t['layout_ms']:.0f} ms)" if "tika_ms" in t else ""
    )
    _report(
        f"{doc.page_count} páginas, {len(doc.tables)} tabelas, {len(doc.figures)} figuras, "
        f"{len(doc.formulas)} fórmulas — {doc.elapsed_ms:.0f} ms{split}",
        args,
    )
    for w in doc.warnings:
        _warn(w)
    if args.images and args.output:
        folder = Path(args.output).parent / "images"
        saved = 0
        for block in doc.blocks():
            if block.image is not None:
                folder.mkdir(parents=True, exist_ok=True)
                (folder / block.image.name).write_bytes(block.image.data)
                saved += 1
        if saved:
            _report(f"{saved} imagens -> {folder}", args)
    fmt = args.format
    if fmt == "markdown":
        return doc.to_markdown(
            images="ref" if args.output else "none", page_breaks=args.page_breaks
        )
    if fmt == "text":
        return doc.text
    if fmt == "html":
        return doc.to_html(images="embed")
    if fmt == "csv":
        return tables_csv(doc)
    return json.dumps(doc.to_dict(embed_images=False), ensure_ascii=False, indent=2)


def _report(msg: str, args: argparse.Namespace) -> None:
    if not args.quiet:
        print(msg, file=sys.stderr)


def _warn(msg: str) -> None:
    print(f"aviso: {msg}", file=sys.stderr)


def _extract(args: argparse.Namespace) -> int:
    if args.format is None:
        suffix = Path(args.output).suffix.lower() if args.output else ""
        args.format = _EXT.get(suffix, "markdown")
    try:
        output = _fast(args) if args.fast else _structured(args)
    except FileNotFoundError:
        print(f"erro: arquivo não encontrado: {args.file}", file=sys.stderr)
        return 2
    except ExtractionError as exc:
        print(f"erro ({exc.code}): {exc}", file=sys.stderr)
        return 1
    if args.output:
        Path(args.output).write_text(
            output, encoding="utf-8-sig" if args.format == "csv" else "utf-8"
        )
        _report(f"-> {args.output}", args)
    else:
        sys.stdout.write(output if output.endswith("\n") else output + "\n")
    return 0


def _serve(args: argparse.Namespace) -> int:
    try:
        import uvicorn
    except ImportError:
        print("Instale os extras da API: pip install 'papero-extract[api]'", file=sys.stderr)
        return 1
    if args.workers:
        os.environ["PTE_WORKERS"] = str(args.workers)
    uvicorn.run(
        "papero_extract.api:app",
        host=args.host,
        port=args.port,
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(
        prog="papero-extract",
        description="papero — extração estruturada de PDFs e documentos (Apache Tika + PDFium).",
    )
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    ex = sub.add_parser("extract", help="extrair texto e estrutura de um arquivo")
    ex.add_argument("file")
    ex.add_argument("-o", "--output", help="arquivo de saída (padrão: stdout)")
    ex.add_argument(
        "-f",
        "--format",
        choices=FORMATS,
        help="formato de saída (padrão: pela extensão de -o, senão markdown)",
    )
    ex.add_argument("-p", "--pages", help="páginas, ex.: 1-3,5")
    ex.add_argument("--password")
    ex.add_argument(
        "--images", action="store_true", help="recortar figuras/tabelas/fórmulas em PNG"
    )
    ex.add_argument(
        "--image-scale", type=float, default=2.0, help="resolução dos recortes (2 = 144 dpi)"
    )
    ex.add_argument("--no-tables", action="store_true", help="não detectar tabelas")
    ex.add_argument("--no-formulas", action="store_true", help="não detectar fórmulas")
    ex.add_argument("--ocr", choices=("auto", "off", "force"), default="auto")
    ex.add_argument("--ocr-language", default="por+eng")
    ex.add_argument("--no-tika", action="store_true", help="só o motor de layout (sem Java)")
    ex.add_argument("--page-breaks", action="store_true", help="marcar o início de cada página")
    ex.add_argument("--fast", action="store_true", help="só texto, via Tika (o mais rápido)")
    ex.add_argument("--raw", action="store_true", help="--fast: sem nenhuma limpeza")
    ex.add_argument("--keep-headers", action="store_true", help="--fast: manter cabeçalhos/rodapés")
    ex.add_argument(
        "--dehyphenate", action="store_true", help="--fast: juntar palavras hifenizadas"
    )
    ex.add_argument(
        "-w",
        "--workers",
        type=int,
        default=os.cpu_count() or 1,
        help="processos para PDFs grandes (padrão: nº de CPUs)",
    )
    ex.add_argument("-q", "--quiet", action="store_true", help="sem resumo no stderr")
    ex.set_defaults(func=_extract)

    sv = sub.add_parser("serve", help="subir a API HTTP e o app web")
    sv.add_argument("--host", default="0.0.0.0")
    sv.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8000)))
    sv.add_argument("-w", "--workers", type=int, help="processos de extração")
    sv.set_defaults(func=_serve)

    args = parser.parse_args(argv)
    return args.func(args)
