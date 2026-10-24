import json
import os
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


# =========================================================
# PATHS AND ENVIRONMENT
# =========================================================

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
HISTORY_FILE = DATA_DIR / "history.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv(ROOT / ".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()


# =========================================================
# FASTAPI APPLICATION
# =========================================================

app = FastAPI(
    title="Quizora AI API",
    description="AI-powered quiz generation and quiz history API.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# REQUEST MODELS
# =========================================================

class QuizRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=200)
    count: int = Field(default=5, ge=1, le=20)
    difficulty: str = "Medium"
    language: str = "English"


class QuizSubmission(BaseModel):
    # Supports both "title" and "topic" from the frontend.
    title: str = ""
    topic: str = ""
    questions: list[dict[str, Any]] = Field(default_factory=list)

    # Frontend may send either a list or a dictionary.
    answers: Any = Field(default_factory=list)

    score: int | None = None
    total: int | None = None
    percentage: float | None = None
    auto_submitted: bool = False


# =========================================================
# OFFLINE QUESTION BANK
# Used when Groq is not configured or unavailable.
# =========================================================

OFFLINE_BANK = {
    "python": [
        {
            "question": "Which keyword defines a function in Python?",
            "options": ["func", "def", "function", "define"],
            "answer": "def",
            "answer_index": 1,
            "explanation": "Python uses the def keyword to define a function.",
        },
        {
            "question": "Which data type stores key-value pairs?",
            "options": ["List", "Tuple", "Dictionary", "Set"],
            "answer": "Dictionary",
            "answer_index": 2,
            "explanation": "A dictionary stores data as key-value pairs.",
        },
        {
            "question": "Which symbol starts a comment in Python?",
            "options": ["//", "#", "/*", "--"],
            "answer": "#",
            "answer_index": 1,
            "explanation": "A single-line Python comment starts with #.",
        },
        {
            "question": "Which function displays output in Python?",
            "options": ["echo()", "write()", "print()", "display()"],
            "answer": "print()",
            "answer_index": 2,
            "explanation": "The print() function displays output.",
        },
        {
            "question": "Which collection is immutable?",
            "options": ["List", "Dictionary", "Set", "Tuple"],
            "answer": "Tuple",
            "answer_index": 3,
            "explanation": "A tuple cannot be modified after creation.",
        },
    ],
    "physics": [
        {
            "question": "What is the SI unit of force?",
            "options": ["Joule", "Newton", "Watt", "Pascal"],
            "answer": "Newton",
            "answer_index": 1,
            "explanation": "Force is measured in newtons.",
        },
        {
            "question": "What is the approximate speed of light in vacuum?",
            "options": [
                "3 × 10⁶ m/s",
                "3 × 10⁸ m/s",
                "3 × 10⁵ m/s",
                "3 × 10⁴ m/s",
            ],
            "answer": "3 × 10⁸ m/s",
            "answer_index": 1,
            "explanation": "Light travels at approximately 3 × 10⁸ m/s in vacuum.",
        },
        {
            "question": "Which instrument measures electric current?",
            "options": ["Voltmeter", "Barometer", "Ammeter", "Thermometer"],
            "answer": "Ammeter",
            "answer_index": 2,
            "explanation": "An ammeter measures electric current.",
        },
    ],
    "biology": [
        {
            "question": "What is the basic unit of life?",
            "options": ["Tissue", "Organ", "Cell", "Atom"],
            "answer": "Cell",
            "answer_index": 2,
            "explanation": "The cell is the basic structural and functional unit of life.",
        },
        {
            "question": "Which organelle performs photosynthesis?",
            "options": ["Mitochondrion", "Chloroplast", "Nucleus", "Ribosome"],
            "answer": "Chloroplast",
            "answer_index": 1,
            "explanation": "Chloroplasts contain chlorophyll and perform photosynthesis.",
        },
        {
            "question": "Which molecule carries genetic information?",
            "options": ["DNA", "Glucose", "Starch", "Water"],
            "answer": "DNA",
            "answer_index": 0,
            "explanation": "DNA stores hereditary genetic information.",
        },
    ],
}


# =========================================================
# HISTORY HELPERS
# =========================================================

def read_history() -> list[dict[str, Any]]:
    """Read saved attempts. Never add demo records automatically."""

    if not HISTORY_FILE.exists():
        return []

    try:
        with HISTORY_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, list):
            return data

        if isinstance(data, dict):
            history = data.get("history", [])
            return history if isinstance(history, list) else []

    except (json.JSONDecodeError, OSError):
        return []

    return []


def write_history(history: list[dict[str, Any]]) -> None:
    """Save history safely using a temporary file."""

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    temp_file = HISTORY_FILE.with_suffix(".tmp")

    with temp_file.open("w", encoding="utf-8") as file:
        json.dump(history, file, ensure_ascii=False, indent=2)

    temp_file.replace(HISTORY_FILE)


