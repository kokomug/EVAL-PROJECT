import streamlit as st
import re
# from dataclasses import dataclass # Question is now imported
from typing import List, Dict, Tuple, Optional
from models.question import Question # Updated import

# Define simple Question class (can be shared or defined per module if variations exist)
# @dataclass # Removed as it's imported
# class Question:
#     id: int
#     question: str
#     answers: List[str] # List of answer strings
#     correct_answer: int # Index of the correct answer in the answers list
#     # Supabase specific fields (optional, can be added when fetching/saving)
#     db_id: Optional[str] = None # To store UUID from Supabase quiz_questions table
#     quiz_db_id: Optional[str] = None # To store UUID of parent quiz from Supabase quizzes table

# Parse questions from LLM response (this version is for LLM-generated quizzes not yet in DB)
def parse_llm_questions(response: str) -> List[Question]:
    """Parse the LLM response into Question objects for a new quiz, supporting MCQ, Fill in the Blanks, True/False, and Open-ended."""
    if not response:
        return []
    
    questions = []
    lines = response.replace('\r\n', '\n').split('\n')
    
    # Patterns for each type
    type_pattern = re.compile(r'^(MCQ|FILL|TF|OPEN)\s*(\d+)[:\.\)]\s*(.+)', re.IGNORECASE)
    answer_pattern = re.compile(r'^([A-Z])[:\.\)]\s*(.+)', re.IGNORECASE)
    fill_answer_pattern = re.compile(r'^Answer:\s*(.+)', re.IGNORECASE)
    
    current_type = None
    current_question_text = None
    current_answers = []
    correct_answer_index = -1
    question_id_counter = 1
    tf_correct = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        type_match = type_pattern.match(line)
        answer_match = answer_pattern.match(line)
        fill_answer_match = fill_answer_pattern.match(line)
        
        if type_match:
            # Save previous question if exists
            if current_question_text:
                if current_type == 'MCQ':
                    if correct_answer_index == -1 and current_answers:
                        correct_answer_index = 0
                    questions.append(Question(
                        id=question_id_counter,
                        question=current_question_text,
                        answers=current_answers,
                        correct_answer=correct_answer_index,
                        question_type='mcq'
                    ))
                elif current_type == 'FILL':
                    # Only one answer, correct_answer is always 0
                    if current_answers:
                        # Enforce at most two words
                        ans = current_answers[0].strip()
                        ans = ' '.join(ans.split()[:2])
                        current_answers = [ans]
                    questions.append(Question(
                        id=question_id_counter,
                        question=current_question_text,
                        answers=current_answers,
                        correct_answer=0,
                        question_type='fill_blank'
                    ))
                elif current_type == 'TF':
                    # Always two options: True/False
                    questions.append(Question(
                        id=question_id_counter,
                        question=current_question_text,
                        answers=["True", "False"],
                        correct_answer=tf_correct if tf_correct is not None else 0,
                        question_type='true_false'
                    ))
                elif current_type == 'OPEN':
                    questions.append(Question(
                        id=question_id_counter,
                        question=current_question_text,
                        answers=[],
                        correct_answer=-1,
                        question_type='open_ended'
                    ))
                question_id_counter += 1
            # Start new question
            current_type = type_match.group(1).upper()
            current_question_text = type_match.group(3).strip()
            current_answers = []
            correct_answer_index = -1
            tf_correct = None
        elif answer_match and current_type == 'MCQ':
            text = answer_match.group(2).strip()
            if "**" in text:
                text = text.replace("**", "").strip()
                correct_answer_index = len(current_answers)
            current_answers.append(text)
        elif answer_match and current_type == 'TF':
            text = answer_match.group(2).strip()
            if text.replace("**", "").strip().lower() == "true":
                idx = 0
            else:
                idx = 1
            if "**" in text:
                tf_correct = idx
        elif fill_answer_match and current_type == 'FILL':
            # Only take at most two words
            ans = fill_answer_match.group(1).strip()
            ans = ' '.join(ans.split()[:2])
            current_answers = [ans]
    # Save the last question
    if current_question_text:
        if current_type == 'MCQ':
            if correct_answer_index == -1 and current_answers:
                correct_answer_index = 0
            questions.append(Question(
                id=question_id_counter,
                question=current_question_text,
                answers=current_answers,
                correct_answer=correct_answer_index,
                question_type='mcq'
            ))
        elif current_type == 'FILL':
            if current_answers:
                ans = current_answers[0].strip()
                ans = ' '.join(ans.split()[:2])
                current_answers = [ans]
            questions.append(Question(
                id=question_id_counter,
                question=current_question_text,
                answers=current_answers,
                correct_answer=0,
                question_type='fill_blank'
            ))
        elif current_type == 'TF':
            questions.append(Question(
                id=question_id_counter,
                question=current_question_text,
                answers=["True", "False"],
                correct_answer=tf_correct if tf_correct is not None else 0,
                question_type='true_false'
            ))
        elif current_type == 'OPEN':
            questions.append(Question(
                id=question_id_counter,
                question=current_question_text,
                answers=[],
                correct_answer=-1,
                question_type='open_ended'
            ))
    return questions

