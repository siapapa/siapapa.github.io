"""Build PowerPoint decks (one per Day) from the mkdocs source markdown.

For each lecture markdown file we parse a tiny subset of markdown:
  # H1 / ## H2 / ### H3 / #### H4   → slide titles or sub-section breaks
  - / *  list items                  → bullet points
  fenced code (``` … ```)             → code-style monospace slide
  | table |                           → PPT table
  blockquotes ( > … )                 → callout block
  paragraphs                          → body text

Slides are paginated: each H2 starts a fresh slide; long bullet lists / code
blocks are auto-split into continuation slides ("(이어서)"). The result is one
.pptx per Day, plus a thin index slide deck for the cover.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt, Emu

REPO = Path("/home/totorokr/Assist 강의")
DOCS = REPO / "docs"
OUT_DIR = REPO / "dist"

# 16:9 deck — width 13.333", height 7.5"
SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)

# Brand palette (matches mkdocs-material indigo/amber theme).
PRIMARY = RGBColor(0x1A, 0x23, 0x7E)        # deep indigo
ACCENT = RGBColor(0xFF, 0xC1, 0x07)         # amber
INK = RGBColor(0x21, 0x25, 0x2B)
SUBTLE = RGBColor(0x5F, 0x6B, 0x7A)
BG_SOFT = RGBColor(0xF5, 0xF6, 0xFB)
CODE_BG = RGBColor(0x1E, 0x1E, 0x2E)
CODE_FG = RGBColor(0xE0, 0xE0, 0xE0)
BORDER = RGBColor(0xC7, 0xC9, 0xD1)
QUOTE_BG = RGBColor(0xEE, 0xF1, 0xFF)

KO_FONT = "Malgun Gothic"
CODE_FONT = "Consolas"

DAYS: list[tuple[str, str, str, list[Path]]] = [
    (
        "Day1",
        "Day 1 — SQL · RAG · 프로젝트 (1~8H)",
        "PostgreSQL · LlamaIndex · ChromaDB · Text-to-SQL · 프로젝트 브리핑",
        [
            DOCS / "index.md",
            DOCS / "setup.md",
            DOCS / "day1/index.md",
            DOCS / "day1/01-ot-demo.md",
            DOCS / "day1/02-postgres-basics.md",
            DOCS / "day1/03-sql-advanced.md",
            DOCS / "day1/04-schema-intelligence.md",
            DOCS / "day1/05-llamaindex-intro.md",
            DOCS / "day1/06-embedding-chromadb.md",
            DOCS / "day1/07-text-to-sql.md",
            DOCS / "day1/08-project-briefing.md",
        ],
    ),
    (
        "Day2",
        "Day 2 — Text-to-SQL 상담사 (9~12H)",
        "프롬프트 튜닝 · 멀티턴 대화 · Gradio UI · 제안서 회수",
        [
            DOCS / "day2/index.md",
            DOCS / "day2/09-peer-review.md",
            DOCS / "day2/10-text-to-sql-advanced.md",
            DOCS / "day2/11-multiturn-chatbot.md",
            DOCS / "day2/12-gradio-ui.md",
        ],
    ),
    (
        "Day3",
        "Day 3 — Vanna · LangChain · LangGraph (13~20H)",
        "LCEL · Advanced RAG · LangGraph SQL Agent",
        [
            DOCS / "day3/index.md",
            DOCS / "day3/13-vanna-intro.md",
            DOCS / "day3/14-vanna-training.md",
            DOCS / "day3/15-langchain-lcel.md",
            DOCS / "day3/16-lcel-rag-chain.md",
            DOCS / "day3/17-advanced-rag-query.md",
            DOCS / "day3/18-advanced-rag-retrieval.md",
            DOCS / "day3/19-langgraph-concept.md",
            DOCS / "day3/20-sql-agent-build.md",
        ],
    ),
    (
        "Day4",
        "Day 4 — 평가 · 발표 (21~24H)",
        "LangSmith · Ragas · 최종 발표 & 수료",
        [
            DOCS / "day4/index.md",
            DOCS / "day4/21-langsmith.md",
            DOCS / "day4/22-ragas-eval.md",
            DOCS / "day4/23-final-tuning.md",
            DOCS / "day4/24-final-presentation.md",
            DOCS / "appendix/notebook-numbering.md",
            DOCS / "appendix/troubleshooting.md",
            DOCS / "appendix/project-brief.md",
        ],
    ),
]

FRONT_MATTER_RE = re.compile(r"\A---\s*\n.*?\n---\s*\n", re.DOTALL)
ICON_RE = re.compile(r":(?:material|fontawesome|octicons|simple)-[a-z0-9-]+:")
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
EMPH_RE = re.compile(r"\*\*([^*]+)\*\*|\*([^*]+)\*|`([^`]+)`")
HTML_TAG_RE = re.compile(r"<[^>]+>")
ATTR_LIST_RE = re.compile(r"\{[^{}]*\}\s*$")


@dataclass
class Block:
    kind: str  # "h1" "h2" "h3" "h4" "p" "ul" "ol" "code" "quote" "table"
    text: str = ""
    items: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)
    lang: str = ""


def clean_inline(text: str) -> str:
    """Strip inline markdown that doesn't translate to plain runs."""
    text = ICON_RE.sub("", text)
    text = HTML_TAG_RE.sub("", text)
    # Replace [label](url) → label
    text = LINK_RE.sub(r"\1", text)
    # Strip emphasis markers but keep the inner text
    text = EMPH_RE.sub(lambda m: m.group(1) or m.group(2) or m.group(3) or "", text)
    text = ATTR_LIST_RE.sub("", text)
    return text.strip()


