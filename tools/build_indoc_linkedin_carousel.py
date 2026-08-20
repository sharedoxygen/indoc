#!/usr/bin/env python3
# flake8: noqa: E501
"""inDoc LinkedIn carousel — 4:5 document post, eight slides, plus caption."""
from __future__ import annotations

import importlib.util
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ASSET = ROOT / "private-docs/gtm/assets/introducing-indoc-linkedin"
PDF = ROOT / "private-docs/gtm/introducing-indoc-linkedin.pdf"
CAPTION = ROOT / "private-docs/gtm/introducing-indoc-linkedin.md"

_spec = importlib.util.spec_from_file_location(
    "gdoc", ROOT / "tools/build_graphrag_article_docx.py"
)
g = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(g)

S, PRIMARY, PRIMARY_50, ORANGE, ORANGE_50 = (
    g.S,
    g.PRIMARY,
    g.PRIMARY_50,
    g.ORANGE,
    g.ORANGE_50,
)
TEAL, TEAL_50, PURPLE, PURPLE_50 = g.TEAL, g.TEAL_50, g.PURPLE, g.PURPLE_50
GREEN, GREEN_50, NAVY, TEXT, MUTED, LINE, PAPER = (
    g.GREEN,
    g.GREEN_50,
    g.NAVY,
    g.TEXT,
    g.MUTED,
    g.LINE,
    g.PAPER,
)

W, H = 1080, 1350
TOTAL = 8


def flatten(img: Image.Image) -> Image.Image:
    rgb = Image.new("RGB", img.size, g.CANVAS)
    rgb.paste(img, mask=img.split()[-1])
    return rgb.resize((W, H), Image.Resampling.LANCZOS)


def save_png(img: Image.Image, name: str) -> Path:
    ASSET.mkdir(parents=True, exist_ok=True)
    out = ASSET / name
    flatten(img).save(out, "PNG", optimize=True)
    return out


def chrome(img: Image.Image, n: int, kicker: str = "inDoc") -> ImageDraw.ImageDraw:
    d = ImageDraw.Draw(img)
    g.draw_rr(d, (S(0), S(0), S(W), S(8)), 0, PRIMARY)
    g.txt(d, (S(72), S(48)), kicker, 16, True, PRIMARY)
    g.txt(d, (S(1008), S(48)), f"{n:02d}  /  {TOTAL:02d}", 14, True, MUTED, "rt")
    g.txt(d, (S(72), S(1294)), "Autonomous, but accountable.", 13, False, MUTED)
    g.txt(d, (S(1008), S(1294)), "Shared Oxygen", 13, False, MUTED, "rt")
    return d


def slide_cover() -> Image.Image:
    img = g.canvas(W, H)
    d = ImageDraw.Draw(img)
    g.draw_rr(d, (S(0), S(0), S(W), S(8)), 0, PRIMARY)
    g.txt(d, (S(72), S(72)), "inDoc", 18, True, PRIMARY)
    g.txt(d, (S(72), S(280)), "Most document AI", 42, True, NAVY)
    g.txt(d, (S(72), S(344)), "retrieves once.", 42, True, NAVY)
    g.wrapped(
        d,
        S(72),
        S(460),
        "That is not an investigation. And it is not a control system for regulated work.",
        S(900),
        24,
        False,
        TEXT,
        1.35,
    )
    g.plate(img, (S(72), S(680), S(1008), S(1120)), 18)
    d = ImageDraw.Draw(img)
    g.draw_rr(d, (S(72), S(680), S(80), S(1120)), 0, PRIMARY)
    g.txt(d, (S(112), S(724)), "Three capabilities", 16, True, PRIMARY)
    g.txt(d, (S(112), S(800)), "Agentic AI", 28, True, NAVY)
    g.txt(d, (S(112), S(860)), "Hybrid Search", 28, True, NAVY)
    g.txt(d, (S(112), S(920)), "Compliance", 28, True, NAVY)
    g.txt(d, (S(112), S(1020)), "On your infrastructure.", 16, False, MUTED)
    g.txt(d, (S(72), S(1294)), "Autonomous, but accountable.", 13, False, MUTED)
    g.txt(d, (S(1008), S(1294)), "01  /  08", 14, True, MUTED, "rt")
    return img


