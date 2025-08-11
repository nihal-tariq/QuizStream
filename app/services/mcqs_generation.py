import os, re, uuid, json, logging

from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from app.models.mcqs import MCQ
from google import genai

logger = logging.getLogger(__name__)

load_dotenv()

# Initialize Gemini client
api_key = os.getenv("GEMINI_FLASH_KEY")
if not api_key:
    raise ValueError("GEMINI_FLASH_KEY is not set in environment variables.")
client = genai.Client(api_key=api_key)


def extract_json_from_text(text: str) -> str:
    """
    Extract valid JSON from Gemini output, stripping markdown fences or extra text.
    Ensures we return only the JSON array.
    """
    if not text:
        return text

    text = text.strip()

    # Remove markdown JSON fences if present
    if text.startswith("```"):
        text = re.sub(r"^```(json)?", "", text, flags=re.IGNORECASE).strip()
        if text.endswith("```"):
            text = text[:-3].strip()

    # If there's a JSON array inside the text, extract it
    if "[" in text and "]" in text:
        start = text.index("[")
        end = text.rindex("]") + 1
        return text[start:end]

    return text


def generate_and_store_mcqs(transcript: str, video_title: str, db: Session):
    """
    Generate MCQs and True/False questions from transcript using Gemini 2.5 Flash
    and store them in the MCQ table with video_title.
    """
    if not transcript or not transcript.strip():
        raise ValueError("Transcript is empty. Cannot generate MCQs.")

    prompt = f"""
    You are an expert educational assessment creator. 
    You will be given a learning content text (such as a lecture, discussion, or training material).
    Read it carefully and generate high-quality quiz questions that thoroughly assess the learner's understanding.

    Instructions:
    1. Analyze the provided learning material to identify its main concepts, supporting facts, examples, and reasoning patterns.
    2. Consider the learning objectives implied or stated, and ensure your questions collectively cover all key ideas.
    3. Create questions that are logical, unambiguous, and self-contained (make sense without referencing the original material).
    4. Ensure variety in cognitive level:
       - Include easy, moderate, and challenging questions.
       - Test recall, application, and analysis.
    5. For Multiple Choice Questions (MCQs):
       - Create exactly 5 MCQs.
       - Each MCQ must have 4 clear and distinct options.
       - Only one correct answer per MCQ.
       - Distractors should be plausible but incorrect.
    6. For True/False questions:
       - Create exactly 5 statements.
       - Statements must be complete and understandable without saying “according to the transcript”.
       - Ensure a balanced mix of True and False answers.
    7. Avoid copying sentences verbatim unless necessary for accuracy.
    8. Do NOT mention the words “transcript” or “document” in the final questions.

    Output Format:
    Return ONLY valid JSON in the following array format (no explanations, no markdown):
    [
        {{
            "question": "...",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "answer": "Correct Option Text",
            "type": "mcq"
        }},
        {{
            "question": "...",
            "answer": "True",
            "type": "true_false"
        }}
    ]

    Learning material:
    {transcript}
    """

    logger.info("Calling Gemini API for MCQ generation...")
    try:
        response = client.models.generate_content(
            model="models/gemini-2.5-flash",
            contents=prompt
        )
    except Exception as e:
        logger.exception("Gemini API call failed")
        raise RuntimeError(f"Gemini API call failed: {e}")

    # Get raw response text
    try:
        raw_text = getattr(response, "text", None) or getattr(response, "output_text", None) or str(response)
        logger.debug(f"Raw Gemini output (first 500 chars): {raw_text[:500]}")

        clean_text = extract_json_from_text(raw_text)
        mcqs_data = json.loads(clean_text)

        if not isinstance(mcqs_data, list):
            raise ValueError("Parsed JSON is not a list.")
    except Exception as e:
        logger.error(f"Invalid JSON from Gemini: {e}")
        raise ValueError(f"Gemini response is not valid JSON: {e}")

    # Store MCQs in database
    logger.info(f"Storing {len(mcqs_data)} MCQs in database...")
    try:
        for item in mcqs_data:
            mcq_entry = MCQ(
                id=uuid.uuid4(),
                video_title=video_title,
                question=item.get("question"),
                options=item.get("options") if item.get("type") == "mcq" else None,
                answer=item.get("answer"),
                created_at=datetime.utcnow()
            )
            db.add(mcq_entry)

        db.commit()
        logger.info(f"✅ Stored {len(mcqs_data)} MCQs for '{video_title}'")

    except Exception as e:
        db.rollback()
        logger.exception("Database insert failed for MCQs")
        raise RuntimeError(f"Failed to store MCQs: {e}")

    return {"message": f"{len(mcqs_data)} questions stored successfully"}