def calculate_quiz_score(questions: List[Question], user_answers: Dict[int, int]) -> tuple:
    """Calculate the quiz score from Question objects and user's answers (by index or string)."""
    if not questions:
        return 0, 0, 0.0
    correct_count = 0
    total_auto_graded = 0
    for i, q in enumerate(questions):
        user_answer = user_answers.get(i, user_answers.get(q.db_id, None))
        if q.question_type in ["mcq", "true_false"]:
            total_auto_graded += 1
            if isinstance(user_answer, int) and user_answer == q.correct_answer:
                correct_count += 1
        elif q.question_type == "fill_blank":
            total_auto_graded += 1
            if isinstance(user_answer, str) and q.answers and len(q.answers) > 0:
                # Compare after stripping, lowering, removing spaces, and basic singular/plural normalization
                def normalize(s):
                    s = s.strip().lower().replace(' ', '')
                    if s.endswith('s') and len(s) > 1:
                        s = s[:-1]
                    return s
                if normalize(user_answer) == normalize(q.answers[0]):
                    correct_count += 1
        # open_ended: skip from auto-grading
    score_percentage = (correct_count / total_auto_graded) * 100 if total_auto_graded > 0 else 0.0
    return correct_count, total_auto_graded, score_percentage

# This prompt is for LLM to generate quiz content
def generate_quiz_creation_prompt(
    topics: str,
    num_mcq: int,
    num_fill: int,
    num_true_false: int,
    num_open_ended: int,
    difficulty: str,
    num_options: int
) -> str:
    """
    Build a few-shot prompt that:
      - MCQs: mark correct option with **…**
      - TF: always as MCQ with two options: 'A) True', 'B) False', mark correct
      - Fill: use ____ and provide the correct answer after the question as 'Answer: ...' (single word or at most two words)
      - Open: leave unanswered
    """
    prompt = (
        "You are an expert instructional designer creating assessments for college-level students.\n"
        f"Topic(s): **{topics}**\n"
        f"Difficulty: **{difficulty.capitalize()}**\n\n"
        "Generate exactly:\n"
        f"- {num_mcq} multiple-choice question(s) with {num_options} options each.\n"
        f"- {num_fill} fill-in-the-blank question(s) (user will type answer; answer must be a single word or at most two words).\n"
        f"- {num_true_false} true/false question(s) (always as MCQ with two options: 'A) True', 'B) False').\n"
        f"- {num_open_ended} open-ended question(s) (no answers).\n\n"
        "### Formatting rules\n"
        "1. Label each: `MCQ 1.`, `FILL 1.`, `TF 1.`, `OPEN 1.`\n"
        "2. MCQs: list options A)–D), mark correct with **…**.\n"
        "3. TF: always as MCQ with two options: 'A) True', 'B) False', mark the correct one with **…**.\n"
        "4. FILL: use `____` in the stem; provide the correct answer after the question as 'Answer: ...' (single word or at most two words).\n"
        "5. OPEN: write the question only, no answers or options.\n\n"
        "### One-Shot Example\n\n"
        "MCQ 1. Which gas do plants absorb during photosynthesis?\n"
        "A) Oxygen\n"
        "B) **Carbon Dioxide**\n"
        "C) Nitrogen\n"
        "D) Hydrogen\n\n"
        "FILL 1. The powerhouse of the cell is _____.\n"
        "Answer: mitochondria\n\n"
        "TF 1. Water boils at 100°C at sea level.\n"
        "A) **True**\n"
        "B) False\n\n"
        "OPEN 1. Explain how natural selection drives evolution over time.\n\n"
        "----\n"
        "**Now, create the quiz:**\n"
    )
    return prompt