def parse_markdown(raw: str) -> list[Block]:
    raw = FRONT_MATTER_RE.sub("", raw)
    lines = raw.splitlines()
    blocks: list[Block] = []

    i = 0
    in_code = False
    code_buf: list[str] = []
    code_lang = ""
    para_buf: list[str] = []
    list_buf: list[str] = []
    list_kind = ""  # "ul" or "ol"
    quote_buf: list[str] = []
    table_buf: list[list[str]] = []

    def flush_para() -> None:
        nonlocal para_buf
        if para_buf:
            text = clean_inline(" ".join(para_buf).strip())
            if text:
                blocks.append(Block("p", text=text))
            para_buf = []

    def flush_list() -> None:
        nonlocal list_buf, list_kind
        if list_buf:
            blocks.append(Block(list_kind, items=[clean_inline(x) for x in list_buf]))
            list_buf = []
            list_kind = ""

    def flush_quote() -> None:
        nonlocal quote_buf
        if quote_buf:
            text = clean_inline(" ".join(quote_buf).strip())
            if text:
                blocks.append(Block("quote", text=text))
            quote_buf = []

    def flush_table() -> None:
        nonlocal table_buf
        if table_buf:
            cleaned: list[list[str]] = []
            for row in table_buf:
                # Skip the alignment separator row (e.g. ---|:--:|----)
                if all(re.match(r"^:?-+:?$", c.strip()) for c in row if c.strip()):
                    continue
                cleaned.append([clean_inline(c) for c in row])
            if cleaned:
                blocks.append(Block("table", rows=cleaned))
            table_buf = []

    def flush_all() -> None:
        flush_para()
        flush_list()
        flush_quote()
        flush_table()

    while i < len(lines):
        line = lines[i]

        if in_code:
            if line.strip().startswith("```"):
                blocks.append(Block("code", text="\n".join(code_buf), lang=code_lang))
                code_buf = []
                code_lang = ""
                in_code = False
            else:
                code_buf.append(line)
            i += 1
            continue

        stripped = line.strip()

        if stripped.startswith("```") or stripped.startswith("~~~"):
            flush_all()
            in_code = True
            code_lang = stripped[3:].strip()
            i += 1
            continue

        if not stripped:
            flush_para()
            flush_list()
            flush_quote()
            flush_table()
            i += 1
            continue

        # Heading
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            flush_all()
            level = len(m.group(1))
            text = clean_inline(m.group(2))
            kind = f"h{min(level, 4)}"
            blocks.append(Block(kind, text=text))
            i += 1
            continue

        # Horizontal rule
        if re.match(r"^(-{3,}|\*{3,}|_{3,})$", stripped):
            flush_all()
            i += 1
            continue

        # Blockquote
        if stripped.startswith(">"):
            flush_para()
            flush_list()
            flush_table()
            quote_buf.append(stripped.lstrip("> ").rstrip())
            i += 1
            continue

        # Table row
        if stripped.startswith("|") and stripped.endswith("|"):
            flush_para()
            flush_list()
            flush_quote()
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            table_buf.append(cells)
            i += 1
            continue

        # Unordered list
        m = re.match(r"^([-*+])\s+(.*)$", line)
        if m:
            flush_para()
            flush_quote()
            flush_table()
            if list_kind and list_kind != "ul":
                flush_list()
            list_kind = "ul"
            list_buf.append(m.group(2))
            i += 1
            continue
        # Ordered list
        m = re.match(r"^\d+\.\s+(.*)$", line)
        if m:
            flush_para()
            flush_quote()
            flush_table()
            if list_kind and list_kind != "ol":
                flush_list()
            list_kind = "ol"
            list_buf.append(m.group(1))
            i += 1
            continue
        # Continuation of list item (indented under previous bullet)
        if list_buf and (line.startswith("  ") or line.startswith("\t")):
            list_buf[-1] = list_buf[-1] + " " + stripped
            i += 1
            continue

        flush_list()
        flush_quote()
        flush_table()
        para_buf.append(stripped)
        i += 1

    flush_all()
    return blocks


