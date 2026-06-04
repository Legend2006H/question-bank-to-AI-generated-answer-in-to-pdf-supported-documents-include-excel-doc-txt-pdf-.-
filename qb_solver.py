"""
QB Solver - Question Bank Answer Generator
==========================================
Reads your question bank (PDF/DOCX/TXT/XLSX) and generates
detailed answers as a clean, formatted PDF.

Usage:
    python qb_solver.py <your_file>

Examples:
    python qb_solver.py questions.pdf
    python qb_solver.py questions.docx
    python qb_solver.py questions.txt
"""

import sys
import os
import re
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv


load_dotenv()

# ── Groq API ──────────────────────────────────────────────────────────────────
from groq import Groq

GROQ_API_KEY = private = os.getenv("API_KEY")
client = Groq(api_key=GROQ_API_KEY)
MODEL  = "llama-3.3-70b-versatile"

# ── PDF generation ────────────────────────────────────────────────────────────
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable,
    KeepTogether, Table, TableStyle
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY

# ── File parsers ──────────────────────────────────────────────────────────────
import pdfplumber
from pypdf import PdfReader

try:
    import docx as python_docx
    DOCX_OK = True
except ImportError:
    DOCX_OK = False

try:
    import openpyxl
    XLSX_OK = True
except ImportError:
    XLSX_OK = False


# ═══════════════════════════════════════════════════════════════════════════════
#  FILE READING
# ═══════════════════════════════════════════════════════════════════════════════

def read_file(filepath):
    path = Path(filepath)
    ext  = path.suffix.lower()
    print(f"  Reading {path.name} ...")

    if ext == ".pdf":
        return read_pdf(filepath)
    elif ext in (".docx", ".doc"):
        return read_docx(filepath)
    elif ext in (".xlsx", ".xls"):
        return read_xlsx(filepath)
    else:
        return read_txt(filepath)


def read_pdf(filepath):
    parts = []
    try:
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    parts.append(t)
    except Exception:
        reader = PdfReader(filepath)
        for page in reader.pages:
            t = page.extract_text()
            if t:
                parts.append(t)
    return "\n\n".join(parts)


def read_docx(filepath):
    if not DOCX_OK:
        raise ImportError("Run: pip install python-docx")
    doc = python_docx.Document(filepath)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def read_xlsx(filepath):
    if not XLSX_OK:
        raise ImportError("Run: pip install openpyxl")
    wb   = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
    rows = []
    for sheet in wb.worksheets:
        rows.append(f"[Sheet: {sheet.title}]")
        for row in sheet.iter_rows(values_only=True):
            cells = [str(c) for c in row if c is not None]
            if cells:
                rows.append(" | ".join(cells))
    return "\n".join(rows)


def read_txt(filepath):
    for enc in ["utf-8", "utf-8-sig", "latin-1", "cp1252"]:
        try:
            with open(filepath, "r", encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Cannot decode {filepath}")


# ═══════════════════════════════════════════════════════════════════════════════
#  AI — EXTRACT QUESTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def extract_questions(raw_text):
    """
    Extract questions locally using regex — no API call, zero tokens used.
    Handles formats:
      1. Question text
      1) Question text
      Q1. Question text
      Q.1 Question text
    Multi-line questions are joined automatically.
    """
    print("  Identifying questions (local parser — no API tokens used) ...")

    lines = raw_text.splitlines()
    questions = []
    current = None
    current_num = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Match numbered question starters: 1. / 1) / Q1. / Q.1 / Q1) etc.
        m = re.match(
            r'^(?:Q\.?\s*)?(\d{1,3})\s*[.)]\s+(.+)',
            line, re.IGNORECASE
        )
        if m:
            num = int(m.group(1))
            text = m.group(2).strip()

            # Only accept if number is sequential (avoids matching random numbers)
            if current_num is None or num == current_num + 1:
                if current:
                    questions.append(current)
                current = text
                current_num = num
            else:
                # Continuation line that looks like a number but isn't sequential
                if current:
                    current += " " + line
        else:
            # Continuation of previous question
            if current is not None:
                # Stop appending if line looks like a section header (all caps, short)
                if not (len(line) < 40 and line.isupper()):
                    current += " " + line

    if current:
        questions.append(current)

    # Clean up extra whitespace in each question
    questions = [re.sub(r'\s+', ' ', q).strip() for q in questions if q.strip()]
    return questions


