"""Generate the big-picture architecture diagrams as draw.io files (then export PNGs next to them).

    python docs/architecture/gen_drawio.py
    for f in docs/architecture/*.drawio; do drawio -x -f png -s 2 -b 20 -o "${f%.drawio}.png" "$f"; done

Style: white background, a centred bold title, dashed rounded group boxes with a light fill and a
coloured uppercase title, AWS-set icons with short captions, labelled right-angle arrows, nothing
overlapping, 8-16 nodes. Edit the .drawio in draw.io, or change this script and regenerate.
"""
from pathlib import Path

OUT = Path(__file__).resolve().parent
FONT = "fontFamily=Helvetica;"
GROUP = {
    "blue": "fillColor=#EAF2FB;strokeColor=#5B8FD1;fontSize=13;fontColor=#1F6FB5;",
    "lav": "fillColor=#F3ECFA;strokeColor=#9B6BC8;fontSize=13;fontColor=#7B3FB5;",
    "org": "fillColor=#FFF1E0;strokeColor=#E08A2E;fontSize=13;fontColor=#C25E00;",
    "grey": "fillColor=#F6F7F9;strokeColor=#9AA5B1;fontSize=12;fontColor=#4A5561;",
    "green": "fillColor=#EEF7EE;strokeColor=#5BA35B;fontSize=13;fontColor=#2E7D32;",
}
cells = []


