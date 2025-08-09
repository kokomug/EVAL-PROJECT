from dataclasses import dataclass
from typing import List

@dataclass
class Question:
    id: int
    question: str
    answers: List[str]
    correct_answer: int
    question_type: str = "mcq"  # New field: 'mcq', 'fill_blank', 'true_false', 'open_ended'
    db_id: int = 0 # Added to match usage in render_take_quiz_page and other places 