# ═══════════════════════════════════════════════════════════════════════════════
#  AI — ANSWER QUESTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def answer_question(question, q_num, total):
    print(f"  Answering Q{q_num}/{total}: {question[:65]}{'...' if len(question)>65 else ''}")

    prompt = f"""You are an expert academic tutor helping a student prepare for university exams.

Answer the following question in a detailed, clear, exam-ready format.

Rules:
- Give a comprehensive answer suitable for university exams
- Structure: definition → explanation → example (where applicable) → conclusion
- For compare/contrast questions: use clear distinctions
- For list/enumerate questions: use numbered or clear points
- For algorithmic/numerical questions: show step-by-step working
- Write in plain text only — NO markdown symbols like **, ##, *, or -
- answer according to the question asked according to there capacity of qution 2 marks, 4 marks, 10 marks, etc

Question: {question}

Answer:"""

    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=1000,
    )
    answer_text = resp.choices[0].message.content.strip()
    return {"question": question, "answer": clean_text(answer_text)}


def clean_text(text):
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*',     r'\1', text)
    text = re.sub(r'^#{1,6}\s+',    '',    text, flags=re.MULTILINE)
    text = re.sub(r'^\s*[-]\s+',    '  \u2022 ', text, flags=re.MULTILINE)
    text = re.sub(r'\n{3,}',        '\n\n', text)
    return text.strip()


def detect_marks(question):
    """Detect marks mentioned in a question string. Returns int or None."""
    if not question:
        return None
    # Common patterns: [10], (2), 2 marks, 2M, 2 M
    patterns = [r"\[(\d{1,3})\]", r"\((\d{1,3})\)", r"(\d{1,3})\s*(?:marks?|mark)\b", r"(\d{1,3})\s*M\b"]
    for p in patterns:
        m = re.search(p, question, re.IGNORECASE)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                continue
    return None


def find_marks_for_questions(raw_text, questions):
    """Try to locate marks in the original raw_text for each numbered question.
    Returns a list of detected mark ints (or None) aligned with `questions`.
    """
    results = [None] * len(questions)
    if not raw_text:
        return results

    for i, q in enumerate(questions, 1):
        # Try to find a block starting with the question number
        pattern = rf'(?:^|\n)\s*{i}[\.)]\s*(.*?)\n(?:\s*\n|$)'
        m = re.search(pattern, raw_text, re.DOTALL)
        block = None
        if m:
            block = m.group(1)
        else:
            # fallback: look within first 300 chars after the number
            pattern2 = rf'{i}[\.)]\s*(.{0,300})'
            m2 = re.search(pattern2, raw_text, re.DOTALL)
            if m2:
                block = m2.group(1)

        if block:
            mk = detect_marks(block)
            if mk:
                results[i-1] = mk
                continue

        # final fallback: try detecting in the extracted question text
        results[i-1] = detect_marks(q)

    return results


# ═══════════════════════════════════════════════════════════════════════════════
#  PDF GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

DARK_BLUE  = colors.HexColor("#1a2340")
MED_BLUE   = colors.HexColor("#2d4a8a")
LIGHT_BLUE = colors.HexColor("#e8f0fe")
ACCENT     = colors.HexColor("#4285f4")
Q_BG       = colors.HexColor("#f0f4ff")
Q_BORDER   = colors.HexColor("#4285f4")
DIVIDER    = colors.HexColor("#d0d8e8")
TEXT_DARK  = colors.HexColor("#1a1a2e")
TEXT_LIGHT = colors.HexColor("#6b7280")


