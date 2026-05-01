"""Build a single PDF from all mkdocs source markdown files.

Pipeline:
1. Read every markdown file in mkdocs.yml navigation order.
2. Render with python-markdown + pymdown-extensions for fenced code, tables,
   admonitions, etc.
3. Wrap with a print-tuned stylesheet (A4, Noto Sans KR, JetBrains Mono).
4. Hand off the merged HTML to Windows Chrome (headless) to emit a PDF.
"""

from __future__ import annotations

import html
import os
import re
import subprocess
import sys
from pathlib import Path

import markdown

REPO = Path("/home/totorokr/Assist 강의")
DOCS = REPO / "docs"
OUT_DIR = REPO / "dist"
OUT_HTML = OUT_DIR / "lecture_full.html"
OUT_PDF = OUT_DIR / "AI기반_SQL_분석_에이전트_구축_강의자료.pdf"

CHROME = "/mnt/c/Program Files/Google/Chrome/Application/chrome.exe"

# Navigation order mirrors mkdocs.yml.
PAGES: list[tuple[str, Path]] = [
    ("과정 개요", DOCS / "index.md"),
    ("사전 준비", DOCS / "setup.md"),

    ("Day 1 — SQL · RAG · 프로젝트 (1~8H)", DOCS / "day1/index.md"),
    ("01H. OT & 전체 데모", DOCS / "day1/01-ot-demo.md"),
    ("02H. PostgreSQL 기초", DOCS / "day1/02-postgres-basics.md"),
    ("03H. 집계 · 조인 · CTE", DOCS / "day1/03-sql-advanced.md"),
    ("04H. Schema Intelligence", DOCS / "day1/04-schema-intelligence.md"),
    ("05H. LlamaIndex 개론", DOCS / "day1/05-llamaindex-intro.md"),
    ("06H. 임베딩 + ChromaDB", DOCS / "day1/06-embedding-chromadb.md"),
    ("07H. Text-to-SQL 맛보기", DOCS / "day1/07-text-to-sql.md"),
    ("08H. 프로젝트 브리핑", DOCS / "day1/08-project-briefing.md"),

    ("Day 2 — Text-to-SQL 상담사 (9~12H)", DOCS / "day2/index.md"),
    ("09H. 제안서 피어리뷰", DOCS / "day2/09-peer-review.md"),
    ("10H. Text-to-SQL 심화", DOCS / "day2/10-text-to-sql-advanced.md"),
    ("11H. 멀티턴 상담사", DOCS / "day2/11-multiturn-chatbot.md"),
    ("12H. Gradio UI", DOCS / "day2/12-gradio-ui.md"),

    ("Day 3 — Vanna · LangChain · LangGraph (13~20H)", DOCS / "day3/index.md"),
    ("13H. Vanna.ai 구조", DOCS / "day3/13-vanna-intro.md"),
    ("14H. Vanna 자가학습", DOCS / "day3/14-vanna-training.md"),
    ("15H. LangChain & LCEL", DOCS / "day3/15-langchain-lcel.md"),
    ("16H. LCEL RAG 체인", DOCS / "day3/16-lcel-rag-chain.md"),
    ("17H. Advanced RAG 쿼리변환", DOCS / "day3/17-advanced-rag-query.md"),
    ("18H. Advanced RAG 검색고도화", DOCS / "day3/18-advanced-rag-retrieval.md"),
    ("19H. LangGraph 개념", DOCS / "day3/19-langgraph-concept.md"),
    ("20H. SQL 에이전트 빌드", DOCS / "day3/20-sql-agent-build.md"),

    ("Day 4 — 평가 · 발표 (21~24H)", DOCS / "day4/index.md"),
    ("21H. LangSmith 트레이싱", DOCS / "day4/21-langsmith.md"),
    ("22H. Ragas 정량 평가", DOCS / "day4/22-ragas-eval.md"),
    ("23H. 최종 튜닝 & 리허설", DOCS / "day4/23-final-tuning.md"),
    ("24H. 최종 발표 & 수료", DOCS / "day4/24-final-presentation.md"),

    ("부록 — 노트북 번호 체계", DOCS / "appendix/notebook-numbering.md"),
    ("부록 — 트러블슈팅", DOCS / "appendix/troubleshooting.md"),
    ("부록 — 프로젝트 브리프", DOCS / "appendix/project-brief.md"),
]