def slide_three() -> Image.Image:
    img = g.canvas(W, H)
    chrome(img, 2)
    d = ImageDraw.Draw(img)
    g.txt(d, (S(72), S(120)), "The product", 16, True, PRIMARY)
    g.wrapped(
        d,
        S(72),
        S(168),
        "Three capabilities. One platform.",
        S(920),
        34,
        True,
        NAVY,
        1.15,
    )
    cols = [
        (
            72,
            ORANGE,
            ORANGE_50,
            "01",
            "Agentic AI",
            "The agent plans, searches, reads, and finishes. Six tools. A live trace. A step budget.",
        ),
        (
            72,
            PRIMARY,
            PRIMARY_50,
            "02",
            "Hybrid Search",
            "Elasticsearch for the words. Qdrant for meaning. Scores fuse. Scope is applied before a result leaves.",
        ),
        (
            72,
            TEAL,
            TEAL_50,
            "03",
            "Compliance",
            "RBAC and ABAC. HIPAA and PCI modes. Audit and SIEM. Local model first. Restricted text stays out.",
        ),
    ]
    y = 340
    for x, accent, wash, num, title, body in cols:
        g.plate(img, (S(x), S(y), S(1008), S(y + 280)), 16)
        dd = ImageDraw.Draw(img)
        g.draw_rr(dd, (S(x), S(y), S(x + 8), S(y + 280)), 0, accent)
        g.pill(dd, (S(x + 28), S(y + 28), S(x + 98), S(y + 60)), wash, num, accent, 12)
        g.txt(dd, (S(x + 116), S(y + 44)), title, 22, True, NAVY, "lm")
        g.wrapped(dd, S(x + 28), S(y + 92), body, S(860), 17, False, TEXT, 1.32)
        y += 304
    return img


def slide_rag() -> Image.Image:
    img = g.canvas(W, H)
    chrome(img, 3)
    d = ImageDraw.Draw(img)
    g.txt(d, (S(72), S(120)), "The distinction", 16, True, PRIMARY)
    g.wrapped(
        d,
        S(72),
        S(168),
        "RAG retrieves once. inDoc investigates.",
        S(920),
        32,
        True,
        NAVY,
        1.15,
    )
    g.plate(img, (S(72), S(360), S(1008), S(680)), 16)
    d = ImageDraw.Draw(img)
    g.pill(d, (S(100), S(392), S(200), S(428)), ORANGE_50, "RAG", ORANGE, 12)
    g.txt(d, (S(100), S(468)), "Retrieve, stuff context, answer.", 20, True, NAVY)
    for i, line in enumerate(
        [
            "One retrieval",
            "One generation",
            "A fixed pipeline",
            "The model does not choose the next step",
        ]
    ):
        g.txt(d, (S(100), S(528 + i * 32)), f"{i+1:02d}   {line}", 15, False, MUTED)
    g.plate(img, (S(72), S(712), S(1008), S(1220)), 16)
    d = ImageDraw.Draw(img)
    g.draw_rr(d, (S(72), S(712), S(1008), S(720)), 0, PRIMARY)
    g.pill(d, (S(100), S(748), S(220), S(784)), PRIMARY_50, "Agent", PRIMARY, 12)
    g.txt(d, (S(100), S(824)), "Plan, act, observe, re-plan, answer.", 20, True, NAVY)
    for i, line in enumerate(
        [
            "Chooses each tool call",
            "Chains steps from evidence",
            "Stops when it has enough",
            "Returns a full trace",
        ]
    ):
        g.txt(d, (S(100), S(884 + i * 36)), f"{i+1:02d}   {line}", 16, True, NAVY)
    return img


