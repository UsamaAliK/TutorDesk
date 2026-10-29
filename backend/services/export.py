import io
import fitz
import zipfile
from xml.sax.saxutils import escape
from backend.db.models import Material


def _format_material_text(material: Material, audience: str = "teacher") -> list[tuple[str, str]]:
    """
    Returns a structured list of (heading, text_block) tuples representing the content.
    Audience can be 'student' (excludes answers and rubrics) or 'teacher' (full details).
    """
    content = material.content_json or {}
    mtype = material.type.lower()
    is_teacher = audience.lower() == "teacher"
    blocks = []

    # Title & Metadata
    title = material.title or content.get("title", "Educational Material")
    meta = f"Subject: {material.subject}  |  Topic: {material.topic}  |  Level: {material.educational_level}"
    if material.difficulty:
        meta += f"  |  Difficulty: {material.difficulty}"
    blocks.append(("TITLE", title))
    blocks.append(("META", meta))

    if mtype == "lesson":
        if content.get("overview"):
            blocks.append(("Overview", content["overview"]))
        if content.get("learning_objectives"):
            objs = "\n".join(f"• {obj}" for obj in content["learning_objectives"])
            blocks.append(("Learning Objectives", objs))
        if content.get("prerequisite_knowledge"):
            prereqs = "\n".join(f"• {p}" for p in content["prerequisite_knowledge"])
            blocks.append(("Prerequisite Knowledge", prereqs))

        for sec in content.get("sections", []):
            sec_title = f"{sec.get('title', 'Section')} ({sec.get('time_minutes', 10)} mins)"
            sec_body = sec.get("concepts", "")
            if sec.get("examples"):
                examples_text = "\n".join(f"- {ex}" for ex in sec["examples"])
                sec_body += f"\n\nExamples:\n{examples_text}"
            if sec.get("activities"):
                sec_body += f"\n\nActivity:\n{sec['activities']}"
            blocks.append((sec_title, sec_body))

        if content.get("practice_questions"):
            pq_body = []
            for i, pq in enumerate(content["practice_questions"], 1):
                pq_body.append(f"{i}. {pq.get('question', '')}")
                if is_teacher and pq.get("guidance"):
                    pq_body.append(f"   [Teacher Guidance: {pq['guidance']}]")
            blocks.append(("Practice Questions", "\n".join(pq_body)))

        if content.get("summary"):
            blocks.append(("Summary", content["summary"]))
        if content.get("assessment_followup"):
            blocks.append(("Assessment & Follow-Up", content["assessment_followup"]))

    elif mtype == "quiz":
        inst = content.get("instructions_for_students") or "Answer all questions to the best of your ability."
        blocks.append(("General Instructions", inst))

        mcqs = content.get("mcq_section", {}).get("mcqs", [])
        written = content.get("questions_section", {}).get("questions", [])

        # Fallback to questions array if sections not explicitly present
        if not mcqs and not written and content.get("questions"):
            for q in content["questions"]:
                if q.get("type") == "mcq" or q.get("options"):
                    mcqs.append(q)
                else:
                    written.append(q)

        # ── Section A: MCQs ──
        if mcqs:
            mcq_blocks = []
            mcq_instructions = content.get("mcq_section", {}).get("instructions")
            if mcq_instructions:
                mcq_blocks.append(mcq_instructions + "\n")
            for i, q in enumerate(mcqs, 1):
                marks = f"({q.get('marks', 1)} pt{'s' if q.get('marks', 1) != 1 else ''})"
                item_text = f"{i}. {q.get('prompt', '')} {marks}"
                if q.get("options"):
                    item_text += "\n" + "\n".join(f"   {opt}" for opt in q["options"])
                mcq_blocks.append(item_text)
            blocks.append(("SECTION A: MULTIPLE CHOICE QUESTIONS", "\n\n".join(mcq_blocks)))

        # ── Section B: Written Questions ──
        if written:
            written_blocks = []
            written_instructions = content.get("questions_section", {}).get("instructions")
            if written_instructions:
                written_blocks.append(written_instructions + "\n")
            for i, q in enumerate(written, 1):
                q_type = q.get("type", "Short Answer").replace("_", " ").title()
                marks = f"({q.get('marks', 2)} pt{'s' if q.get('marks', 2) != 1 else ''})"
                written_blocks.append(f"{i}. [{q_type}] {q.get('prompt', '')} {marks}")
            blocks.append(("SECTION B: SHORT & LONG ANSWER QUESTIONS", "\n\n".join(written_blocks)))

        # ── Teacher Answer Key ──
        if is_teacher:
            key_blocks = []
            if mcqs:
                key_blocks.append("--- SECTION A ANSWER KEY ---")
                for i, q in enumerate(mcqs, 1):
                    ans = f"{i}. Correct Answer: {q.get('correct_answer', 'N/A')}"
                    if q.get("explanation"):
                        ans += f"\n   Explanation: {q['explanation']}"
                    key_blocks.append(ans)
            if written:
                key_blocks.append("\n--- SECTION B MODEL ANSWERS & RUBRIC ---")
                for i, q in enumerate(written, 1):
                    ans = f"{i}. Model Answer:\n   {q.get('correct_answer', 'Criteria-based response.')}"
                    if q.get("explanation"):
                        ans += f"\n   Grading Rationale: {q['explanation']}"
                    key_blocks.append(ans)
            blocks.append(("Teacher Answer Key & Explanations", "\n\n".join(key_blocks)))

    elif mtype == "assignment":
        if content.get("instructions_for_students"):
            blocks.append(("Instructions", content["instructions_for_students"]))

        tasks = content.get("tasks", [])
        t_blocks = []
        teacher_solutions = []

        for i, t in enumerate(tasks, 1):
            marks = f"[{t.get('marks', 5)} marks]"
            t_prompt = f"Task {i}: {t.get('title', '')} {marks}\n{t.get('prompt', '')}"
            t_blocks.append(t_prompt)

            if is_teacher:
                sol = f"Task {i} Model Answer:\n{t.get('model_answer', 'No model answer provided.')}"
                if t.get("rubric_criteria"):
                    sol += "\nRubric Criteria:\n" + "\n".join(
                        f" - {rc.get('criterion', '')} ({rc.get('points', 0)} pts): {rc.get('description', '')}"
                        for rc in t["rubric_criteria"]
                    )
                teacher_solutions.append(sol)

        blocks.append(("Tasks", "\n\n".join(t_blocks)))

        if is_teacher and teacher_solutions:
            blocks.append(("Teacher Solutions & Grading Rubric", "\n\n".join(teacher_solutions)))

    return blocks