def add_textbox(slide, x: Emu, y: Emu, w: Emu, h: Emu, text: str, *, size: int, bold: bool = False,
                color: RGBColor = INK, font: str = KO_FONT, align=PP_ALIGN.LEFT,
                anchor=MSO_ANCHOR.TOP) -> None:
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = Emu(0)
    tf.margin_right = Emu(0)
    tf.margin_top = Emu(0)
    tf.margin_bottom = Emu(0)
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.name = font
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color


def add_solid(slide, x, y, w, h, color: RGBColor) -> None:
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, y, w, h)
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()
    shape.shadow.inherit = False


def make_blank_slide(prs: Presentation):
    blank_layout = prs.slide_layouts[6]
    return prs.slides.add_slide(blank_layout)


def add_header_footer(slide, *, day_label: str, footer: str) -> None:
    # Top accent bar
    add_solid(slide, Emu(0), Emu(0), SLIDE_W, Inches(0.18), PRIMARY)
    # Day label top-right
    add_textbox(
        slide, Inches(10.5), Inches(0.25), Inches(2.6), Inches(0.35),
        day_label, size=10, color=SUBTLE, align=PP_ALIGN.RIGHT,
    )
    # Footer line
    add_solid(slide, Inches(0.5), Inches(7.10), Inches(12.333), Emu(9525), BORDER)
    add_textbox(
        slide, Inches(0.5), Inches(7.18), Inches(9.0), Inches(0.30),
        footer, size=9, color=SUBTLE,
    )
    add_textbox(
        slide, Inches(10.0), Inches(7.18), Inches(2.83), Inches(0.30),
        "AI 기반 SQL 분석 에이전트 구축", size=9, color=SUBTLE, align=PP_ALIGN.RIGHT,
    )


# ---------------------------------------------------------------------------
# Slide builders
# ---------------------------------------------------------------------------