def slide_trace() -> Image.Image:
    img = g.canvas(W, H)
    chrome(img, 4)
    d = ImageDraw.Draw(img)
    g.txt(d, (S(72), S(120)), "A product trace", 16, True, PRIMARY)
    g.wrapped(
        d,
        S(72),
        S(168),
        "What was Q3 revenue and its growth rate?",
        S(920),
        30,
        True,
        NAVY,
        1.15,
    )
    rows = [
        ("01", "Think", "Find the financial report first.", ORANGE, ORANGE_50),
        ("01", "Act", "Search documents  ·  revenue", GREEN, GREEN_50),
        ("01", "Observe", "Q3 Financial Report", PRIMARY, PRIMARY_50),
        ("02", "Think", "Read it for the exact figure.", ORANGE, ORANGE_50),
        ("02", "Act", "Read document  ·  9f6c…", GREEN, GREEN_50),
        ("02", "Observe", "$4.2M, up 18% YoY", PRIMARY, PRIMARY_50),
        ("03", "Finish", "Q3 2025 revenue was $4.2M, up 18% YoY", TEAL, TEAL_50),
    ]
    y = 360
    for n, kind, line, accent, wash in rows:
        g.plate(img, (S(72), S(y), S(1008), S(y + 112)), 12)
        dd = ImageDraw.Draw(img)
        g.pill(dd, (S(92), S(y + 36), S(154), S(y + 76)), wash, n, accent, 12)
        g.pill(dd, (S(168), S(y + 36), S(310), S(y + 76)), accent, kind, PAPER, 12)
        g.txt(dd, (S(334), S(y + 56)), line, 16, True, NAVY, "lm")
        y += 124
    return img


def slide_hybrid() -> Image.Image:
    img = g.canvas(W, H)
    chrome(img, 5)
    d = ImageDraw.Draw(img)
    g.txt(d, (S(72), S(120)), "Hybrid search", 16, True, PRIMARY)
    g.wrapped(
        d,
        S(72),
        S(168),
        "The words and the meaning. Fused. Then scoped.",
        S(920),
        30,
        True,
        NAVY,
        1.18,
    )
    g.plate(img, (S(72), S(360), S(516), S(780)), 16)
    d = ImageDraw.Draw(img)
    g.draw_rr(d, (S(72), S(360), S(516), S(368)), 0, PRIMARY)
    g.pill(d, (S(96), S(396), S(236), S(432)), PRIMARY_50, "Keyword", PRIMARY, 12)
    g.txt(d, (S(96), S(472)), "Elasticsearch", 22, True, NAVY)
    g.wrapped(
        d,
        S(96),
        S(528),
        "Clause numbers. Party names. The words on the page.",
        S(380),
        16,
        False,
        TEXT,
        1.3,
    )
    g.plate(img, (S(564), S(360), S(1008), S(780)), 16)
    d = ImageDraw.Draw(img)
    g.draw_rr(d, (S(564), S(360), S(1008), S(368)), 0, ORANGE)
    g.pill(d, (S(588), S(396), S(728), S(432)), ORANGE_50, "Vector", ORANGE, 12)
    g.txt(d, (S(588), S(472)), "Qdrant", 22, True, NAVY)
    g.wrapped(
        d,
        S(588),
        S(528),
        "Meaning. Nearby ideas when the nouns differ.",
        S(380),
        16,
        False,
        TEXT,
        1.3,
    )
    g.plate(img, (S(72), S(816), S(1008), S(1220)), 16)
    d = ImageDraw.Draw(img)
    g.pill(
        d, (S(96), S(852), S(360), S(888)), TEAL_50, "Fuse  ·  Equal Weight", TEAL, 12
    )
    g.txt(d, (S(96), S(940)), "One ranked list", 24, True, NAVY)
    g.wrapped(
        d,
        S(96),
        S(1004),
        "Min-max normalize. Alpha 0.5. Then the scope gate. Chat, the agent, and MCP share this path. Results are never returned unscoped.",
        S(860),
        17,
        False,
        TEXT,
        1.32,
    )
    return img