MD_EXTENSIONS = [
    "extra",           # tables, fenced_code, attr_list, def_list, footnotes, abbr
    "admonition",
    "toc",
    "sane_lists",
    "codehilite",
    "pymdownx.superfences",
    "pymdownx.highlight",
    "pymdownx.inlinehilite",
    "pymdownx.tabbed",
    "pymdownx.details",
    "pymdownx.tilde",
    "pymdownx.caret",
    "pymdownx.mark",
    "pymdownx.keys",
    "pymdownx.emoji",
    "pymdownx.magiclink",
    "md_in_html",
]

MD_EXT_CONFIGS = {
    "codehilite": {"css_class": "highlight", "guess_lang": False},
    "pymdownx.highlight": {
        "anchor_linenums": False,
        "pygments_lang_class": True,
    },
    "pymdownx.tabbed": {"alternate_style": True},
    "toc": {"permalink": False, "toc_depth": 3},
}

FRONT_MATTER_RE = re.compile(r"\A---\s*\n.*?\n---\s*\n", re.DOTALL)

# Rewrite ":material-...:" / ":fontawesome-...:" style Material icons that
# pymdownx.emoji won't resolve without the Material Twemoji generator. Strip
# them so they don't appear as raw source in the PDF.
MATERIAL_ICON_RE = re.compile(r":(?:material|fontawesome|octicons|simple)-[a-z0-9-]+:")


def render_page(title: str, path: Path, first: bool) -> str:
    raw = path.read_text(encoding="utf-8")
    raw = FRONT_MATTER_RE.sub("", raw)
    raw = MATERIAL_ICON_RE.sub("", raw)

    md = markdown.Markdown(
        extensions=MD_EXTENSIONS,
        extension_configs=MD_EXT_CONFIGS,
        output_format="html5",
    )
    body = md.convert(raw)

    page_break = "" if first else '<div class="page-break"></div>'
    anchor = path.stem
    return (
        f'{page_break}<section class="chapter" id="{anchor}">'
        f'<div class="chapter-label">{html.escape(title)}</div>'
        f"{body}"
        f"</section>"
    )