def cover_slide(prs: Presentation, day_label: str, title: str, subtitle: str) -> None:
    slide = make_blank_slide(prs)
    add_solid(slide, Emu(0), Emu(0), SLIDE_W, SLIDE_H, PRIMARY)
    add_solid(slide, Emu(0), Inches(6.6), SLIDE_W, Inches(0.9), ACCENT)

    add_textbox(
        slide, Inches(0.7), Inches(1.2), Inches(12.0), Inches(0.6),
        "AI 기반 SQL 분석 에이전트 구축", size=20, color=ACCENT,
    )
    add_textbox(
        slide, Inches(0.7), Inches(1.9), Inches(12.0), Inches(2.0),
        title, size=44, bold=True, color=RGBColor(0xFF, 0xFF, 0xFF),
    )
    add_textbox(
        slide, Inches(0.7), Inches(4.4), Inches(12.0), Inches(1.0),
        subtitle, size=18, color=RGBColor(0xE8, 0xEA, 0xF6),
    )
    add_textbox(
        slide, Inches(0.7), Inches(5.4), Inches(12.0), Inches(0.6),
        "24시간 집중 강의 · 4일 과정 · " + day_label,
        size=14, color=RGBColor(0xC5, 0xCA, 0xE9),
    )
    add_textbox(
        slide, Inches(0.7), Inches(6.75), Inches(12.0), Inches(0.5),
        "PostgreSQL · LlamaIndex · ChromaDB · Vanna · LangChain · LangGraph · LangSmith · Ragas · Gradio",
        size=11, color=PRIMARY, align=PP_ALIGN.LEFT,
    )


def section_divider(prs: Presentation, day_label: str, footer: str, label: str, title: str) -> None:
    slide = make_blank_slide(prs)
    add_solid(slide, Emu(0), Emu(0), SLIDE_W, SLIDE_H, BG_SOFT)
    add_solid(slide, Inches(0.7), Inches(2.5), Inches(0.18), Inches(2.5), ACCENT)
    add_textbox(
        slide, Inches(1.1), Inches(2.5), Inches(11.5), Inches(0.6),
        label, size=16, color=SUBTLE,
    )
    add_textbox(
        slide, Inches(1.1), Inches(3.1), Inches(11.5), Inches(2.0),
        title, size=40, bold=True, color=PRIMARY,
    )
    add_header_footer(slide, day_label=day_label, footer=footer)


def title_only_slide(prs: Presentation, day_label: str, footer: str, title: str, subtitle: str = "") -> "Slide":
    slide = make_blank_slide(prs)
    add_solid(slide, Emu(0), Emu(0), SLIDE_W, SLIDE_H, RGBColor(0xFF, 0xFF, 0xFF))
    add_header_footer(slide, day_label=day_label, footer=footer)

    add_textbox(
        slide, Inches(0.6), Inches(0.55), Inches(12.0), Inches(0.6),
        title, size=24, bold=True, color=PRIMARY,
    )
    add_solid(slide, Inches(0.6), Inches(1.18), Inches(12.0), Emu(38100), ACCENT)
    if subtitle:
        add_textbox(
            slide, Inches(0.6), Inches(1.30), Inches(12.0), Inches(0.4),
            subtitle, size=12, color=SUBTLE,
        )
    return slide


# ---------------------------------------------------------------------------
# Slide content fillers
# ---------------------------------------------------------------------------

CONTENT_TOP = Inches(1.85)
CONTENT_LEFT = Inches(0.6)
CONTENT_WIDTH = Inches(12.133)
CONTENT_HEIGHT = Inches(5.10)


def add_bullets(slide, items: list[str], *, level0_size: int = 16, sub_size: int = 13,
                ordered: bool = False) -> None:
    tb = slide.shapes.add_textbox(CONTENT_LEFT, CONTENT_TOP, CONTENT_WIDTH, CONTENT_HEIGHT)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = Emu(0); tf.margin_right = Emu(0)
    tf.margin_top = Emu(0); tf.margin_bottom = Emu(0)
    first = True
    for idx, item in enumerate(items):
        if first:
            p = tf.paragraphs[0]
            first = False
        else:
            p = tf.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        p.space_after = Pt(6)
        bullet = f"{idx+1}. " if ordered else "• "
        run = p.add_run()
        run.text = bullet + item
        run.font.name = KO_FONT
        run.font.size = Pt(level0_size)
        run.font.color.rgb = INK


def add_paragraph_block(slide, text: str, *, top: Emu | None = None, height: Emu | None = None) -> None:
    tb = slide.shapes.add_textbox(
        CONTENT_LEFT, top or CONTENT_TOP, CONTENT_WIDTH, height or CONTENT_HEIGHT,
    )
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = Emu(0); tf.margin_right = Emu(0)
    tf.margin_top = Emu(0); tf.margin_bottom = Emu(0)
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = text
    run.font.name = KO_FONT
    run.font.size = Pt(15)
    run.font.color.rgb = INK