def slide_compliance() -> Image.Image:
    img = g.canvas(W, H)
    chrome(img, 6)
    d = ImageDraw.Draw(img)
    g.txt(d, (S(72), S(120)), "Compliance", 16, True, PRIMARY)
    g.wrapped(
        d,
        S(72),
        S(168),
        "The agent inherits the control plane.",
        S(920),
        30,
        True,
        NAVY,
        1.15,
    )
    items = [
        (72, 360, "Identity", "JWT. TOTP MFA. Session bound to a person.", PRIMARY),
        (564, 360, "Authorization", "RBAC. ABAC. Tenant isolation.", ORANGE),
        (72, 640, "Standards", "HIPAA. PCI-DSS. GDPR-ready. PHI scan.", TEAL),
        (
            564,
            640,
            "Evidence",
            "Full audit. SIEM export. Secret scanning in CI.",
            PURPLE,
        ),
        (
            72,
            920,
            "Tool Scope",
            "Every call scoped. Not available — not the text.",
            ORANGE,
        ),
        (
            564,
            920,
            "Model Path",
            "Ollama first. Air-gap capable. Cloud as fallback.",
            PRIMARY,
        ),
    ]
    for x, y, title, body, accent in items:
        g.plate(img, (S(x), S(y), S(x + 444), S(y + 248)), 14)
        dd = ImageDraw.Draw(img)
        g.draw_rr(dd, (S(x), S(y), S(x + 8), S(y + 248)), 0, accent)
        g.txt(dd, (S(x + 28), S(y + 28)), title, 18, True, NAVY)
        g.wrapped(dd, S(x + 28), S(y + 80), body, S(388), 16, False, TEXT, 1.3)
    return img


def slide_who() -> Image.Image:
    img = g.canvas(W, H)
    chrome(img, 7)
    d = ImageDraw.Draw(img)
    g.txt(d, (S(72), S(120)), "Who it is for", 16, True, PRIMARY)
    g.wrapped(
        d,
        S(72),
        S(168),
        "Healthcare, legal, and finance.",
        S(920),
        32,
        True,
        NAVY,
        1.15,
    )
    cards = [
        (
            72,
            360,
            "Healthcare",
            "HIPAA modes. PHI scan and redaction. Classification on every file.",
            PRIMARY,
        ),
        (
            72,
            620,
            "Legal",
            "Cited passages. Scoped libraries. A trace counsel can open.",
            ORANGE,
        ),
        (
            72,
            880,
            "Finance",
            "PCI-DSS modes. Dual index. An agent that cannot walk the book.",
            TEAL,
        ),
    ]
    for x, y, title, body, accent in cards:
        g.plate(img, (S(x), S(y), S(1008), S(y + 228)), 16)
        dd = ImageDraw.Draw(img)
        g.draw_rr(dd, (S(x), S(y), S(x + 8), S(y + 228)), 0, accent)
        g.txt(dd, (S(x + 36), S(y + 36)), title, 22, True, NAVY)
        g.wrapped(dd, S(x + 36), S(y + 96), body, S(860), 17, False, TEXT, 1.3)
    return img


