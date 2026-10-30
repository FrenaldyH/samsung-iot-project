"""Convert laporan.tex into laporan.docx with pandoc, keeping the report layout of notes/format.txt.

Usage (run from latex/):  python3 to_docx.py
Needs pandoc on PATH, or PANDOC=/path/to/pandoc.

Steps:
  1. rewrite LaTeX that pandoc cannot read (custom column types, \\path, cover table, TOC commands)
  2. pandoc LaTeX -> JSON AST; number chapters/sections/figures/tables and resolve \\ref ourselves
  3. pandoc JSON -> docx; then patch styles, page setup, footer and TOC fields in the docx XML
"""
import json
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from xml.sax.saxutils import escape

PANDOC = os.environ.get("PANDOC", "pandoc")
SRC, OUT = "laporan.tex", "laporan.docx"
TEXTWIDTH_CM = 21 - 4 - 3  # A4 width minus left and right margins
ROMAN = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]


# --------------------------------------------------------------------------
# 1. LaTeX pre-processing
# --------------------------------------------------------------------------
def preprocess(tex):
    """Rewrite the few LaTeX constructs pandoc misreads into ones it understands."""

    # tabularx with P{w}/L columns -> tabular with p{fraction\linewidth}, so pandoc keeps the widths
    def colspec(m):
        cols = re.findall(r"P\{([\d.]+)cm\}|(L)", m.group(1))
        fixed = sum(float(w) for w, _ in cols if w)
        free = (TEXTWIDTH_CM - fixed) / max(1, sum(1 for _, l in cols if l))
        spec = " ".join(f"p{{{(float(w) if w else free) / TEXTWIDTH_CM:.3f}\\linewidth}}" for w, _ in cols)
        return "\\begin{tabular}{" + spec + "}"

    tex = re.sub(r"\\begin\{tabularx\}\{\\textwidth\}\{((?:[^{}]|\{[^{}]*\})*)\}", colspec, tex)
    tex = tex.replace("\\end{tabularx}", "\\end{tabular}")
    tex = re.sub(r"\\path\|([^|]*)\|", lambda m: "\\texttt{" + m.group(1).replace("#", "\\#") + "}", tex)
    tex = tex.replace("\\allowbreak", "")

    # Cover: member table -> centred lines; \vfill -> marker that adds space before the next line
    def cover(m):
        body = re.sub(r"\\begin\{tabular\}\{[^}]*\}(.*?)\\end\{tabular\}",
                      lambda t: t.group(1).replace("&", " ").strip().rstrip("\\").strip(), m.group(0), flags=re.S)
        return body.replace("\\vfill", "\n\nDOCXGAP\n\n")

    tex = re.sub(r"\\begin\{titlepage\}.*?\\end\{titlepage\}", cover, tex, flags=re.S)

    # TOC / list of figures / list of tables -> heading + marker replaced by a Word field later
    tex = re.sub(r"\\cleardoublepage\\addcontentsline\{toc\}\{chapter\}\{([^}]*)\}\s*\\(tableofcontents|listoffigures|listoftables)",
                 r"\\chapter*{\1}\n\nDOCXFIELD\2\n", tex)
    # Roman -> arabic page numbers start here: becomes a Word section break
    tex = tex.replace("\\pagenumbering{arabic}", "\n\nDOCXSECTIONBREAK\n\n")
    return tex


# --------------------------------------------------------------------------
# 2. AST helpers and numbering
# --------------------------------------------------------------------------
def Str(s):
    return {"t": "Str", "c": s}


SPACE = {"t": "Space"}


def nodes(x):
    """Yield every AST element (dict with 't') in document order."""
    if isinstance(x, dict):
        if "t" in x:
            yield x
        for v in x.values():
            yield from nodes(v)
    elif isinstance(x, list):
        for v in x:
            yield from nodes(v)


def is_marker(block, text):
    """True if the block is a paragraph holding only the given marker word."""
    return block.get("t") in ("Para", "Plain") and block["c"] == [Str(text)]


def styled(style, blocks):
    """Wrap blocks in a Div that pandoc maps to a Word paragraph style."""
    return {"t": "Div", "c": [["", [], [["custom-style", style]]], blocks]}