STYLESHEET = """
@page {
    size: A4;
    margin: 18mm 16mm 20mm 16mm;
}

html {
    font-family: 'Noto Sans KR', 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif;
    font-size: 10.5pt;
    color: #1f2328;
    line-height: 1.55;
}

body { margin: 0; }

.cover {
    height: 260mm;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    text-align: center;
    border: 2px solid #3f51b5;
    border-radius: 8px;
    padding: 40px;
    margin-bottom: 30mm;
    background: linear-gradient(135deg, #eef1ff 0%, #fff7e6 100%);
    page-break-after: always;
}
.cover h1 { font-size: 32pt; margin: 0 0 12pt 0; color: #1a237e; }
.cover h2 { font-size: 16pt; margin: 0 0 24pt 0; color: #303f9f; font-weight: 500; }
.cover .meta { font-size: 11pt; color: #455a64; line-height: 1.9; }
.cover .tag {
    display: inline-block;
    margin: 4pt;
    padding: 4pt 10pt;
    border: 1px solid #3f51b5;
    border-radius: 999px;
    font-size: 9pt;
    color: #1a237e;
    background: #fff;
}

.toc-wrap { page-break-after: always; }
.toc-wrap h1 {
    font-size: 22pt;
    margin: 0 0 16pt 0;
    padding-bottom: 8pt;
    border-bottom: 3px solid #3f51b5;
    color: #1a237e;
}
.toc-wrap ol { padding-left: 20pt; line-height: 1.9; }
.toc-wrap li { font-size: 11pt; }
.toc-wrap .group { font-weight: 700; margin-top: 10pt; color: #1a237e; }

.page-break { page-break-before: always; }

.chapter-label {
    font-size: 9pt;
    color: #5f6368;
    letter-spacing: 2pt;
    text-transform: uppercase;
    margin-bottom: 6pt;
    padding-bottom: 4pt;
    border-bottom: 1px dashed #c7c9d1;
}

h1 {
    font-size: 20pt;
    color: #1a237e;
    border-bottom: 3px solid #3f51b5;
    padding-bottom: 6pt;
    margin: 18pt 0 14pt 0;
}

h2 {
    font-size: 15pt;
    color: #1a237e;
    margin: 18pt 0 10pt 0;
    padding-left: 10pt;
    border-left: 5px solid #3f51b5;
}

h3 {
    font-size: 12.5pt;
    color: #283593;
    margin: 14pt 0 8pt 0;
}

h4 { font-size: 11pt; color: #303f9f; margin: 10pt 0 6pt 0; }

p { margin: 6pt 0; }

ul, ol { padding-left: 20pt; margin: 6pt 0; }
li { margin: 2pt 0; }

table {
    border-collapse: collapse;
    width: 100%;
    margin: 10pt 0;
    font-size: 9.5pt;
    page-break-inside: avoid;
}
th, td {
    border: 1px solid #c7c9d1;
    padding: 6pt 8pt;
    vertical-align: top;
    text-align: left;
}
th { background: #eef1ff; color: #1a237e; font-weight: 700; }
tr:nth-child(even) td { background: #f8f9fc; }

code {
    font-family: 'JetBrains Mono', 'Fira Code', Consolas, 'Courier New', monospace;
    background: #f3f4f8;
    padding: 1pt 4pt;
    border-radius: 3px;
    font-size: 9.2pt;
    color: #b91c1c;
}

pre {
    background: #1e1e2e;
    color: #e0e0e0;
    padding: 10pt 12pt;
    border-radius: 6px;
    font-size: 8.8pt;
    line-height: 1.45;
    overflow-x: auto;
    page-break-inside: avoid;
    margin: 8pt 0;
}
pre code { background: transparent; color: inherit; padding: 0; font-size: inherit; }

blockquote {
    border-left: 4px solid #3f51b5;
    padding: 6pt 12pt;
    margin: 10pt 0;
    color: #455a64;
    background: #f5f6fb;
    font-style: italic;
}

hr { border: none; border-top: 1px solid #d0d4dc; margin: 12pt 0; }

a { color: #303f9f; text-decoration: none; }

.admonition {
    border: 1px solid #c7c9d1;
    border-left: 5px solid #3f51b5;
    border-radius: 4px;
    background: #f8f9fc;
    padding: 8pt 12pt;
    margin: 10pt 0;
    page-break-inside: avoid;
}
.admonition .admonition-title {
    font-weight: 700;
    color: #1a237e;
    margin-bottom: 4pt;
}
.admonition.note { border-left-color: #3f51b5; background: #eef1ff; }
.admonition.warning, .admonition.caution { border-left-color: #f57c00; background: #fff7e6; }
.admonition.danger, .admonition.error { border-left-color: #d32f2f; background: #ffebee; }
.admonition.tip, .admonition.hint { border-left-color: #2e7d32; background: #e8f5e9; }
.admonition.info { border-left-color: #0277bd; background: #e1f5fe; }

details {
    border: 1px solid #c7c9d1;
    border-radius: 4px;
    padding: 6pt 10pt;
    margin: 8pt 0;
    background: #fafbfd;
}
details > summary { font-weight: 600; cursor: pointer; color: #303f9f; }

img { max-width: 100%; height: auto; }

.tabbed-set { margin: 10pt 0; }
.tabbed-set input { display: none; }
.tabbed-set label {
    display: inline-block;
    padding: 4pt 10pt;
    margin-right: 4pt;
    border: 1px solid #c7c9d1;
    border-radius: 4px 4px 0 0;
    background: #eef1ff;
    font-size: 9pt;
    font-weight: 600;
    color: #1a237e;
}
.tabbed-content { border: 1px solid #c7c9d1; padding: 8pt 12pt; }

.chapter { page-break-inside: auto; }

/* Pygments syntax-highlight palette tuned for dark code blocks */
.highlight .k, .highlight .kn, .highlight .kd, .highlight .kr { color: #c792ea; }
.highlight .s, .highlight .s1, .highlight .s2, .highlight .sb { color: #c3e88d; }
.highlight .c, .highlight .c1, .highlight .cm { color: #7c8594; font-style: italic; }
.highlight .nb { color: #82aaff; }
.highlight .nf { color: #82aaff; }
.highlight .mi, .highlight .mf { color: #f78c6c; }
.highlight .o { color: #89ddff; }
"""