def normalise_history_item(item: dict[str, Any]) -> dict[str, Any]:
    """Return consistent field names for the frontend."""

    title = (
        item.get("title")
        or item.get("topic")
        or "Untitled Quiz"
    )

    score = int(item.get("score", 0) or 0)
    total = int(item.get("total", 0) or 0)

    percentage = item.get(
        "percentage",
        item.get("percent", 0),
    )

    try:
        percentage = float(percentage or 0)
    except (TypeError, ValueError):
        percentage = 0.0

    created_at = (
        item.get("created_at")
        or item.get("date")
        or item.get("timestamp")
        or ""
    )

    return {
        **item,
        "title": title,
        "topic": title,
        "score": score,
        "total": total,
        "percentage": percentage,
        "percent": percentage,
        "created_at": created_at,
    }


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/")
def home():
    return {
        "name": "Quizora AI",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/api/health")
def health():
    return {
        "status": "healthy",
        "ai_configured": bool(GROQ_API_KEY),
        "service": "Quizora AI Backend",
    }


# =========================================================
# AI QUIZ GENERATION
# =========================================================

def get_offline_questions(topic: str, count: int):
    topic_lower = topic.lower()

    bank = None

    for keyword, questions in OFFLINE_BANK.items():
        if keyword in topic_lower:
            bank = questions
            break

    if bank is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "AI quiz generation is unavailable. "
                "Configure GROQ_API_KEY in the root .env file "
                "or try Python, Physics, or Biology."
            ),
        )

    selected = random.sample(bank, k=min(count, len(bank)))

    # Repeat questions only when more questions were requested
    # than the offline bank contains.
    while len(selected) < count:
        selected.append(random.choice(bank).copy())

    return selected[:count]


def generate_with_groq(
    topic: str,
    count: int,
    difficulty: str,
    language: str,
):
    try:
        from groq import Groq

        client = Groq(api_key=GROQ_API_KEY)

        prompt = f"""
Create exactly {count} multiple-choice quiz questions.

Topic: {topic}
Difficulty: {difficulty}
Language: {language}

Return ONLY a valid JSON object with this structure:
{{
  "questions": [
    {{
      "question": "Question text",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "answer_index": 0,
      "explanation": "Short explanation"
    }}
  ]
}}

Rules:
- Each question must have exactly four options.
- answer_index must be an integer from 0 to 3.
- Questions must be factually accurate.
- Do not include markdown or text outside the JSON.
- Do not include the correct answer inside the question text.
"""

        completion = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {
                    "role": "system",
                    "content": "You generate accurate educational quizzes and valid JSON.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.4,
            response_format={"type": "json_object"},
        )

        content = completion.choices[0].message.content

        if not content:
            raise ValueError("The AI returned an empty response.")

        parsed = json.loads(content)
        questions = parsed.get("questions", [])

        if not isinstance(questions, list) or not questions:
            raise ValueError("The AI did not return a valid question list.")

        validated = []

        for item in questions[:count]:
            options = item.get("options", [])
            answer_index = item.get("answer_index", 0)

            if not isinstance(options, list) or len(options) != 4:
                continue

            try:
                answer_index = int(answer_index)
            except (ValueError, TypeError):
                continue

            if answer_index < 0 or answer_index > 3:
                continue

            question_text = str(item.get("question", "")).strip()

            if not question_text:
                continue

            validated.append({
                "question": question_text,
                "options": [str(option) for option in options],
                "answer_index": answer_index,
                "answer": str(options[answer_index]),
                "explanation": str(item.get("explanation", "")),
            })

        if not validated:
            raise ValueError("No valid questions were generated.")

        return validated

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"AI quiz generation failed: {str(exc)}",
        ) from exc


@app.post("/api/generate-quiz")
def generate_quiz(request: QuizRequest):
    topic = request.topic.strip()

    if not topic:
        raise HTTPException(status_code=400, detail="Topic is required.")

    difficulty = request.difficulty.strip().capitalize()

    if difficulty not in {"Easy", "Medium", "Hard"}:
        difficulty = "Medium"

    if GROQ_API_KEY:
        questions = generate_with_groq(
            topic=topic,
            count=request.count,
            difficulty=difficulty,
            language=request.language,
        )
        source = "Groq AI"
    else:
        questions = get_offline_questions(topic, request.count)
        source = "Offline Question Bank"

    return {
        "title": topic,
        "topic": topic,
        "difficulty": difficulty,
        "source": source,
        "questions": questions,
        "total": len(questions),
    }


# =========================================================
# MATERIAL UPLOAD
# =========================================================

