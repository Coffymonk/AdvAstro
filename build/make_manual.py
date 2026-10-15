#!/usr/bin/env python3
"""Make the user manual as PDF files, one per language, from the help chapters.

    python build/make_manual.py            # all languages -> dist/
    python build/make_manual.py --lang sv  # only Swedish

Needs:  pip install markdown playwright  and  python -m playwright install chromium
The PDFs are printed by Chromium, with a cover page, a table of contents and page numbers.
The text is the same as the manual inside the app (src/advastro/help/<lang>/*.md).
"""

from __future__ import annotations

import argparse
import base64
import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
sys.path.insert(0, str(ROOT / "src"))

from advastro import APP_NAME, __version__  # noqa: E402
from advastro import help as manual  # noqa: E402

TEXT = {
    "en": {"title": "User manual", "contents": "Contents", "version": "Version",
           "file": "AdvancedAstrophotoAnalyzer-{v}-manual-en.pdf",
           "copy": "Copyright © 2026 Miklosoft. Released under the GNU General Public License "
                   "v3.0. See LICENSE in the AdvAstro repository on GitHub."},
    "sv": {"title": "Användarmanual", "contents": "Innehåll", "version": "Version",
           "file": "AdvancedAstrophotoAnalyzer-{v}-manual-sv.pdf",
           "copy": "Copyright © 2026 Miklosoft. Släppt under GNU General Public License v3.0. "
                   "Se LICENSE i AdvAstro-förrådet på GitHub."},
}

CSS = """
@page { size: A4; margin: 20mm 18mm 20mm 18mm; }
body { font-family: 'Segoe UI', 'Helvetica Neue', 'DejaVu Sans', Arial, sans-serif;
       font-size: 10pt; line-height: 1.5; color: #1d232b; }
h1 { font-size: 21pt; color: #1f4f9c; margin: 0 0 10px; padding-bottom: 6px;
     border-bottom: 2px solid #2a6fd6; page-break-before: always; }
h2 { font-size: 14pt; color: #2a6fd6; margin: 22px 0 6px; page-break-after: avoid; }
h3 { font-size: 11.5pt; margin: 16px 0 4px; page-break-after: avoid; }
h4 { font-size: 10.5pt; margin: 12px 0 4px; page-break-after: avoid; }
p, li { orphans: 3; widows: 3; }
a { color: #2a6fd6; text-decoration: none; }
code { font-family: Consolas, 'DejaVu Sans Mono', monospace; font-size: 9pt;
       background: #eef1f5; padding: 1px 4px; border-radius: 3px; }
pre { background: #eef1f5; padding: 8px 10px; border-radius: 4px; page-break-inside: avoid;
      white-space: pre-wrap; }
pre code { background: none; padding: 0; }
table { border-collapse: collapse; margin: 8px 0; width: 100%; page-break-inside: auto; }
th, td { border: 0.5pt solid #c9d0d9; padding: 4px 7px; text-align: left;
         vertical-align: top; font-size: 9pt; }
th { background: #e8eef8; }
tr { page-break-inside: avoid; }
p:has(> strong:only-child) { page-break-after: avoid; margin-bottom: 4px; }
blockquote { border-left: 3px solid #2a6fd6; margin: 8px 0; padding: 2px 12px;
             color: #45505e; }
.cover { height: 250mm; display: flex; flex-direction: column; align-items: center;
         justify-content: center; text-align: center; }
.cover img { width: 150px; height: 150px; }
.cover .name { font-size: 28pt; font-weight: 700; color: #1f4f9c; margin-top: 24px; }
.cover .sub { font-size: 17pt; color: #45505e; margin-top: 6px; }
.cover .ver { font-size: 11pt; color: #6b7480; margin-top: 30px; }
.cover .copy { font-size: 8.5pt; color: #6b7480; margin-top: 70px; max-width: 120mm; }
.toc { page-break-before: always; }
.toc h1 { page-break-before: avoid; }
.toc ol { list-style: none; padding: 0; font-size: 11pt; }
.toc li { margin: 6px 0; }
.toc li ol { font-size: 9.5pt; margin: 2px 0 6px 18px; }
.toc li li { margin: 2px 0; }
"""