def build_toc() -> str:
    groups: list[tuple[str, list[str]]] = []
    current_group: tuple[str, list[str]] | None = None

    def start_group(label: str) -> None:
        nonlocal current_group
        current_group = (label, [])
        groups.append(current_group)

    for title, path in PAGES:
        if path.name == "index.md" and path.parent.name != "docs":
            start_group(title)
            continue
        if path.parent.name == "docs":
            if current_group is None or current_group[0] != "강의 개요":
                start_group("강의 개요")
            current_group[1].append(title)  # type: ignore[union-attr]
            continue
        if path.parent.name == "appendix":
            if current_group is None or current_group[0] != "부록":
                start_group("부록")
            current_group[1].append(title)  # type: ignore[union-attr]
            continue
        if current_group is None:
            start_group("강의 개요")
        current_group[1].append(title)  # type: ignore[union-attr]

    lines = ['<div class="toc-wrap"><h1>목차</h1><ol>']
    for group_label, items in groups:
        lines.append(f'<li class="group">{html.escape(group_label)}</li>')
        for item in items:
            lines.append(f"<li>{html.escape(item)}</li>")
    lines.append("</ol></div>")
    return "\n".join(lines)


def build_cover() -> str:
    return (
        '<div class="cover">'
        "<h1>AI 기반 SQL 분석 에이전트 구축</h1>"
        "<h2>24시간 집중 강의 · 4일 과정</h2>"
        '<div class="meta">'
        "자연어 질문 → SQL 생성 → 실행 → 검증 → 답변하는 <b>AI 에이전트</b>를 직접 만듭니다.<br/>"
        "PostgreSQL · LlamaIndex · ChromaDB · Vanna.ai · LangChain · LangGraph · LangSmith · Ragas · Gradio"
        "</div>"
        '<div style="margin-top:24pt;">'
        '<span class="tag">Day 1 — SQL · RAG</span>'
        '<span class="tag">Day 2 — Text-to-SQL</span>'
        '<span class="tag">Day 3 — LangGraph Agent</span>'
        '<span class="tag">Day 4 — 평가 · 발표</span>'
        "</div>"
        '<div class="meta" style="margin-top:28pt;">'
        "대상: 대학 Assist 집중강의 수강생 · 진행: Jaeyoo"
        "</div>"
        "</div>"
    )


def build_html() -> str:
    chunks = [build_cover(), build_toc()]
    for idx, (title, path) in enumerate(PAGES):
        if not path.exists():
            print(f"[warn] missing: {path}", file=sys.stderr)
            continue
        chunks.append(render_page(title, path, first=False))
    body = "\n".join(chunks)

    return (
        "<!DOCTYPE html>\n"
        '<html lang="ko"><head>'
        '<meta charset="utf-8"/>'
        "<title>AI 기반 SQL 분석 에이전트 구축 — 강의자료</title>"
        f"<style>{STYLESHEET}</style>"
        "</head><body>"
        f"{body}"
        "</body></html>"
    )


def wsl_to_windows_path(p: Path) -> str:
    """Convert /mnt/c/... or WSL path to Windows path with forward slashes."""
    s = str(p.resolve())
    if s.startswith("/mnt/"):
        drive = s[5]
        rest = s[6:]
        return f"{drive.upper()}:{rest}"
    # \\wsl.localhost\<distro>\... style for other paths
    distro = os.environ.get("WSL_DISTRO_NAME", "")
    if distro:
        return f"\\\\wsl.localhost\\{distro}{s}"
    return s


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("[1/3] rendering markdown...")
    html_str = build_html()
    OUT_HTML.write_text(html_str, encoding="utf-8")
    print(f"      wrote {OUT_HTML} ({len(html_str):,} chars)")

    html_win = wsl_to_windows_path(OUT_HTML)
    pdf_win = wsl_to_windows_path(OUT_PDF)
    print(f"[2/3] chrome → PDF\n      src: {html_win}\n      dst: {pdf_win}")

    cmd = [
        CHROME,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--no-pdf-header-footer",
        "--run-all-compositor-stages-before-draw",
        "--virtual-time-budget=10000",
        f"--print-to-pdf={pdf_win}",
        f"file:///{html_win.replace(chr(92), '/')}",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if res.returncode != 0:
        print("chrome stdout:", res.stdout)
        print("chrome stderr:", res.stderr)
        return res.returncode

    if not OUT_PDF.exists():
        print("[error] PDF not produced", file=sys.stderr)
        return 1
    size = OUT_PDF.stat().st_size
    print(f"[3/3] done → {OUT_PDF} ({size:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