@app.post("/api/upload-material")
async def upload_material(file: UploadFile = File(...)):
    filename = file.filename or "uploaded-file"
    extension = Path(filename).suffix.lower()

    allowed_extensions = {".txt", ".pdf", ".docx"}

    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Supported formats: TXT, PDF, DOCX.",
        )

    content = await file.read()

    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="File size must be 10 MB or less.",
        )

    if not content:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty.",
        )

    try:
        if extension == ".txt":
            text_content = content.decode("utf-8", errors="replace")

        elif extension == ".pdf":
            from pypdf import PdfReader
            import io

            reader = PdfReader(io.BytesIO(content))

            text_content = "\n".join(
                page.extract_text() or ""
                for page in reader.pages
            )

        else:
            from docx import Document
            import io

            document = Document(io.BytesIO(content))

            text_content = "\n".join(
                paragraph.text
                for paragraph in document.paragraphs
            )

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Unable to read the uploaded file: {str(exc)}",
        ) from exc

    word_count = len(text_content.split())

    return {
        "filename": filename,
        "characters": len(text_content),
        "words": word_count,
        "text": text_content[:30000],
        "message": "Material extracted successfully.",
    }


# =========================================================
# QUIZ SUBMISSION AND SCORE CALCULATION
# =========================================================

def get_selected_answer(
    answers: Any,
    index: int,
    question: dict[str, Any],
):
    """Accept list-based and dictionary-based frontend answers."""

    if isinstance(answers, list):
        return answers[index] if index < len(answers) else None

    if isinstance(answers, dict):
        possible_keys = [
            str(index),
            index,
            question.get("id"),
            question.get("question"),
        ]

        for key in possible_keys:
            if key is not None and key in answers:
                return answers[key]

    return question.get("selected_answer")


def is_correct_answer(
    selected: Any,
    question: dict[str, Any],
) -> bool:
    """Compare the selected answer with the answer key."""

    if selected is None:
        return False

    correct_index = question.get(
        "answer_index",
        question.get("correct_index"),
    )

    correct_answer = question.get(
        "answer",
        question.get("correct_answer"),
    )

    if correct_index is not None:
        try:
            if isinstance(selected, int):
                return selected == int(correct_index)

            selected_text = str(selected).strip()

            # Accept either the option index or the option text.
            if selected_text.isdigit():
                return int(selected_text) == int(correct_index)

            options = question.get("options", [])

            if isinstance(options, list):
                index = int(correct_index)

                if 0 <= index < len(options):
                    return selected_text.casefold() == str(
                        options[index]
                    ).strip().casefold()

        except (ValueError, TypeError):
            pass

    if correct_answer is not None:
        return str(selected).strip().casefold() == str(
            correct_answer
        ).strip().casefold()

    return False


@app.post("/api/submit-quiz")
def submit_quiz(submission: QuizSubmission):
    questions = submission.questions

    if not questions:
        raise HTTPException(
            status_code=400,
            detail="No quiz questions were submitted.",
        )

    answers = submission.answers
    review = []
    score = 0

    for index, question in enumerate(questions):
        selected = get_selected_answer(answers, index, question)
        correct = is_correct_answer(selected, question)

        if correct:
            score += 1

        options = question.get("options", [])

        correct_index = question.get(
            "answer_index",
            question.get("correct_index"),
        )

        correct_answer = question.get(
            "answer",
            question.get("correct_answer"),
        )

        if correct_answer is None and correct_index is not None:
            try:
                correct_answer = options[int(correct_index)]
            except (IndexError, TypeError, ValueError):
                correct_answer = None

        review.append({
            "question": question.get("question", ""),
            "options": options,
            "selected_answer": selected,
            "correct_answer": correct_answer,
            "is_correct": correct,
            "explanation": question.get("explanation", ""),
        })

    total = len(questions)
    percentage = round((score / total) * 100, 2)

    title = (
        submission.title.strip()
        or submission.topic.strip()
        or "Untitled Quiz"
    )

    created_at = datetime.now(timezone.utc).isoformat()

    result = {
        "id": f"{int(datetime.now(timezone.utc).timestamp() * 1000)}",
        "title": title,
        "topic": title,
        "score": score,
        "total": total,
        "percentage": percentage,
        "percent": percentage,
        "created_at": created_at,
        "auto_submitted": submission.auto_submitted,
    }

    history = read_history()
    history.insert(0, result)

    # Keep the latest 50 real quiz attempts.
    write_history(history[:50])

    return {
        **result,
        "review": review,
        "message": "Quiz result saved successfully.",
    }


# =========================================================
# QUIZ HISTORY
# =========================================================

@app.get("/api/history")
def get_history():
    history = read_history()

    normalised = [
        normalise_history_item(item)
        for item in history
        if isinstance(item, dict)
    ]

    return {
        "history": normalised[:50],
        "total": len(normalised),
    }


@app.delete("/api/history")
def clear_history():
    """Clear saved quiz attempts when explicitly requested."""

    write_history([])

    return {
        "message": "Quiz history cleared successfully.",
        "history": [],
    }