#!/usr/bin/env python3
"""Local HTTP MCP server with document conversion and engineering utilities."""
import csv
import difflib
import html
import json
from pathlib import Path

try:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP as Server
    _V1 = True
except ModuleNotFoundError:  # mcp 2.x
    from mcp.server.mcpserver import MCPServer as Server
    _V1 = False


HOST, PORT = "127.0.0.1", 8768
SERVER_NAME = "terminal_toolbox"
mcp = Server(SERVER_NAME, host=HOST, port=PORT) if _V1 else Server(SERVER_NAME)


def _source_file(path: str) -> Path:
    source = Path(path).expanduser()
    if not source.is_file():
        raise FileNotFoundError(f"Input file does not exist or is not a file: {source}")
    return source.resolve()


def _output_file(source: Path, path: str, suffix: str) -> Path:
    output = Path(path).expanduser() if path else source.with_suffix(suffix)
    output = output.resolve()
    if output == source:
        raise ValueError("Output path must be different from the input path.")
    if not output.parent.is_dir():
        raise FileNotFoundError(f"Output directory does not exist: {output.parent}")
    return output


def _markdown_html(source: Path, title: str) -> str:
    try:
        import markdown
    except ImportError as error:
        raise RuntimeError("Markdown conversion requires the Markdown package; install project requirements.") from error

    body = markdown.markdown(
        source.read_text(encoding="utf-8"),
        extensions=["fenced_code", "tables"],
    )
    return (
        "<!doctype html>\n<html><head><meta charset=\"utf-8\">\n"
        f"<title>{html.escape(title)}</title>\n"
        "<style>body{font:16px/1.5 sans-serif;max-width:960px;margin:2rem auto;padding:0 1rem}"
        "pre{overflow:auto;padding:1rem;background:#f4f4f4}table{border-collapse:collapse}"
        "th,td{border:1px solid #bbb;padding:.4rem .7rem;text-align:left}</style>\n"
        f"</head><body>\n{body}\n</body></html>\n"
    )


def _html_to_pdf(source: Path, output: Path) -> str:
    try:
        from weasyprint import HTML
    except ImportError as error:
        raise RuntimeError("PDF conversion requires WeasyPrint; install project requirements.") from error

    HTML(filename=str(source), base_url=source.parent.as_uri()).write_pdf(str(output))
    return f"Created PDF: {output}"


@mcp.tool()
def csv_to_html(csv_path: str, html_path: str = "", title: str = "CSV data") -> str:
    """Convert a CSV file into an escaped HTML table. Defaults output to the same name with .html."""
    source = _source_file(csv_path)
    output = _output_file(source, html_path, ".html")
    with source.open(encoding="utf-8-sig", newline="") as csv_file:
        rows = list(csv.reader(csv_file))
    if rows:
        header, body_rows = rows[0], rows[1:]
        header_html = "<thead><tr>" + "".join(f"<th>{html.escape(cell)}</th>" for cell in header) + "</tr></thead>"
        body_html = "<tbody>" + "".join(
            "<tr>" + "".join(f"<td>{html.escape(cell)}</td>" for cell in row) + "</tr>"
            for row in body_rows
        ) + "</tbody>"
        table = f"<table>{header_html}{body_html}</table>"
    else:
        table = "<p>The CSV file is empty.</p>"
    page = (
        "<!doctype html>\n<html><head><meta charset=\"utf-8\">\n"
        f"<title>{html.escape(title)}</title>\n"
        "<style>body{font:16px sans-serif;margin:2rem}table{border-collapse:collapse}"
        "th,td{border:1px solid #bbb;padding:.4rem .7rem;text-align:left}</style>\n"
        f"</head><body><h1>{html.escape(title)}</h1>{table}</body></html>\n"
    )
    output.write_text(page, encoding="utf-8")
    return f"Converted {len(body_rows) if rows else 0} data rows to HTML: {output}"


@mcp.tool()
def csv_summary(csv_path: str) -> str:
    """Report the row and column counts and headers in a CSV file."""
    source = _source_file(csv_path)
    with source.open(encoding="utf-8-sig", newline="") as csv_file:
        rows = list(csv.reader(csv_file))
    if not rows:
        return f"{source}: empty CSV (0 rows, 0 columns)."
    headers = rows[0]
    return (
        f"File: {source}\nData rows: {len(rows) - 1}\nColumns: {len(headers)}\n"
        f"Headers: {json.dumps(headers, ensure_ascii=False)}"
    )


@mcp.tool()
def markdown_to_html(markdown_path: str, html_path: str = "", title: str = "") -> str:
    """Convert a Markdown or README file to an HTML document."""
    source = _source_file(markdown_path)
    output = _output_file(source, html_path, ".html")
    document_title = title or source.stem
    output.write_text(_markdown_html(source, document_title), encoding="utf-8")
    return f"Converted Markdown to HTML: {output}"


@mcp.tool()
def readme_to_pdf(readme_path: str, pdf_path: str = "") -> str:
    """Convert a README or other Markdown document to PDF."""
    source = _source_file(readme_path)
    output = _output_file(source, pdf_path, ".pdf")
    document = _markdown_html(source, source.stem)
    try:
        from weasyprint import HTML
    except ImportError as error:
        raise RuntimeError("PDF conversion requires WeasyPrint; install project requirements.") from error
    HTML(string=document, base_url=source.parent.as_uri()).write_pdf(str(output))
    return f"Converted Markdown to PDF: {output}"


@mcp.tool()
def html_to_pdf(html_path: str, pdf_path: str = "") -> str:
    """Convert an HTML file to PDF using WeasyPrint."""
    source = _source_file(html_path)
    output = _output_file(source, pdf_path, ".pdf")
    return _html_to_pdf(source, output)


@mcp.tool()
def format_json_file(json_path: str, output_path: str = "") -> str:
    """Validate and pretty-print a JSON file, defaulting to a separate .formatted.json output."""
    source = _source_file(json_path)
    default_output = source.with_name(f"{source.stem}.formatted.json")
    output = Path(output_path).expanduser().resolve() if output_path else default_output.resolve()
    if output == source:
        raise ValueError("Output path must be different from the input path.")
    if not output.parent.is_dir():
        raise FileNotFoundError(f"Output directory does not exist: {output.parent}")
    data = json.loads(source.read_text(encoding="utf-8"))
    output.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return f"Validated and formatted JSON: {output}"


@mcp.tool()
def text_file_stats(file_path: str) -> str:
    """Count lines, words, characters, and bytes in a UTF-8 text file."""
    source = _source_file(file_path)
    text = source.read_text(encoding="utf-8")
    return (
        f"File: {source}\nLines: {len(text.splitlines())}\nWords: {len(text.split())}\n"
        f"Characters: {len(text)}\nBytes (UTF-8): {len(text.encode('utf-8'))}"
    )


@mcp.tool()
def diff_text_files(first_path: str, second_path: str) -> str:
    """Show a unified diff between two UTF-8 text files."""
    first = _source_file(first_path)
    second = _source_file(second_path)
    diff = difflib.unified_diff(
        first.read_text(encoding="utf-8").splitlines(),
        second.read_text(encoding="utf-8").splitlines(),
        fromfile=str(first),
        tofile=str(second),
        lineterm="",
    )
    result = "\n".join(diff)
    return result or "Files are identical."


if __name__ == "__main__":
    if _V1:
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="streamable-http", host=HOST, port=PORT)