def plain(inl):
    """Inline elements -> plain text."""
    return "".join(n["c"] if n["t"] == "Str" else n["c"][1] if n["t"] == "Code" else
                   " " if n["t"] in ("Space", "SoftBreak") else "" for n in nodes(inl))


def field(instr, hint, entries=None):
    """A Word TOC-style field. With entries [(level, text, page)] its result is pre-filled, so the list
    also shows where fields are not refreshed (Google Docs, LibreOffice, or 'No' on Word's prompt)."""
    begin = ('<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
             f'<w:r><w:instrText xml:space="preserve"> {instr} </w:instrText></w:r>'
             '<w:r><w:fldChar w:fldCharType="separate"/></w:r>')
    end = '<w:r><w:fldChar w:fldCharType="end"/></w:r>'
    if not entries:
        xml = f'<w:p>{begin}<w:r><w:t>Klik kanan lalu Update Field untuk menampilkan {hint}.</w:t></w:r>{end}</w:p>'
    else:
        xml = "".join(
            f'<w:p><w:pPr><w:pStyle w:val="TOC{lvl}"/></w:pPr>{begin if i == 0 else ""}'
            f'<w:r><w:t xml:space="preserve">{escape(text)}</w:t></w:r><w:r><w:tab/></w:r><w:r><w:t>{page}</w:t></w:r>'
            f'{end if i == len(entries) - 1 else ""}</w:p>'
            for i, (lvl, text, page) in enumerate(entries))
    return {"t": "RawBlock", "c": ["openxml", xml]}


# marker -> (entry list, field instruction, hint); LOF/LOT collect paragraphs by caption style
FIELD_SPECS = {
    "DOCXFIELDtableofcontents": ("toc", 'TOC \\o "1-2" \\h \\z \\u', "daftar isi"),
    "DOCXFIELDlistoffigures": ("lof", 'TOC \\h \\z \\t "Image Caption,1"', "daftar gambar"),
    "DOCXFIELDlistoftables": ("lot", 'TOC \\h \\z \\t "Table Caption,1"', "daftar tabel"),
}


def make_fields(pages):
    """Field blocks per marker, pre-filled when page numbers are known."""
    pages = pages or {}
    return {m: field(instr, hint, pages.get(kind)) for m, (kind, instr, hint) in FIELD_SPECS.items()}
SECTION_BREAK = {"t": "RawBlock", "c": ["openxml", "<w:p><w:r><w:t>DOCXSECTIONBREAK</w:t></w:r></w:p>"]}


def number(doc, table_labels):
    """Add BAB/section/figure/table numbers like LaTeX does.

    Returns label -> number, and the entries of the TOC / list of figures / list of tables.
    pandoc drops \\label inside table environments, so table labels come from the source, in order."""
    labels, ch, sec, fig, tab = {}, 0, 0, 0, 0
    lists = {"toc": [], "lof": [], "lot": []}
    table_labels = iter(table_labels)
    for n in nodes(doc["blocks"]):
        if n["t"] == "Header":
            level, (_, classes, _), inl = n["c"]
            if level == 1:  # chapter titles are uppercase, like the PDF
                for s in nodes(inl):
                    if s["t"] == "Str":
                        s["c"] = s["c"].upper()
            if "unnumbered" in classes:
                if level == 1:
                    lists["toc"].append((1, plain(inl)))
                continue
            if level == 1:
                ch, sec, fig, tab = ch + 1, 0, 0, 0
                n["c"][2] = [Str("BAB"), SPACE, Str(ROMAN[ch]), SPACE] + inl
            elif level == 2:
                sec += 1
                n["c"][2] = [Str(f"{ch}.{sec}"), SPACE] + inl
            if level <= 2:
                lists["toc"].append((level, plain(n["c"][2])))
        elif n["t"] in ("Figure", "Table"):
            if n["t"] == "Figure":
                fig += 1
                kind, num = "Gambar", f"{ch}.{fig}"
            else:
                tab += 1
                kind, num = "Tabel", f"{ch}.{tab}"
            labels[n["c"][0][0] if n["t"] == "Figure" else next(table_labels)] = num
            caption = n["c"][1][1]
            if caption:  # bold "Gambar 2.1" prefix, as with caption labelfont=bf
                caption[0]["c"] = [{"t": "Strong", "c": [Str(kind), SPACE, Str(num)]}, SPACE] + caption[0]["c"]
                lists["lof" if kind == "Gambar" else "lot"].append((1, plain(caption[0]["c"])))
    return labels, lists