_ID_LINE = re.compile(r"^<!--\s*id:\s*([\w.]+)\s*-->\s*$")


def _anchor(key: str) -> str:
    return "s-" + re.sub(r"[^\w-]", "-", key)


def chapter_html(text: str) -> str:
    """Markdown -> HTML, with an anchor before each section that has an id."""
    import markdown

    lines, in_code = [], False
    for line in text.splitlines():
        if line.startswith("```"):
            in_code = not in_code
        m = None if in_code else _ID_LINE.match(line)
        if m:
            lines += [f'<a id="{_anchor(m.group(1))}"></a>', ""]
        else:
            lines.append(line)
    body = markdown.markdown("\n".join(lines), extensions=["tables", "fenced_code", "sane_lists"])
    # help:topic links jump inside the PDF; locate() finds the nearest section with an id.
    return re.sub(r'href="help:([\w.]+)"', lambda m: f'href="#{_anchor(_target(m.group(1)))}"',
                  body)


_LANG = "en"


def _target(topic: str) -> str:
    found = manual.locate(topic, _LANG)
    return found[1].id if found else "intro"


def document(lang: str) -> str:
    global _LANG
    _LANG = lang
    t = TEXT[lang]
    icon = base64.b64encode((ROOT / "build/icons/png/advastro-256.png").read_bytes()).decode()
    chapters = manual.chapters(lang)
    toc = []
    for ch in chapters:
        subs = "".join(f'<li><a href="#{_anchor(s.id)}">{html.escape(s.title)}</a></li>'
                       for s in ch.sections[1:] if s.level == 2 and not s.id.startswith("_"))
        toc.append(f'<li><a href="#{_anchor(ch.key)}"><b>{html.escape(ch.title)}</b></a>'
                   + (f"<ol>{subs}</ol>" if subs else "") + "</li>")
    files = sorted((ROOT / "src/advastro/help" / lang).glob("*.md"))
    body = "\n".join(chapter_html(f.read_text(encoding="utf-8")) for f in files)
    return f"""<!doctype html><html lang="{lang}"><head><meta charset="utf-8">
<title>{APP_NAME} – {t['title']}</title><style>{CSS}</style></head><body>
<div class="cover"><img src="data:image/png;base64,{icon}" alt="">
<div class="name">{APP_NAME}</div><div class="sub">{t['title']}</div>
<div class="ver">{t['version']} {__version__}</div>
<div class="copy">{html.escape(t['copy'])}<br>
miklosoft.se/main · github.com/Coffymonk/AdvAstro</div>
</div>
<div class="toc"><h1>{t['contents']}</h1><ol>{''.join(toc)}</ol></div>
{body}
</body></html>"""


def make_pdf(lang: str, out_dir: Path) -> Path:
    from playwright.sync_api import sync_playwright

    out_dir.mkdir(parents=True, exist_ok=True)
    pdf = out_dir / TEXT[lang]["file"].format(v=__version__)
    footer = (f'<div style="font-size:7.5pt;color:#6b7480;width:100%;padding:0 18mm;'
              f'display:flex;justify-content:space-between;font-family:sans-serif">'
              f'<span>{APP_NAME} {__version__} · {TEXT[lang]["title"]}</span>'
              f'<span><span class="pageNumber"></span> / <span class="totalPages"></span></span>'
              f"</div>")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(document(lang), wait_until="load")
        page.pdf(path=str(pdf), format="A4", print_background=True, prefer_css_page_size=True,
                 display_header_footer=True, header_template="<span></span>",
                 footer_template=footer, outline=True, tagged=True)
        browser.close()
    return pdf


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--lang", choices=sorted(TEXT), action="append")
    ap.add_argument("--out", type=Path, default=DIST)
    args = ap.parse_args()
    for lang in args.lang or sorted(TEXT):
        pdf = make_pdf(lang, args.out)
        print(f"  {pdf.name}  ({pdf.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