def esc(s): return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def v(id, val, style, x, y, w, h):
    cells.append(f'<mxCell id="{id}" value="{esc(val)}" style="{style}" vertex="1" parent="1">'
                 f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')


def group(id, val, col, x, y, w, h):
    v(id, val, "rounded=1;arcSize=24;absoluteArcSize=1;dashed=1;dashPattern=4 4;strokeWidth=1.2;html=1;whiteSpace=wrap;"
      "verticalAlign=top;align=center;spacingTop=4;fontStyle=1;" + FONT + GROUP[col], x, y, w, h)


def text(id, val, x, y, w, h, size=11, bold=0, color="#232F3E", align="center", valign="middle"):
    v(id, val, f"text;html=1;align={align};verticalAlign={valign};whiteSpace=wrap;strokeColor=none;fillColor=none;"
      f"{FONT}fontSize={size};fontStyle={bold};fontColor={color};", x, y, w, h)


LABEL = {"bottom": "verticalLabelPosition=bottom;verticalAlign=top;align=center;",
         "right": "labelPosition=right;verticalLabelPosition=middle;verticalAlign=middle;align=left;spacingLeft=6;"}


def res(id, val, icon, fill, x, y, s=56, lab="bottom"):
    """An AWS-set resource icon (coloured square)."""
    v(id, val, f"sketch=0;outlineConnect=0;fontColor=#232F3E;fillColor={fill};strokeColor=#ffffff;dashed=0;{LABEL[lab]}"
      f"html=1;fontSize=11;fontStyle=0;aspect=fixed;shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.{icon};{FONT}", x, y, s, s)


def glyph(id, val, shape, fill, x, y, w, h, lab="bottom"):
    """An AWS-set general glyph (user, document, database...)."""
    v(id, val, f"sketch=0;outlineConnect=0;fontColor=#232F3E;gradientColor=none;fillColor={fill};strokeColor=none;dashed=0;"
      f"{LABEL[lab]}html=1;fontSize=11;fontStyle=0;aspect=fixed;pointerEvents=1;shape=mxgraph.aws4.{shape};{FONT}", x, y, w, h)


BOX = {"green": "fillColor=#D5F5D5;strokeColor=#2E7D32;fontColor=#1B3A1B;",
       "orange": "fillColor=#FFE0B2;strokeColor=#E07B00;fontColor=#4A2A00;",
       "white": "fillColor=#FFFFFF;strokeColor=#5B8FD1;fontColor=#232F3E;",
       "lavw": "fillColor=#FFFFFF;strokeColor=#9B6BC8;fontColor=#232F3E;",
       "dash": "fillColor=#F6F7F9;strokeColor=#9AA5B1;fontColor=#4A5561;dashed=1;dashPattern=4 4;"}


def box(id, val, kind, x, y, w, h, size=11, extra=""):
    v(id, val, f"rounded=1;arcSize=14;whiteSpace=wrap;html=1;{BOX[kind]}{FONT}fontSize={size};strokeWidth=1.2;" + extra, x, y, w, h)


def badge(id, n, x, y):
    v(id, str(n), f"ellipse;whiteSpace=wrap;html=1;aspect=fixed;fillColor=#232F3E;strokeColor=none;fontColor=#FFFFFF;"
      f"fontStyle=1;fontSize=13;{FONT}", x, y, 28, 28)


def e(id, src, tgt, label="", color="#8C8C8C", pts=(), exit=(1, 0.5), entry=(0, 0.5), dashed=False, both=False,
      bold=False, lblcolor="#232F3E", lblbg="#FFFFFF", w=1.2, lx=None):
    st = (f"edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;endArrow=classic;endFill=1;"
          f"strokeColor={color};strokeWidth={w};{FONT}fontSize=11;fontColor={lblcolor};labelBackgroundColor={lblbg};"
          f"exitX={exit[0]};exitY={exit[1]};exitDx=0;exitDy=0;entryX={entry[0]};entryY={entry[1]};entryDx=0;entryDy=0;")
    if dashed:
        st += "dashed=1;dashPattern=6 4;"
    if both:
        st += "startArrow=classic;startFill=1;"
    if bold:
        st += "fontStyle=1;"
    geo = '<mxGeometry relative="1" as="geometry"' + (f' x="{lx}"' if lx is not None else "") + ">"
    if pts:
        geo += '<Array as="points">' + "".join(f'<mxPoint x="{a}" y="{b}"/>' for a, b in pts) + "</Array>"
    cells.append(f'<mxCell id="{id}" value="{esc(label)}" style="{st}" edge="1" parent="1" source="{src}" '
                 f'target="{tgt}">{geo}</mxGeometry></mxCell>')


def title(val, pw):
    text("title", val, pw / 2 - 450, 12, 900, 30, size=20, bold=1)


def write(name, pw, ph):
    xml = (f'<mxfile host="drawio" agent="StatementLens gen_drawio.py"><diagram id="{name}" name="{name}">'
           f'<mxGraphModel dx="{pw}" dy="{ph}" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" '
           f'fold="1" page="1" pageScale="1" pageWidth="{pw}" pageHeight="{ph}" background="#FFFFFF" math="0" shadow="0">'
           '<root><mxCell id="0"/><mxCell id="1" parent="0"/>\n' + "\n".join(cells) + "\n</root></mxGraphModel></diagram></mxfile>\n")
    (OUT / f"{name}.drawio").write_text(xml)
    cells.clear()


# icon helpers: (kind, shape/icon, fill, w, h)
I = {
    "user": ("glyph", "user", "#232F3E", 48, 48), "client": ("glyph", "client", "#232F3E", 48, 41),
    "app": ("glyph", "generic_application", "#1F6FB5", 48, 48), "chat": ("glyph", "chat", "#232F3E", 48, 42),
    "mobile": ("glyph", "mobile_client", "#232F3E", 30, 48), "folder": ("glyph", "folder", "#E07B00", 48, 40),
    "db": ("glyph", "generic_database", "#C925D1", 40, 48), "email": ("glyph", "email", "#DD344C", 48, 36),
    "doc": ("glyph", "document", "#1F6FB5", 35, 48), "docs": ("glyph", "documents", "#E07B00", 39, 48),
    "code": ("glyph", "source_code", "#232F3E", 35, 48), "gear": ("glyph", "gear", "#232F3E", 48, 48),
    "web": ("glyph", "internet_alt1", "#232F3E", 48, 48), "site": ("glyph", "internet_alt2", "#E07B00", 48, 48),
    "vault": ("res", "secrets_manager", "#DD344C", 48, 48), "cert": ("res", "certificate_manager", "#DD344C", 48, 48),
    "key": ("res", "key_management_service", "#DD344C", 48, 48), "pkg": ("res", "codeartifact", "#C925D1", 40, 40),
}


def icon(id, val, k, cx, y, lab="bottom"):
    """Place icon kind `k` centred on cx with its top at y."""
    kind, shape, fill, w, h = I[k]
    if kind == "res":
        res(id, val, shape, fill, cx - w / 2, y, w, lab)
    else:
        glyph(id, val, shape, fill, cx - w / 2, y, w, h, lab)
    return h


def flow(name, ttl, steps, groups, notes=(), footer="", gap=232, x0=150, top=80):
    """A numbered left-to-right flow. steps: (caption, icon, label on the arrow to the next step)."""
    C = [x0 + i * gap for i in range(len(steps))]
    pw, ph = C[-1] + 150, top + 340
    for gid, label, col, a, b in groups:
        group(gid, label, col, C[a] - 105, top, C[b] - C[a] + 210, 270)
    title(ttl, pw)
    for i, (cap, k, _) in enumerate(steps):
        badge(f"b{i}", i + 1, C[i] - 14, top + 32)
        h = I[k][4]
        icon(f"s{i}", cap, k, C[i], top + 98 - h / 2)
    for i, (_, _, lbl) in enumerate(steps[:-1]):
        e(f"e{i}", f"s{i}", f"s{i + 1}", lbl, color="#6B7785", w=1.4)
    for j, (i, val, kind) in enumerate(notes):
        box(f"n{j}", val, kind, C[i] - 98, top + 206, 196, 44, size=10)
    if footer:
        text("foot", f"<i>{footer}</i>", pw / 2 - 600, top + 286, 1200, 24, size=11, color="#4A5561")
    write(name, pw, ph)


# ---------------- 1. what runs where ----------------
PW, PH = 1900, 780
group("gDev", "YOUR MAC · YOUR DATA STAYS HERE", "blue", 40, 80, 1180, 620)
group("gExt", "OUTSIDE SERVICES · THEY SEE ONLY WHAT IS SHOWN", "grey", 1290, 80, 570, 290)
group("gWeb", "PUBLIC WEB · NO PERSONAL DATA", "org", 1290, 420, 570, 280)
title("StatementLens: what runs where", PW)
icon("you", "<b>You</b><br>one browser", "user", 180, 120)
icon("page", "<b>Dashboard page</b> in your browser<br>self-contained, fetches nothing", "client", 560, 120, lab="right")
box("sl", "<b>StatementLens</b><br>local process on 127.0.0.1<br>bank + card statements, spending", "white", 420, 300, 280, 90,
    extra="align=left;spacingLeft=58;strokeWidth=1.6;")
icon("slI", "", "app", 452, 321)
box("nf", "<b>Netfolio</b><br>local scripts + a localhost page<br>what you own and owe", "lavw", 860, 300, 280, 90,
    extra="align=left;spacingLeft=58;strokeWidth=1.6;")
icon("nfI", "", "app", 892, 321)
icon("msg", "<b>macOS Messages</b><br>bank SMS from your iPhone", "chat", 180, 324)
icon("fold", "<b>A folder of PDFs</b><br>your own files", "folder", 180, 470)
icon("db", "<b>store.db</b><br>SQLite on your disk", "db", 476, 540)
box("ik", "<b>inboxkit</b> (shared library)<br>Gmail fetch, sender check,<br>PDF unlock", "orange", 640, 500, 260, 76,
    extra="align=left;spacingLeft=52;fillColor=#FFF8F0;")
icon("ikI", "", "pkg", 666, 518)
icon("kc", "<b>OS keychain</b><br>your Gmail token", "vault", 770, 618, lab="right")
icon("yahoo", "<b>Yahoo Finance</b><br>chart API", "web", 1676, 160)
icon("gmail", "<b>Gmail API</b><br>read-only OAuth", "email", 1400, 256)
icon("share", "<b>sharecase</b><br>build and share baskets", "site", 1400, 490)
icon("price", "<b>/api/price</b><br>stateless quote proxy", "gear", 1676, 490)
box("demo", "StatementLens demo: a static page on synthetic data (proposed)", "dash", 1330, 616, 490, 46)
text("own", "<i>Nothing personal leaves your Mac: Gmail is read with your own token, and Yahoo sees only stock tickers. "
     "The public web holds no personal data.</i>", 350, 722, 1200, 24, size=11, color="#4A5561")
e("eYou", "you", "page", "opens 127.0.0.1<br>per-launch token", color="#6B7785")
e("ePage", "page", "sl", "page out,<br>corrections in", color="#1F6FB5", exit=(0.5, 1), entry=(0.5, 0), both=True)
e("eMsg", "msg", "sl", "bank SMS, read-only", color="#6B7785", entry=(0, 0.45))
e("eFold", "fold", "sl", "PDFs you drop in", color="#6B7785", entry=(0, 0.8), pts=((380, 494), (380, 372)))
e("eDb", "sl", "db", "rows, tags,<br>notes, splits", color="#C925D1", exit=(0.2, 1), entry=(0.5, 0))
e("eIk", "sl", "ik", "uses", color="#E07B00", exit=(0.85, 1), entry=(0.07, 0))
e("eNfIk", "nf", "ik", "uses", color="#E07B00", exit=(0.3, 1), entry=(1, 0.25), pts=((944, 519),))
e("eKc", "ik", "kc", "token", color="#DD344C", exit=(0.5, 1), entry=(0.5, 0))
e("eGm", "ik", "gmail", "HTTPS, read-only, your token", color="#DD344C", exit=(1, 0.75), entry=(0, 0.5),
  pts=((1250, 557), (1250, 274)), lx=-0.55)
e("eBal", "sl", "nf", "balances --json<br>(planned)", color="#7E57C2", dashed=True)
e("eNfY", "nf", "yahoo", "tickers only, server-side", color="#6B7785", exit=(0.8, 0), entry=(0, 0.5), pts=((1084, 184),))
e("eShare", "share", "price", "quotes", color="#6B7785")
e("ePx", "price", "yahoo", "tickers only", color="#6B7785", exit=(1, 0.5), entry=(1, 0.5), pts=((1830, 514), (1830, 184)))
write("01-what-runs-where", PW, PH)

# ---------------- 2. inside StatementLens ----------------
PW, PH = 1900, 700
group("gS", "SOURCES", "grey", 40, 80, 250, 540)
group("gR", "READ: INBOXKIT + PARSERS", "org", 340, 80, 460, 540)
group("gW", "WRITE: USE-CASES", "lav", 850, 80, 280, 540)
group("gD", "STORE", "blue", 1180, 80, 200, 540)
group("gV", "READ AND SERVE", "green", 1430, 80, 270, 540)
title("Inside StatementLens", PW)
icon("gm", "<b>Gmail</b><br>statement PDFs", "email", 165, 140)
icon("fo", "<b>A folder</b><br>of PDFs", "folder", 165, 250)
icon("im", "<b>Any IMAP</b><br>mailbox", "email", 165, 360)
icon("sm", "<b>Bank SMS</b><br>macOS Messages", "chat", 165, 483)
box("ik", "<b>inboxkit</b><br>sender check (Gmail),<br>PDF unlock, text", "orange", 365, 168, 190, 84, extra="fillColor=#FFF8F0;")
box("reg", "<b>ParserRegistry</b><br>bank + card statements", "white", 590, 148, 190, 50, extra="strokeColor=#E08A2E;")
box("pos", "<b>Positions</b> (inboxkit)<br>loan, FD, NPS", "white", 590, 222, 190, 50, extra="strokeColor=#E08A2E;")
box("al", "<b>parse_alert()</b><br>amount, date, last-4, ref", "white", 590, 480, 190, 50, extra="strokeColor=#E08A2E;")
box("ing", "<b>IngestStatements.run()</b><br>duplicates by file,<br>movement and row", "lavw", 870, 175, 240, 70)
box("ia", "<b>App.ingest_alerts()</b><br>route, one row per swipe,<br>reconcile", "lavw", 870, 470, 240, 70)
icon("db", "<b>store.db</b><br>rows, tags, notes,<br>positions", "db", 1280, 300)
box("ds", "<b>build_dataset()</b><br>the page's data", "green", 1450, 170, 230, 50)
box("rn", "<b>AppShellRenderer</b><br>one self-contained page", "green", 1450, 290, 230, 50)
box("sv", "<b>serve()</b> on 127.0.0.1<br>token, /api/* corrections", "green", 1450, 410, 230, 50)
icon("pg", "<b>Dashboard page</b><br>React + NeoPOP,<br>totals in core.js", "client", 1790, 414)
for i, s in enumerate(("gm", "fo", "im")):
    e(f"eS{i}", s, "ik", "", color="#6B7785", pts=((320, [158, 270, 378][i]), (320, 210)))
e("eSm", "sm", "al", "alerts", color="#6B7785", entry=(0, 0.5))
e("eReg", "ik", "reg", "text", color="#E07B00", exit=(1, 0.3), entry=(0, 0.5), pts=((572, 193), (572, 173)))
e("ePos", "ik", "pos", "", color="#E07B00", exit=(1, 0.75), entry=(0, 0.5), pts=((572, 231), (572, 247)))
e("eIng", "reg", "ing", "rows", color="#7E57C2", exit=(1, 0.5), entry=(0, 0.3))
e("eIngP", "pos", "ing", "snapshot", color="#7E57C2", exit=(1, 0.5), entry=(0, 0.75), pts=((830, 247), (830, 227)))
e("eAl", "al", "ia", "parsed", color="#7E57C2")
e("eDb1", "ing", "db", "rows, positions", color="#C925D1", exit=(1, 0.5), entry=(0, 0.3), pts=((1210, 210), (1210, 314)))
e("eDb2", "ia", "db", "live rows", color="#C925D1", exit=(1, 0.5), entry=(0, 0.75), pts=((1210, 505), (1210, 336)))
e("eDs", "db", "ds", "rows", color="#2E7D32", exit=(1, 0.2), entry=(0, 0.5), pts=((1405, 310), (1405, 195)))
e("eRn", "ds", "rn", "", color="#2E7D32", exit=(0.5, 1), entry=(0.5, 0))
e("eSv", "rn", "sv", "", color="#2E7D32", exit=(0.5, 1), entry=(0.5, 0))
e("ePg", "sv", "pg", "page out,<br>corrections in", color="#1F6FB5", exit=(1, 0.5), entry=(0, 0.5), both=True)
e("eFix", "sv", "db", "tags, notes, splits", color="#1F6FB5", exit=(0, 0.75), entry=(1, 0.83), pts=((1360, 448), (1360, 340)))
text("own", "<i>Statements and SMS enter on the left, the page leaves on the right. Corrections you make on the page go "
     "straight back to the store, never into the parsed rows.</i>", 350, 640, 1200, 24, size=11, color="#4A5561")
write("02-inside-statementlens", PW, PH)

# ---------------- 3. importing a statement ----------------
flow("03-importing-a-statement", "Importing a statement from Gmail", [
    ("<b>Statement email</b><br>from your bank,<br>read-only", "email", "PDF +<br>headers"),
    ("<b>Sender check</b><br>trusted bank domain +<br>Gmail's DKIM / DMARC", "cert", "proven<br>sender"),
    ("<b>Unlock the PDF</b><br>password derived in<br>memory from your hints", "key", "text"),
    ("<b>Loan, FD or NPS?</b><br>inboxkit.positions,<br>checks its own sums", "code", "not a<br>position"),
    ("<b>Parse the statement</b><br>bank or card parser,<br>amounts in paise", "code", "rows"),
    ("<b>Drop duplicates</b><br>same file, same<br>movement, same row", "docs", "new rows"),
    ("<b>Store the rows</b><br>store.db", "db", "months<br>covered"),
    ("<b>Reconcile live rows</b><br>pair SMS rows with<br>statement lines", "gear", ""),
], [("g1", "FROM GMAIL", "blue", 0, 1), ("g2", "READ", "lav", 2, 4), ("g3", "STORE", "org", 5, 7)],
    notes=[(1, "<b>not proven:</b> listed on the<br>page as not read, never opened", "orange"),
           (3, "<b>a position:</b> stored apart,<br>never counted as spending", "green"),
           (5, "<b>already stored:</b><br>counted as a duplicate", "orange")],
    footer="A PDF from a folder starts at step 3: your own files have no sender to check.")

# ---------------- 4. live rows from bank SMS ----------------
flow("04-live-rows-from-sms", "Live rows from bank SMS, settled by the statement", [
    ("<b>Bank SMS</b><br>forwarded from your<br>iPhone to your Mac", "mobile", "new<br>messages"),
    ("<b>Read chat.db</b><br>read-only, bank<br>senders only", "chat", "bank<br>alerts"),
    ("<b>parse_alert()</b><br>amount, date, direction,<br>last-4, reference", "code", "parsed"),
    ("<b>Route to an account</b><br>last-4, then a known<br>reference, then the bank", "gear", "routed"),
    ("<b>One row per payment</b><br>an SMS and an email of<br>the same swipe kept once", "docs", "stored"),
    ("<b>Live rows</b><br>tagged live,<br>counted in totals", "db", "statement<br>arrives"),
    ("<b>Pair with the statement</b><br>by reference, else date<br>±2 days + amount", "doc", "no match"),
    ("<b>Unsettled</b><br>listed, and taken out<br>of every total", "db", ""),
], [("g1", "ON YOUR MAC", "blue", 0, 1), ("g2", "STATEMENTLENS", "lav", 2, 5), ("g3", "WHEN THE STATEMENT COMES", "org", 6, 7)],
    notes=[(3, "<b>no rule matches:</b><br>counted, never guessed", "orange"),
           (6, "<b>paired:</b> the statement<br>line replaces the live row", "green")],
    footer="Each read rebuilds the live window from the messages, so a renamed payee never leaves a second copy.")

# ---------------- 5. how inboxkit reads Gmail ----------------
flow("05-how-inboxkit-reads-gmail", "How inboxkit reads a statement from Gmail", [
    ("<b>Your app asks</b><br>GmailDocuments.fetch(query)", "app", "query"),
    ("<b>Token from the keychain</b><br>under the app's<br>own service name", "vault", "valid<br>token"),
    ("<b>messages.list</b><br>every page of results,<br>retries on rate limits", "email", "message<br>ids"),
    ("<b>messages.get</b><br>+ attachments.get<br>headers, labels, PDFs", "docs", ""),
    ("<b>Document</b><br>filename, bytes,<br>headers, labels", "doc", ""),
    ("<b>authenticated(domain)</b><br>the DKIM / DMARC verdict<br>Gmail's server recorded", "cert", "proven"),
    ("<b>PdfDecryptor</b><br>tries the password<br>candidates in order", "key", "text"),
    ("<b>Text to your parser</b><br>bank, card, loan,<br>FD, NPS", "code", ""),
], [("g1", "YOUR APP + KEYCHAIN", "blue", 0, 1), ("g2", "GMAIL API, READ-ONLY", "lav", 2, 3),
    ("g3", "CHECK AND UNLOCK", "org", 4, 6), ("g4", "YOUR APP", "grey", 7, 7)],
    notes=[(1, "<b>first run only:</b> consent in<br>your browser, gmail.readonly", "orange"),
           (2, "<b>stopped early?</b> it says so<br>instead of returning less", "green")],
    footer="Plain Python on Google's Gmail API, on your machine: no AI, no MCP. The token is used only to call Gmail.")
print("wrote", sorted(p.name for p in OUT.glob("*.drawio")))