def resolve_refs(x, labels):
    """Replace \\ref links (rendered as [label]) with the computed number."""
    if isinstance(x, list):
        for i, v in enumerate(x):
            if isinstance(v, dict) and v.get("t") == "Link" and ("reference-type", "ref") in map(tuple, v["c"][0][2]):
                ref = dict(map(tuple, v["c"][0][2]))["reference"]
                x[i] = Str(labels.get(ref, "??"))
            else:
                resolve_refs(v, labels)
    elif isinstance(x, dict):
        for v in x.values():
            resolve_refs(v, labels)


def restyle(blocks, fields):
    """Map cover, right-aligned block, markers and unnumbered subheadings to Word styles."""
    out = []
    for b in blocks:
        t = b.get("t")
        attr = b["c"][1] if t == "Header" else b["c"][0] if t in ("Div", "CodeBlock") else None
        classes = attr[1] if attr else []
        if t == "Div" and "titlepage" in classes:
            inner, gap = [], False
            for i, p in enumerate(b["c"][1]):
                if is_marker(p, "DOCXGAP"):
                    gap = True
                    continue
                has_img = any(n["t"] == "Image" for n in nodes(p))
                style = ("CoverTitle" if i == 0 else "CoverSubtitle" if i == 1 else
                         "CoverLogo" if has_img else "CoverGap" if gap else "Cover")
                inner.append(styled(style, [p]))
                gap = False
            out.extend(inner)
        elif t == "Div" and "flushright" in classes:
            out.append(styled("RightAligned", b["c"][1]))
        elif t == "Div":
            b["c"][1] = restyle(b["c"][1], fields)
            out.append(b)
        elif t == "Header" and b["c"][0] == 2 and "unnumbered" in classes:
            # Lampiran subheadings: look like Heading 2 but stay out of the TOC, as in the PDF
            out.append(styled("SubheadingNoToc", [{"t": "Para", "c": b["c"][2]}]))
        elif t == "CodeBlock":
            b["c"][0][1] = ["cpp"]  # listings' "iso c++" is unknown to the highlighter
            out.append(b)
        elif t in ("Para", "Plain") and len(b["c"]) == 1 and b["c"][0].get("c") in fields:
            out.append(fields[b["c"][0]["c"]])
        elif is_marker(b, "DOCXSECTIONBREAK"):
            out.append(SECTION_BREAK)
        else:
            out.append(b)
    return out


# --------------------------------------------------------------------------
# 3. docx post-processing: styles, page setup, footer, field update
# --------------------------------------------------------------------------
W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
FONT = '<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman" w:eastAsia="Times New Roman"/>'
MONO = '<w:rFonts w:ascii="Courier New" w:hAnsi="Courier New" w:cs="Courier New"/>'
SINGLE = '<w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/>'
NO_IND = '<w:ind w:left="0" w:firstLine="0"/>'


def style(sid, name, ppr="", rpr="", based="Normal", kind="paragraph", custom=True, extra=""):
    """One w:style element."""
    return (f'<w:style w:type="{kind}"{" w:customStyle=\"1\"" if custom else ""} w:styleId="{sid}">'
            f'<w:name w:val="{name}"/>{f"<w:basedOn w:val=\"{based}\"/>" if based else ""}<w:qFormat/>'
            f'{f"<w:pPr>{ppr}</w:pPr>" if ppr else ""}{f"<w:rPr>{rpr}</w:rPr>" if rpr else ""}{extra}</w:style>')