def build_styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("title", parent=base["Normal"],
            fontName="Helvetica-Bold", fontSize=22, textColor=DARK_BLUE,
            alignment=TA_CENTER, spaceAfter=4),
        "subtitle": ParagraphStyle("subtitle", parent=base["Normal"],
            fontName="Helvetica", fontSize=10, textColor=TEXT_LIGHT,
            alignment=TA_CENTER, spaceAfter=6),
        "section_num": ParagraphStyle("section_num", parent=base["Normal"],
            fontName="Helvetica-Bold", fontSize=9, textColor=ACCENT,
            spaceBefore=14, spaceAfter=2),
        "question": ParagraphStyle("question", parent=base["Normal"],
            fontName="Helvetica-Bold", fontSize=11, textColor=DARK_BLUE,
            leading=16, spaceBefore=2, spaceAfter=4),
        "answer": ParagraphStyle("answer", parent=base["Normal"],
            fontName="Helvetica", fontSize=10.5, textColor=TEXT_DARK,
            leading=16, alignment=TA_JUSTIFY, spaceBefore=2, spaceAfter=6,
            leftIndent=4),
        "bullet": ParagraphStyle("bullet", parent=base["Normal"],
            fontName="Helvetica", fontSize=10.5, textColor=TEXT_DARK,
            leading=15, leftIndent=20, spaceAfter=2),
        "footer": ParagraphStyle("footer", parent=base["Normal"],
            fontName="Helvetica", fontSize=8, textColor=TEXT_LIGHT,
            alignment=TA_CENTER),
    }


def render_answer(answer_text, styles):
    flowables = []
    for para in answer_text.split("\n\n"):
        para = para.strip()
        if not para:
            continue
        for line in para.split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.startswith("\u2022") or line.startswith("  \u2022"):
                flowables.append(Paragraph(
                    "&bull;&nbsp;&nbsp;" + line.lstrip("\u2022 ").strip(),
                    styles["bullet"]))
            else:
                flowables.append(Paragraph(line, styles["answer"]))
        flowables.append(Spacer(1, 3))
    return flowables


