import streamlit as st
from typing import List, Dict, Any, Optional
from auth import get_supabase_client, get_user_id
# from quiz_utils import Question # Old import
from models.question import Question # New import
# from assignment_utils import ... # If specific assignment dataclass needed
import uuid # For generating IDs if not handled by Supabase default

# --- QUIZ DATABASE FUNCTIONS ---

def save_quiz_to_db(title: str, description: str, questions: List[Question], topics: str = "", difficulty: str = "") -> Optional[str]:
    """Saves a new quiz and its questions to the database.
       Returns the quiz_id if successful, else None."""
    client = get_supabase_client()
    user_id = get_user_id()
    if not client or not user_id:
        st.error("User not logged in or Supabase client error.")
        return None
    try:
        quiz_data = {
            "title": title,
            "description": description,
            "topics": topics,
            "difficulty": difficulty,
            "teacher_id": user_id,
            "questions": [
                {
                    "question": q_obj.question,
                    "answers": q_obj.answers,
                    "correct_answer": q_obj.correct_answer,
                    "question_type": getattr(q_obj, "question_type", "mcq")
                } for q_obj in questions
            ]
        }
        quiz_response = client.table("quizzes").insert(quiz_data).execute()
        if quiz_response.data and len(quiz_response.data) > 0:
            quiz_db_id = quiz_response.data[0]["id"]
            st.success(f"Quiz '{title}' saved successfully!")
            return quiz_db_id
        else:
            st.error(f"Failed to save quiz '{title}'. Error: {quiz_response.error}")
            return None
    except Exception as e:
        st.error(f"An error occurred while saving the quiz: {str(e)}")
        return None

def get_quizzes_for_student() -> List[Dict[str, Any]]:
    """Fetches all available quizzes for a student."""
    client = get_supabase_client()
    if not client:
        return []
    try:
        response = client.table("quizzes").select("id, title, description, topics, difficulty, created_at, teacher_id").order("created_at", desc=True).execute()
        if response.data:
            return response.data
        return []
    except Exception as e:
        st.error(f"Error fetching quizzes: {e}")
        return []

def get_quiz_details_by_id(quiz_id: str) -> Optional[Dict[str, Any]]:
    """Fetches a specific quiz by quiz_id."""
    client = get_supabase_client()
    if not client:
        return None
    try:
        quiz_response = client.table("quizzes").select("*").eq("id", quiz_id).single().execute()
        if quiz_response.data:
            quiz_data = quiz_response.data
            # Parse questions from JSONB field
            questions = []
            for i, q in enumerate(quiz_data.get("questions", [])):
                questions.append(Question(
                    id=i,
                    question=q["question"],
                    answers=q["answers"],
                    correct_answer=q["correct_answer"],
                    question_type=q.get("question_type", "mcq"),
                    db_id=str(i)
                ))
            quiz_data['questions'] = questions
            return quiz_data
        return None
    except Exception as e:
        st.error(f"Error fetching quiz details: {e}")
        return None

def save_quiz_submission(quiz_id: str, student_id: str, answers: Dict[str, Any], score: float, feedback: Optional[str] = None) -> bool:
    """Saves a student's quiz submission, including optional AI feedback."""
    client = get_supabase_client()
    if not client:
        return False
    try:
        submission_data = {
            "quiz_id": quiz_id,
            "student_id": student_id,
            "answers": answers,
            "score": score
        }
        if feedback is not None:
            submission_data["feedback"] = feedback
        response = client.table("quiz_results").insert(submission_data).execute()
        if response.data:
            st.success("Quiz submission saved!")
            return True
        st.error(f"Failed to save quiz submission: {response.error}")
        return False
    except Exception as e:
        st.error(f"Error saving quiz submission: {e}")
        return False

def get_student_quiz_submissions(student_id: str, quiz_id: Optional[str] = None) -> List[Dict[str, Any]]:
    client = get_supabase_client()
    if not client: return []
    try:
        query = client.table("quiz_results").select("*").eq("student_id", student_id).order("created_at", desc=True)
        if quiz_id:
            query = query.eq("quiz_id", quiz_id)
        response = query.execute()
        return response.data if response.data else []
    except Exception as e:
        st.error(f"Error fetching student quiz submissions: {e}")
        return []