def slide_close() -> Image.Image:
    img = g.canvas(W, H)
    d = ImageDraw.Draw(img)
    g.draw_rr(d, (S(0), S(0), S(W), S(8)), 0, PRIMARY)
    g.txt(d, (S(72), S(72)), "inDoc", 18, True, PRIMARY)
    g.txt(d, (S(1008), S(72)), "08  /  08", 14, True, MUTED, "rt")
    g.wrapped(
        d,
        S(72),
        S(280),
        "An investigation system, not a chat overlay.",
        S(900),
        36,
        True,
        NAVY,
        1.18,
    )
    g.wrapped(
        d,
        S(72),
        S(460),
        "A goal is planned, executed through tools, and closed with evidence. Hybrid search is the retrieve path. Compliance is the boundary. Generation can stay on your infrastructure.",
        S(900),
        20,
        False,
        TEXT,
        1.35,
    )
    g.plate(img, (S(72), S(720), S(1008), S(1120)), 18)
    d = ImageDraw.Draw(img)
    g.draw_rr(d, (S(72), S(720), S(1008), S(728)), 0, PRIMARY)
    g.txt(d, (S(112), S(776)), "Demonstration", 14, True, PRIMARY)
    g.txt(d, (S(112), S(824)), "sharedoxygen.github.io/indoc", 20, True, NAVY)
    g.txt(d, (S(112), S(900)), "Source", 14, True, PRIMARY)
    g.txt(d, (S(112), S(948)), "github.com/sharedoxygen/indoc", 20, True, NAVY)
    g.txt(d, (S(112), S(1032)), "Self-hosted. Air-gap capable.", 16, False, MUTED)
    g.txt(d, (S(72), S(1294)), "Autonomous, but accountable.", 13, False, MUTED)
    g.txt(d, (S(1008), S(1294)), "Shared Oxygen", 13, False, MUTED, "rt")
    return img


CAPTION_MD = """# Introducing inDoc — LinkedIn

**Format:** Native caption + 8-slide document (4:5 PDF).
**Do not** upload the Word briefing. LinkedIn will treat it as a file dump.

**Asset:** `introducing-indoc-linkedin.pdf`
**Slides:** `private-docs/gtm/assets/introducing-indoc-linkedin/`

---

## How to post

1. Create a post as yourself or the company page.
2. Attach the PDF as a **document** (not as images, not as a link-only post).
3. Paste the caption below. Keep the first line intact — it is the only line visible before “see more.”
4. No hashtag stack. One optional line at the end is enough.
5. First comment: the demo URL, once, if you want the link clickable and uncluttered in the caption.

---

## Caption

Most document AI retrieves once and writes an answer.

The model does not decide what to do next. When the answer is wrong, there is no investigation to inspect. When the user is not cleared for a file, policy text is not a control.

inDoc is built for that gap.

An agent investigates — it plans, searches, reads, and re-plans — and returns a trace a reviewer can open. Hybrid search finds the clause number and the nearby idea, then applies scope before a result leaves. Compliance binds the run: identity, classification, HIPAA and PCI modes, audit, SIEM, and a local model path.

Ask what Q3 revenue was. It finds the report, reads it, and returns $4.2 million, up 18% year over year.

Self-hosted. Air-gap capable.

Autonomous, but accountable.

---

## First comment

Demonstration: https://sharedoxygen.github.io/indoc/
Source: https://github.com/sharedoxygen/indoc

---

## Slide map

| Slide | Job |
|---|---|
| 01 | Stop the scroll. Name the three capabilities. |
| 02 | Equal weight: agentic AI, hybrid search, compliance. |
| 03 | RAG versus investigation. |
| 04 | Proof. A real product trace. |
| 05 | Hybrid search — keyword, vector, fuse, scope. |
| 06 | Compliance the agent inherits. |
| 07 | Healthcare, legal, finance. |
| 08 | Position and where to go. |

Eight slides. Portrait 4:5. That is the LinkedIn object. The Word briefing stays the leave-behind.
"""


def build() -> Path:
    makers = [
        ("01-cover.png", slide_cover),
        ("02-three.png", slide_three),
        ("03-rag.png", slide_rag),
        ("04-trace.png", slide_trace),
        ("05-hybrid.png", slide_hybrid),
        ("06-compliance.png", slide_compliance),
        ("07-who.png", slide_who),
        ("08-close.png", slide_close),
    ]
    pages: list[Image.Image] = []
    for name, fn in makers:
        path = save_png(fn(), name)
        pages.append(Image.open(path).convert("RGB"))
    PDF.parent.mkdir(parents=True, exist_ok=True)
    pages[0].save(PDF, "PDF", save_all=True, append_images=pages[1:], resolution=144.0)
    CAPTION.write_text(CAPTION_MD, encoding="utf-8")
    return PDF


if __name__ == "__main__":
    path = build()
    print(path)
    print("bytes", path.stat().st_size)
    print(CAPTION)