# This prompt is for LLM to analyze a completed quiz
def generate_quiz_analysis_prompt(quiz_summary: str, correct: int, total: int, score_pct: float) -> str:
    """Generate the prompt for LLM quiz performance analysis."""
    return f"""Based on the following quiz performance, provide a comprehensive analysis.

{quiz_summary}

The user scored {correct}/{total} ({score_pct:.1f}%).

Please provide:
1. An overall assessment of the user's understanding of the subject matter.
2. Identification of specific knowledge gaps or common misconceptions observed.
3. Specific, actionable recommendations for further study or areas to focus on.
4. Positive reinforcement and highlight areas where the user demonstrated good understanding.

Format your response clearly using the following tags:
<understanding>
[Your assessment of overall understanding here]
</understanding>

<knowledge_gaps>
[Your identification of specific knowledge gaps or misconceptions here]
</knowledge_gaps>

<recommendations>
[Your specific recommendations for improvement here]
</recommendations>

<strengths>
[Areas where the user demonstrated good understanding or strengths]
</strengths>
"""

def parse_quiz_analysis(evaluation: str) -> Dict[str, str]:
    """Parse the LLM response for quiz analysis into sections."""
    if not evaluation:
        return {}
        
    sections = {
        "understanding": r'<understanding>(.*?)</understanding>',
        "knowledge_gaps": r'<knowledge_gaps>(.*?)</knowledge_gaps>',
        "recommendations": r'<recommendations>(.*?)</recommendations>',
        "strengths": r'<strengths>(.*?)</strengths>'
    }
    
    result = {}
    for key, pattern in sections.items():
        match = re.search(pattern, evaluation, re.DOTALL | re.IGNORECASE)
        result[key] = match.group(1).strip() if match else "Analysis not found or format error."
    
    return result

def create_quiz_summary_for_llm(questions: List[Question], user_answers: Dict[int, int]) -> str:
    """Create a text summary of the quiz questions, options, user's answers, and correct answers for LLM analysis."""
    quiz_summary = "QUIZ QUESTIONS, ANSWERS, AND USER PERFORMANCE:\n\n"
    for i, q in enumerate(questions):
        user_selected_option_index = user_answers.get(i, user_answers.get(q.db_id, -1))
        user_answer_text = "Not answered"
        # For MCQ/TF: index, for fill/open: string
        if q.question_type in ["mcq", "true_false"]:
            if q.answers and isinstance(user_selected_option_index, int) and 0 <= user_selected_option_index < len(q.answers):
                user_answer_text = q.answers[user_selected_option_index]
            user_choice_label = chr(65 + user_selected_option_index) if isinstance(user_selected_option_index, int) and user_selected_option_index != -1 and q.answers and 0 <= user_selected_option_index < len(q.answers) else "N/A"
        else:
            if isinstance(user_selected_option_index, str) and user_selected_option_index.strip():
                user_answer_text = user_selected_option_index
            user_choice_label = "N/A"
        if q.answers and 0 <= q.correct_answer < len(q.answers):
            correct_answer_text = q.answers[q.correct_answer]
            correct_choice_label = chr(65 + q.correct_answer)
        elif q.question_type == "fill_blank" and q.answers:
            correct_answer_text = q.answers[0]
            correct_choice_label = "(text)"
        elif q.question_type == "open_ended":
            correct_answer_text = "Under evaluation"
            correct_choice_label = "N/A"
        else:
            correct_answer_text = "(No correct answer)"
            correct_choice_label = "N/A"
        quiz_summary += f"Question {i+1}: {q.question}\n"
        for j, ans_text in enumerate(q.answers):
            option_label = chr(65+j)
            quiz_summary += f"  {option_label}) {ans_text}\n"
        quiz_summary += f"  User's answer: {user_choice_label}) {user_answer_text}\n"
        quiz_summary += f"  Correct answer: {correct_choice_label}) {correct_answer_text}\n\n"
    return quiz_summary 