def generate_pdf(qa_pairs, output_path, source_filename, subject="", level="", style=""):
    print(f"  Building PDF ...")
    styles = build_styles()
    W = A4[0] - 4.4*cm

    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=2.2*cm, rightMargin=2.2*cm,
        topMargin=2.5*cm,  bottomMargin=2.5*cm,
        title="Question Bank – Detailed Answers",
        author="QB Solver (Groq / Llama-3.3)",
    )

    story = []

    # ── Header ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.4*cm))

    hdr = Table([[Paragraph("QUESTION BANK — DETAILED ANSWERS",
        ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=9,
                       textColor=colors.white, alignment=TA_CENTER))]],
        colWidths=[W], rowHeights=[24])
    hdr.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), MED_BLUE),
        ("ALIGN",         (0,0),(-1,-1), "CENTER"),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
    ]))
    story.append(hdr)

    title_tbl = Table([[Paragraph("Answer Key", styles["title"])]],
        colWidths=[W], rowHeights=[54])
    title_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), LIGHT_BLUE),
        ("ALIGN",         (0,0),(-1,-1), "CENTER"),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("TOPPADDING",    (0,0),(-1,-1), 8),
        ("BOTTOMPADDING", (0,0),(-1,-1), 8),
    ]))
    story.append(title_tbl)
    story.append(Spacer(1, 0.3*cm))

    meta = meta = (f"Subject: {subject}   •   Level: {level}   •   Questions: {len(qa_pairs)}"
        f"   •   Generated: {datetime.now().strftime('%d %b %Y, %I:%M %p')}")
    story.append(Paragraph(meta, styles["subtitle"]))
    story.append(Spacer(1, 0.2*cm))
    story.append(HRFlowable(width="100%", thickness=1.5, color=ACCENT))
    story.append(Spacer(1, 0.3*cm))

    # ── Q&A blocks ────────────────────────────────────────────────────────────
    for i, qa in enumerate(qa_pairs, 1):

        # Question box
        q_tbl = Table([
            [Paragraph(f"QUESTION {i} of {len(qa_pairs)}", styles["section_num"])],
            [Paragraph(qa["question"], styles["question"])],
        ], colWidths=[W - 0.6*cm])
        q_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), Q_BG),
            ("LEFTPADDING",   (0,0),(-1,-1), 10),
            ("RIGHTPADDING",  (0,0),(-1,-1), 10),
            ("TOPPADDING",    (0,0),(-1,-1), 6),
            ("BOTTOMPADDING", (0,0),(-1,-1), 8),
            ("LINEBEFORE",    (0,0),(0,-1),  3, Q_BORDER),
        ]))

        # Answer label badge
        ans_badge = Table([[Paragraph("ANSWER",
            ParagraphStyle("ab", fontName="Helvetica-Bold", fontSize=8,
                           textColor=colors.white))]],
            colWidths=[62], rowHeights=[18])
        ans_badge.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), ACCENT),
            ("LEFTPADDING",   (0,0),(-1,-1), 8),
            ("RIGHTPADDING",  (0,0),(-1,-1), 8),
            ("TOPPADDING",    (0,0),(-1,-1), 3),
            ("BOTTOMPADDING", (0,0),(-1,-1), 3),
        ]))

        answer_parts = render_answer(qa["answer"], styles)

        story.append(KeepTogether([q_tbl, Spacer(1,5), ans_badge, Spacer(1,4)]))
        for part in answer_parts:
            story.append(part)
        story.append(Spacer(1, 5))
        story.append(HRFlowable(width="100%", thickness=0.5,
                                color=DIVIDER, spaceAfter=14))

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.4*cm))
    story.append(HRFlowable(width="100%", thickness=1, color=MED_BLUE))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        "Generated by QB Solver  \u2022  Powered by Groq + Llama-3.3-70b  \u2022  For academic use only",
        styles["footer"]))

    def page_num(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(TEXT_LIGHT)
        canvas.drawRightString(A4[0] - 2.2*cm, 1.8*cm, f"Page {canvas.getPageNumber()}")
        canvas.restoreState()

    doc.build(story, onFirstPage=page_num, onLaterPages=page_num)
    print(f"  PDF saved: {output_path}")

def parse_instruction_marks(instruction, q_num, total):
    """
    Parse user instruction to figure out how many marks this question is worth.
    Understands patterns like:
      - "first 10 questions 2 marks, rest 10 marks"
      - "first 5 short, remaining detailed"
      - "questions 1-10: 2 marks, 11 onwards: 10 marks"
    Returns an integer mark value or None.
    """
    text = instruction.lower()

    first_n_match = re.search(
        r'first\s+(\d+)(?:\s+questions?)?\s+.*?(\d+)[\s-]*marks?', text)
    rest_mark_match = re.search(
        r'(?:rest|remaining|others?)\s+.*?(\d+)[\s-]*marks?', text)
    first_short_match = re.search(
        r'first\s+(\d+)(?:\s+questions?)?\s+(?:short|2[\s-]mark|brief)', text)
    rest_long_match = re.search(
        r'(?:rest|remaining)\s+.*?(?:detailed|long|10[\s-]mark|big)', text)

    first_n = None
    first_marks = 2
    rest_marks = 10

    if first_n_match:
        first_n = int(first_n_match.group(1))
        first_marks = int(first_n_match.group(2))
    elif first_short_match:
        first_n = int(first_short_match.group(1))
        first_marks = 2

    if rest_mark_match:
        rest_marks = int(rest_mark_match.group(1))
    elif rest_long_match:
        rest_marks = 10

    if first_n is not None:
        return first_marks if q_num <= first_n else rest_marks

    range_matches = re.findall(r'(\d+)\s*[-to]+\s*(\d+).*?(\d+)\s*marks?', text)
    for start, end, mark in range_matches:
        if int(start) <= q_num <= int(end):
            return int(mark)

    if re.search(r'\b2[\s-]*marks?\b', text) and re.search(r'\b10[\s-]*marks?\b', text):
        midpoint = total // 2
        return 2 if q_num <= midpoint else 10

    return None


def marks_to_word_range(marks):
    if marks is None:
        return 120, 200
    if marks <= 2:
        return 50, 80
    elif marks <= 4:
        return 100, 150
    elif marks <= 5:
        return 130, 180
    elif marks <= 6:
        return 160, 220
    elif marks <= 8:
        return 200, 280
    elif marks <= 10:
        return 280, 380
    else:
        return 300, 450


def answer_question_personalised(question, q_num, total, subject, level, style, marks=""):
    print(f"  Answering Q{q_num}/{total}: {question[:65]}{'...' if len(question)>65 else ''}")

    # Priority 1: parse from user instruction (position-aware)
    instruction_marks = parse_instruction_marks(style, q_num, total)

    # Priority 2: detect from question text or passed marks arg
    detected = detect_marks(question)
    if not detected and marks:
        try:
            detected = int(marks)
        except Exception:
            pass

    final_marks = instruction_marks if instruction_marks is not None else detected
    wmin, wmax = marks_to_word_range(final_marks)
    mark_label = f"{final_marks}-mark" if final_marks else "standard"
    print(f"       Q{q_num}: {mark_label} → {wmin}–{wmax} words")

    prompt = f"""You are an expert academic tutor. The student's instruction is:

"{style}"

Answer Question {q_num} below. This is a {mark_label} answer.
Write between {wmin} and {wmax} words. Do NOT exceed {wmax} words.
Rules:
- Plain text only. No markdown, no **, no ##, no bullet dashes.
- No meta-comments like "This is a 2-mark answer".
- Short answers (under 100 words): clear, direct definition or explanation only.
- Long answers (100+ words): definition, explanation, example, conclusion.
- Use numbered points only if the question says "list" or "enumerate".

Question: {question}

Answer:"""

    max_tokens = min(2048, int(wmax * 2.2))
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.25,
        max_tokens=max_tokens,
    )
    answer_text = resp.choices[0].message.content.strip()

    words = re.findall(r"\S+", answer_text)
    if len(words) > wmax:
        answer_text = " ".join(words[:wmax]).rstrip()
        if not answer_text.endswith(('.', '?', '!')):
            answer_text += "."

    return {"question": question, "answer": clean_text(answer_text)}


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    if len(sys.argv) < 2:
        print("Usage: python qb_solver.py yourfile.pdf")
        sys.exit(1)

    input_file = sys.argv[1]
    if not os.path.exists(input_file):
        print(f"ERROR: File not found: {input_file}")
        sys.exit(1)

    source_name = Path(input_file).name
    output_file = Path(input_file).stem + "_ANSWERS.pdf"

    print("\n" + "="*60)
    print("  QB SOLVER — Powered by Groq + Llama-3.3-70b")
    print("="*60)

    # ── Ask user for a single free-form instruction ───────────────────────────
    print("\n  Enter your instruction for how the AI should answer (then press Enter):")
    print("  Example: Engineering Sem 4 OS exam, first 10 questions short 2-mark answers, rest detailed 10-mark answers with examples")
    print()
    user_instruction = input("  > ").strip()
    if not user_instruction:
        user_instruction = "detailed, exam-ready answers suitable for a university student"

    # These are kept for PDF metadata — extracted from instruction or set to defaults
    subject = user_instruction[:60]
    level   = ""
    answer_style = user_instruction

    print()

    print("[1/4] Reading your question bank...")
    raw_text = read_file(input_file)
    if not raw_text.strip():
        print("ERROR: No text extracted.")
        sys.exit(1)
    print(f"       Extracted {len(raw_text)} characters.")

    print("\n[2/4] Identifying questions...")
    questions = extract_questions(raw_text)
    if not questions:
        print("ERROR: No questions found.")
        sys.exit(1)
    print(f"       Found {len(questions)} questions.")

    print(f"\n[3/4] Generating answers...")
    qa_pairs = []

    # Try to detect marks from original extracted raw text to preserve annotations
    marks_list = find_marks_for_questions(raw_text, questions)

    for i, q in enumerate(questions, 1):
        try:
            detected_marks = marks_list[i-1] if marks_list and i-1 < len(marks_list) else None
            # fallback to direct detection in case find_marks failed
            if not detected_marks:
                detected_marks = detect_marks(q)
            if detected_marks:
                print(f"       Detected marks for Q{i}: {detected_marks}")
            qa_pairs.append(answer_question_personalised(q, i, len(questions), subject, level, answer_style, marks=detected_marks))
        except Exception as e:
            print(f"       WARNING Q{i} failed: {e}")
            qa_pairs.append({"question": q, "answer": "Could not generate answer."})

    print(f"\n[4/4] Creating PDF...")
    generate_pdf(qa_pairs, output_file, source_name, subject, level, answer_style)

    print("\n" + "="*60)
    print(f"  SUCCESS!  =>  {os.path.abspath(output_file)}")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()