def get_quiz_submissions_for_teacher(teacher_id: str, quiz_id: Optional[str] = None) -> List[Dict[str, Any]]:
    client = get_supabase_client()
    if not client: return []
    try:
        # Get all quizzes for this teacher
        quizzes_resp = client.table("quizzes").select("id").eq("teacher_id", teacher_id).execute()
        quiz_ids = [q['id'] for q in quizzes_resp.data] if quizzes_resp.data else []
        if not quiz_ids:
            return []
        query = client.table("quiz_results").select("*").in_("quiz_id", quiz_ids).order("created_at", desc=True)
        if quiz_id:
            query = query.eq("quiz_id", quiz_id)
        response = query.execute()
        return response.data if response.data else []
    except Exception as e:
        st.error(f"Error fetching quiz submissions for teacher: {e}")
        return []

# --- ASSIGNMENT DATABASE FUNCTIONS ---

def save_assignment_to_db(assignment_data: Dict[str, Any]) -> Optional[str]:
    """Saves a new coding assignment to the database.
       assignment_data should include title, description, requirements, etc.
       Returns the assignment_id if successful, else None."""
    client = get_supabase_client()
    user_id = get_user_id()
    if not client or not user_id:
        st.error("User not logged in or Supabase client error.")
        return None
    try:
        assignment_data["teacher_id"] = user_id
        response = client.table("coding_assignments").insert(assignment_data).execute()
        if response.data and len(response.data) > 0:
            assignment_db_id = response.data[0]["id"]
            st.success(f"Assignment '{assignment_data.get('title')}' saved successfully!")
            return assignment_db_id
        else:
            st.error(f"Failed to save assignment. Error: {response.error}")
            return None
    except Exception as e:
        st.error(f"An error occurred while saving the assignment: {str(e)}")
        return None

def get_assignments_for_student() -> List[Dict[str, Any]]:
    """Fetches all available assignments for a student."""
    client = get_supabase_client()
    if not client:
        return []
    try:
        response = client.table("coding_assignments").select("id, title, description, topic, difficulty, time_limit, created_at, teacher_id").order("created_at", desc=True).execute()
        return response.data if response.data else []
    except Exception as e:
        st.error(f"Error fetching assignments: {e}")
        return []

def get_assignment_details_by_id(assignment_id: str) -> Optional[Dict[str, Any]]:
    """Fetches a specific assignment by assignment_id."""
    client = get_supabase_client()
    if not client:
        return None
    try:
        response = client.table("coding_assignments").select("*").eq("id", assignment_id).single().execute()
        return response.data if response.data else None
    except Exception as e:
        st.error(f"Error fetching assignment details: {e}")
        return None

def save_assignment_submission(assignment_id: str, student_id: str, submitted_code: str, evaluation_feedback: Optional[str] = None, score: Optional[float] = None) -> bool:
    """Saves a student's assignment submission."""
    client = get_supabase_client()
    if not client:
        return False
    try:
        submission_data = {
            "assignment_id": assignment_id,
            "student_id": student_id,
            "code": submitted_code,
            "evaluation": evaluation_feedback,
        }
        response = client.table("assignment_submissions").insert(submission_data).execute()
        if response.data:
            st.success("Assignment submission saved!")
            return True
        st.error(f"Failed to save assignment submission: {response.error}")
        return False
    except Exception as e:
        st.error(f"Error saving assignment submission: {e}")
        return False

def get_student_assignment_submissions(student_id: str, assignment_id: Optional[str] = None) -> List[Dict[str, Any]]:
    client = get_supabase_client()
    if not client: return []
    try:
        query = client.table("assignment_submissions").select("*").eq("student_id", student_id).order("created_at", desc=True)
        if assignment_id:
            query = query.eq("assignment_id", assignment_id)
        response = query.execute()
        return response.data if response.data else []
    except Exception as e:
        st.error(f"Error fetching student assignment submissions: {e}")
        return []

def get_assignment_submissions_for_teacher(teacher_id: str, assignment_id: Optional[str] = None) -> List[Dict[str, Any]]:
    client = get_supabase_client()
    if not client: return []
    try:
        # Get all assignments for this teacher
        assignments_resp = client.table("coding_assignments").select("id").eq("teacher_id", teacher_id).execute()
        assignment_ids = [a['id'] for a in assignments_resp.data] if assignments_resp.data else []
        if not assignment_ids:
            return []
        query = client.table("assignment_submissions").select("*").in_("assignment_id", assignment_ids).order("created_at", desc=True)
        if assignment_id:
            query = query.eq("assignment_id", assignment_id)
        response = query.execute()
        return response.data if response.data else []
    except Exception as e:
        st.error(f"Error fetching assignment submissions for teacher: {e}")
        return [] 