def add_code_box(slide, code: str, lang: str = "") -> None:
    add_solid(slide, CONTENT_LEFT, CONTENT_TOP, CONTENT_WIDTH, CONTENT_HEIGHT, CODE_BG)
    if lang:
        add_textbox(
            slide, CONTENT_LEFT + Inches(0.15), CONTENT_TOP + Inches(0.10),
            Inches(3.0), Inches(0.30), lang, size=10,
            color=RGBColor(0x9F, 0xA8, 0xDA),
        )
    tb = slide.shapes.add_textbox(
        CONTENT_LEFT + Inches(0.20),
        CONTENT_TOP + (Inches(0.45) if lang else Inches(0.20)),
        CONTENT_WIDTH - Inches(0.40),
        CONTENT_HEIGHT - (Inches(0.55) if lang else Inches(0.30)),
    )
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = Emu(0); tf.margin_right = Emu(0)
    tf.margin_top = Emu(0); tf.margin_bottom = Emu(0)
    first = True
    # Heuristic font sizing based on density.
    line_count = max(1, code.count("\n") + 1)
    max_line_len = max((len(l) for l in code.splitlines()), default=20)
    if line_count >= 22 or max_line_len >= 110:
        size = 9
    elif line_count >= 16 or max_line_len >= 85:
        size = 10
    elif line_count >= 12 or max_line_len >= 70:
        size = 11
    else:
        size = 12
    for line in code.splitlines() or [""]:
        if first:
            p = tf.paragraphs[0]
            first = False
        else:
            p = tf.add_paragraph()
        p.space_after = Pt(0)
        run = p.add_run()
        run.text = line if line else " "
        run.font.name = CODE_FONT
        run.font.size = Pt(size)
        run.font.color.rgb = CODE_FG


def add_quote_box(slide, text: str) -> None:
    add_solid(slide, CONTENT_LEFT, CONTENT_TOP, CONTENT_WIDTH, CONTENT_HEIGHT, QUOTE_BG)
    add_solid(slide, CONTENT_LEFT, CONTENT_TOP, Inches(0.10), CONTENT_HEIGHT, PRIMARY)
    tb = slide.shapes.add_textbox(
        CONTENT_LEFT + Inches(0.30), CONTENT_TOP + Inches(0.30),
        CONTENT_WIDTH - Inches(0.60), CONTENT_HEIGHT - Inches(0.60),
    )
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = text
    run.font.name = KO_FONT
    run.font.size = Pt(16)
    run.font.italic = True
    run.font.color.rgb = PRIMARY


def add_table(slide, rows: list[list[str]]) -> None:
    if not rows:
        return
    n_cols = max(len(r) for r in rows)
    rows = [r + [""] * (n_cols - len(r)) for r in rows]
    n_rows = len(rows)

    height = min(CONTENT_HEIGHT, Inches(0.45) + Inches(0.40) * n_rows)
    table_shape = slide.shapes.add_table(
        n_rows, n_cols,
        CONTENT_LEFT, CONTENT_TOP, CONTENT_WIDTH, height,
    )
    tbl = table_shape.table

    # Even column widths.
    col_w = int(CONTENT_WIDTH / n_cols)
    for c in range(n_cols):
        tbl.columns[c].width = col_w

    # Heuristic font sizing
    cell_lens = [max(len(c) for c in row) for row in rows]
    avg_len = sum(cell_lens) / max(1, len(cell_lens))
    if n_rows > 12 or avg_len > 22:
        size = 10
    elif n_rows > 8 or avg_len > 14:
        size = 12
    else:
        size = 13

    for r_idx, row in enumerate(rows):
        for c_idx, value in enumerate(row):
            cell = tbl.cell(r_idx, c_idx)
            cell.fill.solid()
            cell.fill.fore_color.rgb = PRIMARY if r_idx == 0 else (
                RGBColor(0xFF, 0xFF, 0xFF) if r_idx % 2 == 1 else BG_SOFT
            )
            tf = cell.text_frame
            tf.word_wrap = True
            tf.margin_left = Emu(50000); tf.margin_right = Emu(50000)
            tf.margin_top = Emu(20000); tf.margin_bottom = Emu(20000)
            p = tf.paragraphs[0]
            run = p.add_run()
            run.text = value
            run.font.name = KO_FONT
            run.font.size = Pt(size)
            run.font.bold = (r_idx == 0)
            run.font.color.rgb = (
                RGBColor(0xFF, 0xFF, 0xFF) if r_idx == 0 else INK
            )


