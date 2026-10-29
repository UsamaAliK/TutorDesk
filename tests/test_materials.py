import io
import unittest
import zipfile
from pydantic import ValidationError

from backend.schemas.material import (
    EducationalLevel,
    DifficultyLevel,
    SourceMode,
    LessonGenerateRequest,
    QuizGenerateRequest,
    AssignmentGenerateRequest,
)
from backend.services.export import export_to_pdf, export_to_docx
from backend.db.models import Material


class TestMaterialSchemas(unittest.TestCase):
    def test_quiz_distribution_validation_success(self):
        req = QuizGenerateRequest(
            subject="Computer Science",
            topic="Binary Trees",
            educational_level=EducationalLevel.BACHELORS,
            difficulty=DifficultyLevel.MEDIUM,
            total_questions=10,
            num_mcqs=6,
            num_short_answer=3,
            num_long_answer=1,
            mcq_options_count=4,
        )
        self.assertEqual(req.total_questions, 10)
        self.assertEqual(req.num_mcqs + req.num_short_answer + req.num_long_answer, 10)

    def test_quiz_distribution_validation_mismatch_fails(self):
        with self.assertRaises(ValidationError) as ctx:
            QuizGenerateRequest(
                subject="Biology",
                topic="Photosynthesis",
                educational_level=EducationalLevel.GRADE_9_12,
                total_questions=10,
                num_mcqs=5,
                num_short_answer=2,
                num_long_answer=1,  # sum is 8 != 10
            )
        self.assertIn("Question distribution", str(ctx.exception))

    def test_lesson_duration_validation(self):
        req = LessonGenerateRequest(
            subject="History",
            topic="The Renaissance",
            educational_level=EducationalLevel.GRADE_9_12,
            duration_minutes=40,
        )
        self.assertEqual(req.duration_minutes, 40)

        # Out of bounds duration (< 10)
        with self.assertRaises(ValidationError):
            LessonGenerateRequest(
                subject="History",
                topic="The Renaissance",
                duration_minutes=5,
            )

        # Out of bounds duration (> 120)
        with self.assertRaises(ValidationError):
            LessonGenerateRequest(
                subject="History",
                topic="The Renaissance",
                duration_minutes=150,
            )

    def test_assignment_schema_defaults(self):
        req = AssignmentGenerateRequest(
            subject="Physics",
            topic="Kinematics",
            educational_level=EducationalLevel.BACHELORS,
            total_tasks=5,
        )
        self.assertEqual(req.total_tasks, 5)
        self.assertIn("short_answer", req.task_types)
        self.assertEqual(req.source_mode, SourceMode.WEB_SEARCH)


class TestExportEngine(unittest.TestCase):
    def setUp(self):
        self.sample_quiz_material = Material(
            id=1,
            user_id=1,
            type="quiz",
            title="Quiz: Cellular Respiration",
            subject="Biology",
            topic="Cellular Respiration",
            educational_level="Grades 9-12",
            difficulty="Medium",
            source_mode="web_search",
            content_json={
                "title": "Quiz: Cellular Respiration",
                "instructions_for_students": "Answer all 2 questions.",
                "questions": [
                    {
                        "id": "q1",
                        "type": "mcq",
                        "prompt": "Where does glycolysis occur?",
                        "options": ["A) Cytoplasm", "B) Mitochondria", "C) Ribosome", "D) Nucleus"],
                        "correct_answer": "A) Cytoplasm",
                        "explanation": "Glycolysis takes place in the cytoplasm of the cell.",
                        "marks": 1,
                    },
                    {
                        "id": "q2",
                        "type": "short_answer",
                        "prompt": "Explain the role of ATP synthase.",
                        "options": [],
                        "correct_answer": "Synthesizes ATP from ADP and inorganic phosphate.",
                        "explanation": "Key mechanism in oxidative phosphorylation.",
                        "marks": 3,
                    }
                ],
                "sources": ["https://example.com/biology"],
            }
        )

        self.sample_lesson_material = Material(
            id=2,
            user_id=1,
            type="lesson",
            title="Lesson: Neural Networks",
            subject="Computer Science",
            topic="Neural Networks",
            educational_level="Bachelor's Degree",
            difficulty="Standard",
            source_mode="web_search",
            content_json={
                "title": "Lesson: Neural Networks",
                "overview": "Introduction to Perceptrons and Multi-layer Networks.",
                "learning_objectives": ["Understand forward propagation", "Define activation functions"],
                "sections": [
                    {
                        "id": "sec_1",
                        "title": "Introduction to Neurons",
                        "time_minutes": 15,
                        "concepts": "Artificial neurons simulate biological synaptic activation.",
                        "examples": ["Binary classification of linear data."],
                        "activities": "Calculate neuron output by hand."
                    }
                ],
                "summary": "Neurons apply weights, biases, and non-linearities to produce output.",
                "sources": [],
            }
        )

    def test_export_quiz_pdf_teacher_and_student(self):
        teacher_pdf = export_to_pdf(self.sample_quiz_material, audience="teacher")
        self.assertTrue(teacher_pdf.startswith(b"%PDF-"))
        self.assertGreater(len(teacher_pdf), 500)

        student_pdf = export_to_pdf(self.sample_quiz_material, audience="student")
        self.assertTrue(student_pdf.startswith(b"%PDF-"))
        self.assertGreater(len(student_pdf), 500)

    def test_export_lesson_docx(self):
        docx_bytes = export_to_docx(self.sample_lesson_material, audience="teacher")
        self.assertGreater(len(docx_bytes), 500)

        # Verify it's a valid zip archive with word/document.xml
        with zipfile.ZipFile(io.BytesIO(docx_bytes), "r") as z:
            namelist = z.namelist()
            self.assertIn("word/document.xml", namelist)
            self.assertIn("[Content_Types].xml", namelist)
            xml_content = z.read("word/document.xml").decode("utf-8")
            self.assertIn("Neural Networks", xml_content)
            self.assertIn("Artificial neurons", xml_content)


if __name__ == "__main__":
    unittest.main()