def export_to_pdf(material: Material, audience: str = "teacher") -> bytes:
    """Exports structured educational material to a clean, readable PDF."""
    doc = fitz.open()
    blocks = _format_material_text(material, audience=audience)

    page = doc.new_page(width=595, height=842) # A4
    y = 54
    line_height = 14
    max_y = 780
    margin_x = 54

    for heading, text_body in blocks:
        # Check remaining space for heading
        if y > max_y - 40:
            page = doc.new_page(width=595, height=842)
            y = 54

        if heading == "TITLE":
            page.insert_text((margin_x, y), text_body[:80], fontsize=18, fontname="helv", color=(0.17, 0.24, 0.24))
            y += 24
            continue
        elif heading == "META":
            page.insert_text((margin_x, y), text_body[:100], fontsize=9, fontname="helv", color=(0.4, 0.5, 0.45))
            y += 18
            # Draw divider line
            page.draw_line(fitz.Point(margin_x, y), fitz.Point(541, y), color=(0.7, 0.75, 0.72), width=1)
            y += 20
            continue

        # Section Heading
        page.insert_text((margin_x, y), heading, fontsize=12, fontname="helv", color=(0.17, 0.24, 0.24))
        y += 18

        # Section Body (wrap lines)
        for paragraph in text_body.split("\n"):
            # Simple line chunker for PDF
            words = paragraph.split(" ")
            current_line = []
            for w in words:
                current_line.append(w)
                if len(" ".join(current_line)) > 75:
                    if y > max_y:
                        page = doc.new_page(width=595, height=842)
                        y = 54
                    page.insert_text((margin_x + 8, y), " ".join(current_line), fontsize=9.5, fontname="helv", color=(0.1, 0.1, 0.1))
                    y += line_height
                    current_line = []
            if current_line:
                if y > max_y:
                    page = doc.new_page(width=595, height=842)
                    y = 54
                page.insert_text((margin_x + 8, y), " ".join(current_line), fontsize=9.5, fontname="helv", color=(0.1, 0.1, 0.1))
                y += line_height
            y += 4
        y += 10

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def export_to_docx(material: Material, audience: str = "teacher") -> bytes:
    """Exports structured educational material to an OpenXML .docx file."""
    blocks = _format_material_text(material, audience=audience)
    paragraphs_xml = []

    for heading, text_body in blocks:
        if heading == "TITLE":
            esc = escape(text_body)
            paragraphs_xml.append(f"<w:p><w:pPr><w:jc w:val='left'/></w:pPr><w:r><w:rPr><w:b/><w:sz w:val='36'/><w:color w:val='2C3E3E'/></w:rPr><w:t>{esc}</w:t></w:r></w:p>")
            continue
        elif heading == "META":
            esc = escape(text_body)
            paragraphs_xml.append(f"<w:p><w:r><w:rPr><w:i/><w:sz w:val='18'/><w:color w:val='5A6F6D'/></w:rPr><w:t>{esc}</w:t></w:r></w:p>")
            continue

        # Heading
        esc_h = escape(heading)
        paragraphs_xml.append(f"<w:p><w:pPr><w:spacing w:before='240' w:after='120'/></w:pPr><w:r><w:rPr><w:b/><w:sz w:val='24'/><w:color w:val='2C3E3E'/></w:rPr><w:t>{esc_h}</w:t></w:r></w:p>")

        # Paragraphs
        for p in text_body.split("\n"):
            esc_p = escape(p)
            paragraphs_xml.append(f"<w:p><w:pPr><w:spacing w:after='80'/></w:pPr><w:r><w:rPr><w:sz w:val='20'/></w:rPr><w:t>{esc_p}</w:t></w:r></w:p>")

    doc_body = "".join(paragraphs_xml)
    main_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    {doc_body}
  </w:body>
</w:document>"""

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>'
        )
        z.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>'
        )
        z.writestr("word/document.xml", main_xml)

    return buf.getvalue()