CENTER_SINGLE = SINGLE + NO_IND + '<w:jc w:val="center"/>'
STYLES = [
    # format.txt: Times New Roman 12, 1.5 spacing, justified, first-line indent ~1 cm
    style("Normal", "Normal", SINGLE, FONT + '<w:color w:val="000000"/><w:sz w:val="24"/><w:szCs w:val="24"/>',
          based="", custom=False),
    style("BodyText", "Body Text", '<w:spacing w:before="0" w:after="0" w:line="360" w:lineRule="auto"/>'
          '<w:ind w:firstLine="567"/><w:jc w:val="both"/>'),
    style("FirstParagraph", "First Paragraph", based="BodyText"),
    style("Compact", "Compact", '<w:ind w:firstLine="0"/>', based="BodyText"),
    # Chapter titles: 14 pt bold, centred, each chapter on a new page
    style("Heading1", "heading 1", '<w:keepNext/><w:pageBreakBefore/><w:spacing w:before="0" w:after="480" w:line="360" w:lineRule="auto"/>'
          + NO_IND + '<w:jc w:val="center"/><w:outlineLvl w:val="0"/>',
          '<w:b/><w:bCs/><w:sz w:val="28"/><w:szCs w:val="28"/>', custom=False),
    style("Heading2", "heading 2", '<w:keepNext/><w:spacing w:before="240" w:after="120" w:line="360" w:lineRule="auto"/>'
          + NO_IND + '<w:outlineLvl w:val="1"/>', '<w:b/><w:bCs/>', custom=False),
    style("SubheadingNoToc", "Subheading No TOC", '<w:keepNext/><w:spacing w:before="240" w:after="120" w:line="360" w:lineRule="auto"/>'
          + NO_IND, '<w:b/><w:bCs/>'),
    # Captions: centred, single spaced; table caption above the table, figure caption below
    style("Caption", "caption", CENTER_SINGLE, custom=False),
    style("TableCaption", "Table Caption", '<w:keepNext/><w:spacing w:before="240" w:after="120" w:line="240" w:lineRule="auto"/>'
          + NO_IND + '<w:jc w:val="center"/>', based="Caption"),
    style("ImageCaption", "Image Caption", '<w:spacing w:before="120" w:after="240" w:line="240" w:lineRule="auto"/>'
          + NO_IND + '<w:jc w:val="center"/>', based="Caption"),
    style("Figure", "Figure", '<w:keepNext/>' + CENTER_SINGLE),
    style("CaptionedFigure", "Captioned Figure", '<w:keepNext/>' + CENTER_SINGLE, based="Figure"),
    # Table cells: single spaced, 11 pt, left aligned
    style("TableText", "Table Text", '<w:spacing w:before="20" w:after="20" w:line="240" w:lineRule="auto"/>' + NO_IND,
          '<w:sz w:val="22"/><w:szCs w:val="22"/>'),
    style("TableTextSmall", "Table Text Small", rpr='<w:sz w:val="18"/><w:szCs w:val="18"/>', based="TableText"),
    # TOC / list entries: title, dot leader, page number at the right margin (text width 14 cm)
    style("TOC1", "toc 1", '<w:tabs><w:tab w:val="right" w:leader="dot" w:pos="7937"/></w:tabs>'
          '<w:spacing w:before="60" w:after="60"/>' + NO_IND, custom=False),
    style("TOC2", "toc 2", '<w:tabs><w:tab w:val="right" w:leader="dot" w:pos="7937"/></w:tabs>'
          '<w:spacing w:before="0" w:after="60"/><w:ind w:left="440"/>', custom=False),
    # Booktabs look: rule above and below the table, and under the header row
    style("Table", "Table", based="TableNormal", kind="table", custom=False, extra=(
        '<w:tblPr><w:tblBorders><w:top w:val="single" w:sz="8" w:space="0" w:color="000000"/>'
        '<w:bottom w:val="single" w:sz="8" w:space="0" w:color="000000"/></w:tblBorders>'
        '<w:tblCellMar><w:left w:w="57" w:type="dxa"/><w:right w:w="57" w:type="dxa"/></w:tblCellMar></w:tblPr>'
        '<w:tblStylePr w:type="firstRow"><w:rPr><w:b/></w:rPr><w:tcPr><w:tcBorders>'
        '<w:bottom w:val="single" w:sz="4" w:space="0" w:color="000000"/></w:tcBorders></w:tcPr></w:tblStylePr>')),
    # Appendix source code: small monospace in a light frame (pBdr must come before spacing)
    style("SourceCode", "Source Code",
          '<w:pBdr><w:top w:val="single" w:sz="4" w:space="2" w:color="999999"/><w:left w:val="single" w:sz="4" w:space="4" w:color="999999"/>'
          '<w:bottom w:val="single" w:sz="4" w:space="2" w:color="999999"/><w:right w:val="single" w:sz="4" w:space="4" w:color="999999"/></w:pBdr>'
          + SINGLE + NO_IND, MONO + '<w:sz w:val="17"/><w:szCs w:val="17"/>'),
    style("VerbatimChar", "Verbatim Char", rpr=MONO, based="", kind="character"),
    # Cover page
    style("Cover", "Cover", CENTER_SINGLE.replace('w:after="0"', 'w:after="60"')),
    style("CoverTitle", "Cover Title", '<w:spacing w:before="0" w:after="480"/>', '<w:b/><w:sz w:val="32"/><w:szCs w:val="32"/>', based="Cover"),
    style("CoverSubtitle", "Cover Subtitle", '<w:spacing w:before="0" w:after="480"/>', '<w:b/><w:sz w:val="28"/><w:szCs w:val="28"/>', based="Cover"),
    style("CoverLogo", "Cover Logo", '<w:spacing w:before="600" w:after="0"/>', based="Cover"),
    style("CoverGap", "Cover Gap", '<w:spacing w:before="1800" w:after="60"/>', based="Cover"),
    style("RightAligned", "Right Aligned", '<w:spacing w:before="480" w:after="0" w:line="360" w:lineRule="auto"/>'
          + NO_IND + '<w:jc w:val="right"/>'),
]
DOC_DEFAULTS = (f'<w:docDefaults><w:rPrDefault><w:rPr>{FONT}<w:sz w:val="24"/><w:szCs w:val="24"/>'
                '<w:lang w:val="id-ID"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr>' + SINGLE + '</w:pPr></w:pPrDefault></w:docDefaults>')