# ---------------------------------------------------------------------------
# Pagination logic
# ---------------------------------------------------------------------------

# Approximate budget per slide for bullet groups.
MAX_BULLET_LINES = 9   # number of top-level bullets per slide
MAX_CODE_LINES = 26    # split very long fences across slides
MAX_TABLE_ROWS = 13


def chunk_list(items: list[str], size: int) -> Iterable[list[str]]:
    for i in range(0, len(items), size):
        yield items[i:i + size]


def chunk_table(rows: list[list[str]], size: int) -> Iterable[list[list[str]]]:
    if len(rows) <= 1:
        yield rows
        return
    header = rows[0]
    body = rows[1:]
    for i in range(0, len(body), size):
        yield [header] + body[i:i + size]


def chunk_code(code: str, size: int) -> Iterable[str]:
    lines = code.splitlines()
    if len(lines) <= size:
        yield code
        return
    for i in range(0, len(lines), size):
        yield "\n".join(lines[i:i + size])


# ---------------------------------------------------------------------------
# Slide flow per markdown file
# ---------------------------------------------------------------------------

@dataclass
class FileMeta:
    path: Path
    label: str  # e.g. "01H. OT & 전체 데모"
    file_title: str  # H1 from markdown (or fallback to label)


def derive_label(path: Path) -> str:
    name = path.stem
    if name == "index" and path.parent.name == "docs":
        return "과정 개요"
    if name == "setup":
        return "사전 준비"
    if name == "index":
        parent = path.parent.name
        return {
            "day1": "Day 1 — 개관",
            "day2": "Day 2 — 개관",
            "day3": "Day 3 — 개관",
            "day4": "Day 4 — 개관",
        }.get(parent, parent)
    if path.parent.name == "appendix":
        readable = {
            "notebook-numbering": "부록 — 노트북 번호 체계",
            "troubleshooting": "부록 — 트러블슈팅",
            "project-brief": "부록 — 프로젝트 브리프",
        }.get(name, f"부록 — {name}")
        return readable
    # day1/01-ot-demo → "01H. OT 데모" fallback uses filename
    m = re.match(r"^(\d{2})-(.+)$", name)
    if m:
        readable = m.group(2).replace("-", " ").title()
        return f"{int(m.group(1))}H. {readable}"
    return name


def add_file_slides(prs: Presentation, day_label: str, footer: str, meta: FileMeta) -> None:
    blocks = parse_markdown(meta.path.read_text(encoding="utf-8"))

    # Section divider for the file.
    section_divider(prs, day_label, footer, meta.label, meta.file_title or meta.label)

    # Walk blocks. Each H2 starts a new slide. Collect a buffer of "current
    # slide content blocks" and flush whenever we hit a slide boundary or a
    # block that needs its own dedicated slide (code/table beyond a certain
    # size).
    current_title = meta.file_title or meta.label
    current_subtitle = ""
    pending: list[Block] = []
    section_index = 0

    def emit_pending(title: str, subtitle: str) -> None:
        if not pending:
            return
        # If the only block is one big code/table, flush directly.
        groups = list(group_blocks_for_slides(pending))
        for idx, group in enumerate(groups):
            slide_title = title if idx == 0 else f"{title} (이어서)"
            slide = title_only_slide(prs, day_label, footer, slide_title, subtitle if idx == 0 else "")
            render_blocks(slide, group)
        pending.clear()

    # Skip the file's H1 if it just repeats the label.
    seen_h1 = False

    for blk in blocks:
        if blk.kind == "h1":
            if not seen_h1:
                seen_h1 = True
                if blk.text and blk.text != meta.label:
                    current_title = blk.text
                continue
            # Subsequent H1 inside one file → treat like H2.
            blk = Block("h2", text=blk.text)

        if blk.kind == "h2":
            emit_pending(current_title, current_subtitle)
            section_index += 1
            current_title = blk.text or current_title
            current_subtitle = ""
            continue

        if blk.kind == "h3":
            # Use as in-slide subsection; flush slide if buffer non-empty.
            emit_pending(current_title, current_subtitle)
            current_subtitle = blk.text
            continue

        pending.append(blk)

    emit_pending(current_title, current_subtitle)


