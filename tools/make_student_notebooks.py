"""Build student-facing notebooks by stripping the solution code from the
"실습 과제" exercise cell of each instructor notebook.

Output directory: /home/totorokr/Assist 강의/notebooks_student/
"""

from pathlib import Path
import re
import shutil
import sys

import nbformat

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "notebooks"
DST = ROOT / "notebooks_student"

EXERCISE_RE = re.compile(r"실습\s*과제")

# Keep lines that serve as task headers / separators / pure description.
# Everything else in the exercise code cell is treated as solution and stripped.
KEEP_LINE_PATTERNS = [
    re.compile(r"^#\s*TODO", re.IGNORECASE),
    re.compile(r"^#\s*\d+\s*[\.\)]"),                   # "# 1)" / "# 2."
    re.compile(r"^#\s*[=\-─━]{3,}"),                     # separator rulers
    re.compile(r"^#\s*(힌트|참고|목표|출력|입력|예시|설명)\b"),
    re.compile(r"^#\s*={2,}\s*$"),
]

# Fast check: does the content look like actual code (SQL / Python)?
CODE_TOKEN_RE = re.compile(
    r"\b("
    r"SELECT|FROM|WHERE|GROUP\s+BY|ORDER\s+BY|HAVING|JOIN|LIMIT|WITH|UNION|"
    r"CREATE|INSERT|UPDATE|DELETE|ALTER|DROP|"
    r"import|from|def|class|return|if\s|else:|elif\s|for\s|while\s|try:|except|with\s|lambda|"
    r"print\s*\(|range\s*\("
    r")",
    re.IGNORECASE,
)
ASSIGN_RE = re.compile(r"^\s*[A-Za-z_][A-Za-z0-9_\.\[\]]*\s*=\s*")
CALL_RE = re.compile(r"\b[A-Za-z_]\w*\s*\(")


WHITELIST_RE = re.compile(
    r"^(TODO|\d+\s*[\.\)]|[=\-─━]{3,}|"
    r"힌트|참고|목표|출력|입력|예시|설명|문제|과제|주의)",
    re.IGNORECASE,
)


def is_keeper(line: str) -> bool:
    """Strict whitelist: keep only lines that are clearly task headers,
    sub-task numbering, separators, or hint/note labels. Strip every other
    line in an exercise cell — even if it looks like plain Korean, because
    code fragments (string literals, brackets, etc.) often don't contain
    recognizable code tokens yet still leak the solution shape.
    """
    stripped = line.strip()
    if not stripped:
        return True  # preserve one blank; runs are collapsed upstream
    if not stripped.startswith("#"):
        return False  # any raw code → strip
    content = stripped.lstrip("#").strip()
    if not content:
        return True
    return bool(WHITELIST_RE.match(content))


def strip_exercise_cell(source: str) -> str:
    """Transform an instructor exercise code cell into a student stub that
    keeps TODO / task headers but drops the filled-in implementation.
    """
    lines = source.splitlines()
    kept: list[str] = []
    prev_blank = False
    for line in lines:
        if is_keeper(line):
            # collapse runs of blank lines to a single blank
            if not line.strip():
                if prev_blank:
                    continue
                prev_blank = True
            else:
                prev_blank = False
            kept.append(line)
        else:
            # replace stripped solution block with a single placeholder (once
            # per contiguous stripped run)
            if kept and kept[-1] != "# 여기에 구현하세요.":
                kept.append("# 여기에 구현하세요.")
                prev_blank = False
    # trim trailing blanks
    while kept and not kept[-1].strip():
        kept.pop()
    # ensure the cell ends with a writable placeholder so the student has a
    # cursor target
    if not kept or kept[-1] != "# 여기에 구현하세요.":
        kept.append("")
        kept.append("# 여기에 구현하세요.")
    return "\n".join(kept)


def convert(nb_path: Path, out_path: Path) -> tuple[str, int, int]:
    nb = nbformat.read(str(nb_path), as_version=4)
    exercise_md_idx = -1
    for i, cell in enumerate(nb.cells):
        src = cell.source if isinstance(cell.source, str) else "".join(cell.source)
        if cell.cell_type == "markdown" and EXERCISE_RE.search(src):
            exercise_md_idx = i
            break
    stripped_cell_idx = -1
    if exercise_md_idx >= 0 and exercise_md_idx + 1 < len(nb.cells):
        follower = nb.cells[exercise_md_idx + 1]
        if follower.cell_type == "code":
            original = follower.source if isinstance(follower.source, str) else "".join(follower.source)
            new_source = strip_exercise_cell(original)
            follower.source = new_source
            stripped_cell_idx = exercise_md_idx + 1
    # Write
    nbformat.validate(nb)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(nb, str(out_path))
    return (nb_path.name, exercise_md_idx, stripped_cell_idx)


def main() -> int:
    if not SRC.is_dir():
        print(f"Source directory not found: {SRC}", file=sys.stderr)
        return 1
    DST.mkdir(exist_ok=True)
    summary = []
    for p in sorted(SRC.glob("*.ipynb")):
        out = DST / p.name
        name, md_idx, code_idx = convert(p, out)
        summary.append((name, md_idx, code_idx))
    print(f"{'notebook':<40} {'md_idx':>8} {'code_idx':>8}")
    for name, md_idx, code_idx in summary:
        print(f"{name:<40} {md_idx:>8} {code_idx:>8}")
    print(f"\nTotal: {len(summary)} notebooks written to {DST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