FOOTER = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:ftr {W}><w:p><w:pPr><w:jc w:val="center"/></w:pPr>'
          '<w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText xml:space="preserve"> PAGE </w:instrText></w:r>'
          '<w:r><w:fldChar w:fldCharType="separate"/></w:r><w:r><w:t>1</w:t></w:r><w:r><w:fldChar w:fldCharType="end"/></w:r></w:p></w:ftr>')


def sect_pr(fmt, title_page):
    """Section properties: A4, margins 4/4/3/3 cm (top/left/bottom/right), centred page number footer."""
    return ('<w:sectPr><w:footerReference w:type="default" r:id="rIdFooter1"/>'
            '<w:pgSz w:w="11906" w:h="16838"/>'
            '<w:pgMar w:top="2268" w:right="1701" w:bottom="1701" w:left="2268" w:header="708" w:footer="708" w:gutter="0"/>'
            f'<w:pgNumType w:fmt="{fmt}" w:start="1"/>{"<w:titlePg/>" if title_page else ""}</w:sectPr>')


def patch_docx(path, small_tables):
    """Apply styles, page setup, footer and 'update fields on open' to the pandoc output.

    small_tables: one flag per table, in order; True where the LaTeX table used \\footnotesize."""
    with zipfile.ZipFile(path) as z:
        files = {n: z.read(n) for n in z.namelist()}

    # Styles: drop pandoc's version of each style we define, then append ours
    s = files["word/styles.xml"].decode()
    s = re.sub(r"<w:docDefaults>.*?</w:docDefaults>", DOC_DEFAULTS, s, flags=re.S)
    for st in STYLES:
        sid = re.search(r'w:styleId="([^"]+)"', st).group(1)
        s = re.sub(rf'<w:style [^>]*w:styleId="{sid}"[^>]*>.*?</w:style>', "", s, flags=re.S)
    files["word/styles.xml"] = s.replace("</w:styles>", "".join(STYLES) + "</w:styles>").encode()

    d = files["word/document.xml"].decode()
    # Table cells get the compact table style instead of the list "Compact" style
    small = iter(small_tables)
    d = re.sub(r"<w:tbl>.*?</w:tbl>", lambda m: m.group(0).replace(
        'w:val="Compact"', 'w:val="TableTextSmall"' if next(small, False) else 'w:val="TableText"'), d, flags=re.S)
    # Front matter (cover .. lists): roman numbers, no number on the cover; body: arabic from 1
    d = re.sub(r"<w:sectPr>.*?</w:sectPr>(?=\s*</w:body>)", sect_pr("decimal", False), d, flags=re.S)
    d = d.replace("<w:p><w:r><w:t>DOCXSECTIONBREAK</w:t></w:r></w:p>",
                  f"<w:p><w:pPr>{sect_pr('lowerRoman', True)}</w:pPr></w:p>")
    if 'xmlns:r=' not in d[:2000]:
        d = d.replace("<w:document ", '<w:document xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" ', 1)
    files["word/document.xml"] = d.encode()

    files["word/footer1.xml"] = FOOTER.encode()
    rels = files["word/_rels/document.xml.rels"].decode()
    files["word/_rels/document.xml.rels"] = rels.replace("</Relationships>",
        '<Relationship Id="rIdFooter1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" '
        'Target="footer1.xml"/></Relationships>').encode()
    ct = files["[Content_Types].xml"].decode()
    files["[Content_Types].xml"] = ct.replace("</Types>",
        '<Override PartName="/word/footer1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/></Types>').encode()

    # Ask Word to refresh TOC fields and page numbers when the file is opened
    st = files["word/settings.xml"].decode()
    files["word/settings.xml"] = re.sub(r"(<w:settings[^>]*>)", r'\1<w:updateFields w:val="true"/>', st, count=1).encode()

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data)