def group_blocks_for_slides(blocks: list[Block]) -> Iterable[list[Block]]:
    """Bin blocks into groups that fit on a single slide.

    Heuristic: a slide either holds (a) one big visual element — code, table,
    quote, h4-led mini-section — or (b) a mixed group of small bullets +
    paragraphs. We split lists/code/tables that exceed per-slide caps.
    """
    buf: list[Block] = []

    def buf_weight() -> int:
        w = 0
        for b in buf:
            if b.kind in ("ul", "ol"):
                w += len(b.items)
            elif b.kind == "p":
                w += 2
            elif b.kind == "h4":
                w += 1
            elif b.kind == "quote":
                w += 4
        return w

    def flush() -> Iterable[list[Block]]:
        nonlocal buf
        if buf:
            yield buf
            buf = []

    for blk in blocks:
        if blk.kind == "code":
            yield from flush()
            for chunk in chunk_code(blk.text, MAX_CODE_LINES):
                yield [Block("code", text=chunk, lang=blk.lang)]
            continue
        if blk.kind == "table":
            yield from flush()
            for chunk in chunk_table(blk.rows, MAX_TABLE_ROWS):
                yield [Block("table", rows=chunk)]
            continue
        if blk.kind == "quote":
            yield from flush()
            yield [blk]
            continue
        if blk.kind in ("ul", "ol") and len(blk.items) > MAX_BULLET_LINES:
            yield from flush()
            for chunk in chunk_list(blk.items, MAX_BULLET_LINES):
                yield [Block(blk.kind, items=chunk)]
            continue

        # Otherwise add to buffer; flush if too heavy.
        if buf_weight() + (len(blk.items) if blk.kind in ("ul", "ol") else 2) > MAX_BULLET_LINES + 4:
            yield from flush()
        buf.append(blk)

    yield from flush()