def find_pages(lists):
    """Render OUT with LibreOffice and look up the printed page number of every list entry."""
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", tmp, OUT],
                       capture_output=True, check=True)
        pdf = os.path.join(tmp, os.path.splitext(OUT)[0] + ".pdf")
        text = subprocess.run(["pdftotext", pdf, "-"], capture_output=True, text=True, check=True).stdout
    pages = [" ".join(p.split()) for p in text.split("\f")]

    def lookup(entries):
        # entries appear in document order, so search forward from the previous hit
        out, start = [], 0
        for lvl, title in entries:
            key = " ".join(title.split())[:60]
            hit = next((i for i in range(start, len(pages)) if key in pages[i]), None)
            if hit is None:
                print(f"warning: page not found for {title!r}")
            start = hit if hit is not None else start
            out.append((lvl, title, start))
        return out

    found = {kind: lookup(entries) for kind, entries in lists.items()}
    body = next(p for _, title, p in found["toc"] if title.startswith("BAB I "))
    # front matter counts in roman from the cover (i); the body restarts at 1 on BAB I
    label = lambda p: str(p - body + 1) if p >= body else ROMAN[p + 1].lower()
    return {kind: [(lvl, title, label(p)) for lvl, title, p in v] for kind, v in found.items()}


def build(tex, pages=None):
    """One conversion pass: tex -> AST -> numbered/styled AST -> docx -> patched docx."""
    ast = json.loads(subprocess.run([PANDOC, "-f", "latex", "-t", "json"], input=tex, text=True,
                                    capture_output=True, check=True).stdout)
    labels, lists = number(ast, re.findall(r"\\label\{(tab:[^}]*)\}", tex))
    resolve_refs(ast["blocks"], labels)
    ast["blocks"] = restyle(ast["blocks"], make_fields(pages))
    subprocess.run([PANDOC, "-f", "json", "-o", OUT, "--resource-path=.:../image"],
                   input=json.dumps(ast), text=True, check=True)
    small = ["\\footnotesize" in t for t in re.findall(r"\\begin\{table\}.*?\\end\{table\}", tex, flags=re.S)]
    patch_docx(OUT, small)
    return labels, lists


def main():
    """Build once, then rebuild with the TOC / lists pre-filled using page numbers from a render."""
    with open(SRC, encoding="utf-8") as f:
        tex = preprocess(f.read())
    labels, lists = build(tex)
    if shutil.which("soffice") and shutil.which("pdftotext"):
        build(tex, find_pages(lists))
    else:
        print("soffice/pdftotext not found: TOC and lists fill in only when Word updates fields")
    print(f"wrote {OUT}; labels: {labels}")


if __name__ == "__main__":
    main()