def render_blocks(slide, blocks: list[Block]) -> None:
    """Render a small group of blocks onto a single slide."""
    if not blocks:
        return
    if len(blocks) == 1:
        b = blocks[0]
        if b.kind == "code":
            add_code_box(slide, b.text, b.lang); return
        if b.kind == "table":
            add_table(slide, b.rows); return
        if b.kind == "quote":
            add_quote_box(slide, b.text); return
        if b.kind in ("ul", "ol"):
            add_bullets(slide, b.items, ordered=(b.kind == "ol")); return
        if b.kind == "p":
            add_paragraph_block(slide, b.text); return
        if b.kind == "h4":
            add_paragraph_block(slide, b.text); return

    # Mixed content: stack vertically. Allocate proportional space.
    total_weight = 0
    weights: list[int] = []
    for b in blocks:
        if b.kind in ("ul", "ol"):
            w = max(2, len(b.items))
        elif b.kind == "p":
            w = max(2, min(6, len(b.text) // 60 + 1))
        elif b.kind == "h4":
            w = 1
        elif b.kind == "quote":
            w = 4
        else:
            w = 3
        weights.append(w)
        total_weight += w

    cur_y = CONTENT_TOP
    for blk, w in zip(blocks, weights):
        h = Emu(int(int(CONTENT_HEIGHT) * w / total_weight))
        if blk.kind == "h4":
            tb = slide.shapes.add_textbox(CONTENT_LEFT, cur_y, CONTENT_WIDTH, Inches(0.40))
            tf = tb.text_frame; tf.word_wrap = True
            tf.margin_left = Emu(0); tf.margin_right = Emu(0)
            tf.margin_top = Emu(0); tf.margin_bottom = Emu(0)
            p = tf.paragraphs[0]
            run = p.add_run()
            run.text = "▸ " + blk.text
            run.font.name = KO_FONT
            run.font.size = Pt(15)
            run.font.bold = True
            run.font.color.rgb = PRIMARY
            cur_y = cur_y + Inches(0.45)
            continue
        if blk.kind == "p":
            tb = slide.shapes.add_textbox(CONTENT_LEFT, cur_y, CONTENT_WIDTH, h)
            tf = tb.text_frame; tf.word_wrap = True
            tf.margin_left = Emu(0); tf.margin_right = Emu(0)
            tf.margin_top = Emu(0); tf.margin_bottom = Emu(0)
            p = tf.paragraphs[0]
            run = p.add_run()
            run.text = blk.text
            run.font.name = KO_FONT
            run.font.size = Pt(13)
            run.font.color.rgb = INK
            cur_y = cur_y + h
            continue
        if blk.kind in ("ul", "ol"):
            tb = slide.shapes.add_textbox(CONTENT_LEFT, cur_y, CONTENT_WIDTH, h)
            tf = tb.text_frame; tf.word_wrap = True
            tf.margin_left = Emu(0); tf.margin_right = Emu(0)
            tf.margin_top = Emu(0); tf.margin_bottom = Emu(0)
            for i, item in enumerate(blk.items):
                p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
                p.space_after = Pt(2)
                run = p.add_run()
                run.text = (f"{i+1}. " if blk.kind == "ol" else "• ") + item
                run.font.name = KO_FONT
                run.font.size = Pt(13)
                run.font.color.rgb = INK
            cur_y = cur_y + h
            continue
        if blk.kind == "quote":
            add_solid(slide, CONTENT_LEFT, cur_y, CONTENT_WIDTH, h, QUOTE_BG)
            add_solid(slide, CONTENT_LEFT, cur_y, Inches(0.08), h, PRIMARY)
            tb = slide.shapes.add_textbox(
                CONTENT_LEFT + Inches(0.25), cur_y + Inches(0.10),
                CONTENT_WIDTH - Inches(0.50), h - Inches(0.20),
            )
            tf = tb.text_frame; tf.word_wrap = True
            p = tf.paragraphs[0]
            run = p.add_run()
            run.text = blk.text
            run.font.name = KO_FONT
            run.font.size = Pt(12)
            run.font.italic = True
            run.font.color.rgb = PRIMARY
            cur_y = cur_y + h
            continue


# ---------------------------------------------------------------------------
# Build per-day deck
# ---------------------------------------------------------------------------

def build_day(name: str, title: str, subtitle: str, files: list[Path]) -> Path:
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H

    cover_slide(prs, day_label=name, title=title, subtitle=subtitle)

    # Mini-TOC slide with one bullet per file.
    metas: list[FileMeta] = []
    for path in files:
        if not path.exists():
            print(f"  [warn] missing: {path}", file=sys.stderr)
            continue
        raw = path.read_text(encoding="utf-8")
        # Try to grab the first H1 as a friendlier title.
        m = re.search(r"^#\s+(.+)$", FRONT_MATTER_RE.sub("", raw), re.MULTILINE)
        file_title = clean_inline(m.group(1)) if m else ""
        metas.append(FileMeta(path=path, label=derive_label(path), file_title=file_title))

    slide = title_only_slide(prs, name, title, "목차", subtitle)
    add_bullets(slide, [f"{m.label} — {m.file_title}" if m.file_title and m.file_title != m.label else m.label
                        for m in metas], level0_size=15)

    for meta in metas:
        add_file_slides(prs, day_label=name, footer=title, meta=meta)

    out = OUT_DIR / f"AI기반_SQL_분석_에이전트_구축_{name}.pptx"
    prs.save(out)
    return out


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, title, subtitle, files in DAYS:
        print(f"[build] {name} — {len(files)} files")
        out = build_day(name, title, subtitle, files)
        size = out.stat().st_size
        print(f"        wrote {out.name} ({size:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
