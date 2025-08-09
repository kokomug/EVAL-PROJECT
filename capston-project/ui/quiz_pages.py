import streamlit as st
import ast # For ast.literal_eval in quiz_submissions
from typing import List, Dict, Any # For type hinting

# Assuming services, models, auth, db_utils are accessible
from services.llm_service import generate_content, GROQ_MODELS
from services.quiz_processing_service import (
    generate_quiz_creation_prompt, 
    parse_llm_questions, 
    calculate_quiz_score,
    create_quiz_summary_for_llm,
    generate_quiz_analysis_prompt,
    parse_quiz_analysis
)
from models.question import Question # For type hinting and instantiation if needed
from db_utils import (
    save_quiz_to_db, 
    get_quiz_details_by_id, 
    save_quiz_submission, 
    get_student_quiz_submissions,
    get_quiz_submissions_for_teacher
)
from auth import get_user_id, get_supabase_client

QUIZ_GROQ_MODELS = [
    m for m in GROQ_MODELS if m not in [
        "llama-guard-3-8b",
        "llama3-70b-8192",
        "gemma2-9b-it",
        "qwen-qwq-32b",
        "deepseek-r1-distill-llama-70b"
    ]
]

def render_quiz_page(): # Teacher: Create Quiz
    """Render the quiz generation and question display page."""
    if st.session_state.user_role != "teacher":
        st.error("Only teachers can create quizzes. Please use the dashboard to take available quizzes.")
        if st.button("Back to Dashboard"): # Generic back button
            st.session_state.page = "student_dashboard" if st.session_state.user_role == "student" else "teacher_dashboard"
            st.rerun()
        return
    
    st.title("Quiz Generator") 
    with st.form("quiz_form"):
        st.subheader("Create Your Quiz")
        # PDF upload
        uploaded_pdf = st.file_uploader("Upload a PDF to generate questions from (one-time use, not saved)", type=["pdf"])
        topics = st.text_input("Topics:", placeholder="e.g., Python, Machine Learning, History, Mathematics")
        col1, col2 = st.columns(2)
        with col1:
            num_mcq = st.slider("Number of MCQs:", 0, 15, 3)
            num_fill = st.slider("Number of Fill in the Blanks:", 0, 10, 1)
        with col2:
            num_true_false = st.slider("Number of True/False:", 0, 10, 1)
            num_open_ended = st.slider("Number of Open-ended:", 0, 10, 0)
            difficulty = st.select_slider("Difficulty:", options=["Beginner", "Intermediate", "Advanced"])
            num_options = st.slider("Options per MCQ:", 2, 5, 4)
            total_questions = num_mcq + num_fill + num_true_false + num_open_ended
            st.info(f"Estimated completion time: {total_questions * 1.5:.0f} minutes")
        # LLM model selection dropdown
        llama4_model = "meta-llama/llama-4-maverick-17b-128e-instruct"
        default_index = QUIZ_GROQ_MODELS.index(llama4_model) if llama4_model in QUIZ_GROQ_MODELS else 0
        selected_model = st.selectbox("Choose LLM Model", QUIZ_GROQ_MODELS, index=default_index)
        
        generate_btn = st.form_submit_button("Generate Quiz", use_container_width=True, type="primary")
        if generate_btn and (topics or uploaded_pdf) and total_questions > 0:
            # If PDF is uploaded, extract its text
            pdf_text = None
            if uploaded_pdf is not None:
                try:
                    import PyPDF2
                    pdf_reader = PyPDF2.PdfReader(uploaded_pdf)
                    pdf_text = "\n".join(page.extract_text() or "" for page in pdf_reader.pages)
                except Exception as e:
                    st.error(f"Failed to extract text from PDF: {e}")
                    pdf_text = None
            # Use PDF text if available, else fallback to topics
            if pdf_text and pdf_text.strip():
                prompt = generate_quiz_creation_prompt(
                    pdf_text, num_mcq, num_fill, num_true_false, num_open_ended, difficulty, num_options
                )
            else:
                prompt = generate_quiz_creation_prompt(
                    topics, num_mcq, num_fill, num_true_false, num_open_ended, difficulty, num_options
                )
            response = generate_content(prompt, show_spinner=True, model_name=selected_model)
            if response:
                st.code(response, language='markdown')
                questions_data = parse_llm_questions(response) # This returns List[Question] from quiz_processing_service
                if questions_data:
                    quiz_title = f"Quiz on {topics if not pdf_text else 'Uploaded PDF'} ({difficulty})"
                    quiz_desc = f"Auto-generated quiz on {topics if not pdf_text else 'uploaded PDF'} at {difficulty} level."
                    quiz_id = save_quiz_to_db(quiz_title, quiz_desc, questions_data, topics, difficulty)
                    if quiz_id:
                        st.success("Quiz saved and ready!")
                    else:
                        st.error("Failed to save the quiz to the database.")
                else:
                    st.error("Could not parse any questions from the generated content.")
            else:
                st.error("Failed to generate quiz content. Please check LLM service or API key.")
    
    if st.button("Back to Teacher Dashboard", key="quiz_gen_back_dash"):
        st.session_state.page = "teacher_dashboard"
        st.rerun()

def render_results_page(): # Student: Quiz Results & AI Analysis (after taking quiz, not directly from main.py routing)
    """Render the quiz results page with detailed analysis."""
    st.title("Quiz Results")
    
    questions_for_results = st.session_state.get("current_quiz_questions_for_results")
    user_answers_for_results = st.session_state.get("user_answers_for_results")
    score_for_results = st.session_state.get("score_for_results")
    ai_feedback = st.session_state.get("ai_feedback_for_results")

    if not questions_for_results or user_answers_for_results is None or score_for_results is None:
        st.warning("No quiz results found to display. Please complete a quiz first.")
        if st.button("Back to Dashboard"):
            st.session_state.page = "student_dashboard"
            st.rerun()
        return

    # Initialize manual_grades before using it
    manual_grades = {}
    user_id = get_user_id() if 'get_user_id' in globals() else None
    quiz_id = st.session_state.get('view_quiz_id')
    if user_id and quiz_id:
        submissions = get_student_quiz_submissions(user_id, quiz_id)
        if submissions and submissions[0]:
            mg = submissions[0].get('manual_grades', {})
            if mg is not None:
                manual_grades = mg

    # Get initial score values
    correct, total, score_pct = score_for_results
    
    # Calculate additional points from manual grades
    manual_points = 0
    manual_total = 0
    for q_obj in questions_for_results:
        if q_obj.question_type in ["open_ended", "fill_blank"]:
            grade = manual_grades.get(str(q_obj.db_id))
            if grade is not None:
                try:
                    manual_points += float(grade)
                    manual_total += 1
                except (ValueError, TypeError):
                    pass

    # Update total score with manual grades
    if manual_total > 0:
        correct = correct + manual_points
        total = total + manual_total
        score_pct = (correct / total) * 100 if total > 0 else 0.0
    
    st.subheader(f"Your Score: {correct}/{total} ({score_pct:.1f}%)")
    st.progress(score_pct / 100)
    
    # Feedback messages based on score
    if score_pct >= 90: st.success("🏆 Excellent! You've mastered this topic!")
    elif score_pct >= 75: st.success("👏 Great job! You have a solid understanding.")
    elif score_pct >= 60: st.info("🎯 Good effort! You're on the right track.")
    elif score_pct >= 40: st.warning("📚 Keep studying! You're making progress.")
    else: st.error("💪 This topic needs more attention. Don't give up!")
    
    st.subheader("Detailed Results")
    for i, q_obj in enumerate(questions_for_results):
        user_answer_idx = user_answers_for_results.get(q_obj.db_id, -1)
        if q_obj.question_type in ["open_ended", "fill_blank"]:
            grade = manual_grades.get(str(q_obj.db_id))
            if grade is not None:
                correctness = f"Manual Grade: {grade}"
            else:
                correctness = "Under evaluation"
        else:
            is_correct = user_answer_idx == q_obj.correct_answer
            correctness = "Correct" if is_correct else "Incorrect"
        
        expander_label = f"Q{i+1}: {q_obj.question} - {correctness}"
        with st.expander(expander_label, expanded=False):
            st.markdown(f"**{q_obj.question}**")
            if q_obj.question_type in ["open_ended", "fill_blank"]:
                st.write("Your Answer:")
                st.code(user_answers_for_results.get(q_obj.db_id, "No answer provided"))
                if grade is not None:
                    st.success(f"Manual Grade: {grade}")
                else:
                    st.info("Under evaluation")
            else:
                for j, ans_text in enumerate(q_obj.answers):
                    option_label = f"{chr(65+j)}) {ans_text}"
                    if j == q_obj.correct_answer and j == user_answer_idx:
                        st.success(f"{option_label} (Your correct answer)")
                    elif j == q_obj.correct_answer:
                        st.info(f"{option_label} (Correct answer)")
                    elif j == user_answer_idx:
                        st.error(f"{option_label} (Your incorrect answer)")
                    else:
                        st.write(option_label)
    
    st.subheader("AI Analysis")
    if st.button("Get Detailed Feedback", use_container_width=True, type="primary"):
        # For AI analysis, we need the questions and the user's answers in the format expected by create_quiz_summary_for_llm
        # create_quiz_summary_for_llm expects List[Question] and Dict[int, int] (question index to answer index)
        # We need to map db_id based user_answers_for_results to index-based for the summary function
        indexed_user_answers = {}
        for idx, q_instance in enumerate(questions_for_results):
            if q_instance.db_id in user_answers_for_results:
                indexed_user_answers[idx] = user_answers_for_results[q_instance.db_id]
            else:
                 indexed_user_answers[idx] = -1 # Not answered

        quiz_summary_text = create_quiz_summary_for_llm(questions_for_results, indexed_user_answers)
        evaluation_prompt = generate_quiz_analysis_prompt(quiz_summary_text, correct, total, score_pct)
        ai_evaluation = generate_content(evaluation_prompt, show_spinner=True)
        
        if ai_evaluation:
            analysis_sections = parse_quiz_analysis(ai_evaluation)
            st.subheader("Personalized Quiz Analysis")
            if analysis_sections.get("understanding"): st.markdown("#### Overall Understanding"); st.write(analysis_sections["understanding"])
            if analysis_sections.get("strengths"): st.markdown("#### Your Strengths"); st.success(analysis_sections["strengths"])
            if analysis_sections.get("knowledge_gaps"): st.markdown("#### Areas to Improve"); st.warning(analysis_sections["knowledge_gaps"])
            if analysis_sections.get("recommendations"): st.markdown("#### Recommended Next Steps"); st.info(analysis_sections["recommendations"])
        else:
            st.error("Could not retrieve AI analysis at this time.")
    
    st.markdown("--- ")
    if st.button("Back to Student Dashboard", key="results_back_dash"):
        # Clear results-specific session state
        for key in ["current_quiz_questions_for_results", "user_answers_for_results", "score_for_results", "ai_feedback_for_results"]:
            if key in st.session_state: del st.session_state[key]
        st.session_state.page = "student_dashboard"
        st.rerun()

    # After the detailed results, add a section for manual grades if present
    if 'manual_grades' in st.session_state:
        st.subheader("Manual Grading Results (Open-Ended & Fill-in-the-Blank Questions)")
        for i, q_obj in enumerate(questions_for_results):
            if q_obj.question_type in ["open_ended", "fill_blank"]:
                grade = manual_grades.get(str(q_obj.db_id))
                st.write(f"Q{i+1}: Manual Grade: {grade if grade is not None else 'Not graded yet'}")

    # In the score calculation, add manual grades for both types
    if manual_grades:
        manual_points = 0
        manual_total = 0
        for i, q_obj in enumerate(questions_for_results):
            if q_obj.question_type in ["open_ended", "fill_blank"]:
                manual_total += 1
                grade = manual_grades.get(str(q_obj.db_id))
                try:
                    manual_points += float(grade)
                except Exception:
                    pass
        if manual_total > 0:
            correct += manual_points
            total += manual_total
            score_pct = (correct / total) * 100 if total > 0 else 0.0

def render_take_quiz_page(): # Student: Take Quiz
    """Student view: Take a quiz and submit answers."""
    quiz_id = st.session_state.get("view_quiz_id")
    if not quiz_id:
        st.warning("No quiz selected.")
        if st.button("Back to Dashboard"):
            st.session_state.page = "student_dashboard"
            st.rerun()
        return

    # Fetch full quiz details including questions (which are Question objects from db_utils)
    quiz_details = get_quiz_details_by_id(quiz_id)
    if not quiz_details or not quiz_details.get('questions'):
        st.error("Quiz details or questions not found.")
        if st.button("Back to Dashboard"):
            st.session_state.page = "student_dashboard"
            st.rerun()
        return
    
    st.title(quiz_details['title'])
    st.write(quiz_details.get('description',''))
    st.markdown("--- ")
    
    user_id = get_user_id()
    if not user_id:
        st.error("User ID not found. Please log in.")
        st.session_state.page = "login"
        st.rerun()
        return

    existing_submissions = get_student_quiz_submissions(user_id, quiz_id)
    if existing_submissions:
        st.info("You have already submitted this quiz. Only one submission is allowed.")
        if st.button("Back to Dashboard"):
            st.session_state.page = "student_dashboard"
            st.rerun()
        return
        
    if 'current_quiz_answers' not in st.session_state or st.session_state.get('_current_quiz_id_for_answers') != quiz_id:
        st.session_state.current_quiz_answers = {} # Stores {question_db_id: selected_option_index}
        st.session_state._current_quiz_id_for_answers = quiz_id

    quiz_questions: List[Question] = quiz_details['questions']

    with st.form("take_quiz_form"):
        for q_obj in quiz_questions: # q_obj is a Question dataclass instance
            st.subheader(f"Q{q_obj.id + 1}: {q_obj.question}")
            if q_obj.question_type == "mcq":
                options_texts = [f"{chr(65+j)}) {q_obj.answers[j]}" for j in range(len(q_obj.answers))]
                selected_option_index = st.radio(
                    label=f"Select your answer for Question {q_obj.id + 1}:", 
                    options=range(len(options_texts)),
                    format_func=lambda x: options_texts[x],
                    key=f"take_quiz_q_{q_obj.db_id}"
                )
                st.session_state.current_quiz_answers[q_obj.db_id] = selected_option_index
            elif q_obj.question_type == "true_false":
                tf_options = ["True", "False"]
                selected_option_index = st.radio(
                    label=f"Select True or False for Question {q_obj.id + 1}:",
                    options=range(2),
                    format_func=lambda x: tf_options[x],
                    key=f"take_quiz_q_{q_obj.db_id}"
                )
                st.session_state.current_quiz_answers[q_obj.db_id] = selected_option_index
            elif q_obj.question_type == "fill_blank":
                st.info("Type your answer in lowercase, no spaces, as required for grading accuracy.")
                user_text = st.text_input(
                    label=f"Enter your answer for Question {q_obj.id + 1}:",
                    key=f"take_quiz_q_{q_obj.db_id}"
                )
                st.session_state.current_quiz_answers[q_obj.db_id] = user_text.strip()
            elif q_obj.question_type == "open_ended":
                user_text = st.text_area(
                    label=f"Write your answer for Question {q_obj.id + 1}:",
                    key=f"take_quiz_q_{q_obj.db_id}"
                )
                st.session_state.current_quiz_answers[q_obj.db_id] = user_text.strip()
        
        submit_button = st.form_submit_button("Submit Quiz", use_container_width=True, type="primary")
        
        if submit_button:
            # Calculate score before saving
            correct_count = 0
            for q_obj in quiz_questions:
                if st.session_state.current_quiz_answers.get(q_obj.db_id) == q_obj.correct_answer:
                    correct_count += 1
            score_percentage = (correct_count / len(quiz_questions)) * 100 if quiz_questions else 0.0
            
            # Generate AI feedback using LLM
            from services.quiz_processing_service import create_quiz_summary_for_llm, generate_quiz_analysis_prompt, parse_quiz_analysis
            from services.llm_service import generate_content
            quiz_summary = create_quiz_summary_for_llm(quiz_questions, st.session_state.current_quiz_answers)
            ai_prompt = generate_quiz_analysis_prompt(quiz_summary, correct_count, len(quiz_questions), score_percentage)
            ai_feedback_raw = generate_content(ai_prompt, show_spinner=True)
            ai_feedback = parse_quiz_analysis(ai_feedback_raw) if ai_feedback_raw else {}
            
            # Save feedback as a string (raw or parsed)
            import json
            feedback_to_save = json.dumps(ai_feedback) if ai_feedback else None
            
            # answers_to_save is st.session_state.current_quiz_answers (already {q_db_id: ans_idx})
            save_successful = save_quiz_submission(quiz_id, user_id, st.session_state.current_quiz_answers, score_percentage, feedback=feedback_to_save)
            
            if save_successful:
                st.session_state.quiz_submitted_successfully = True
                # Store info needed for the results page
                st.session_state.current_quiz_questions_for_results = quiz_questions
                st.session_state.user_answers_for_results = st.session_state.current_quiz_answers.copy()
                st.session_state.score_for_results = (correct_count, len(quiz_questions), score_percentage)
                st.session_state.ai_feedback_for_results = ai_feedback
                
                # Clear quiz-taking specific state before going to results
                del st.session_state['current_quiz_answers']
                del st.session_state['_current_quiz_id_for_answers']
                st.session_state.page = "results" # Navigate to results page
                st.rerun()
            else:
                st.error("There was an issue submitting your quiz. Please try again.")

    # This part is for displaying the success message if quiz_submitted_successfully was set by a previous rerun
    # However, navigation to results page is now direct, so this might not be hit unless that fails.
    if st.session_state.get("quiz_submitted_successfully") and st.session_state.page != "results":
        st.success("Quiz submitted successfully! Preparing your results...") 
        # Logic to go to dashboard if results navigation failed for some reason
        if st.button("Back to Dashboard", key="take_quiz_back_after_submit_fail_nav"):
            st.session_state.page = "student_dashboard"
            st.session_state.pop('quiz_submitted_successfully', None)
            st.rerun()

def render_quiz_submissions_page(): # Teacher: View Submissions for a Quiz
    """Teacher view: See all student submissions for a quiz."""
    quiz_id = st.session_state.get("view_quiz_id")
    teacher_id = get_user_id()

    # Add this line to define is_teacher
    is_teacher = st.session_state.get("user_role") == "teacher"

    if not teacher_id:
        st.error("Teacher ID not found. Please log in.")
        st.session_state.page = "login"
        st.rerun()
        return

    if not quiz_id:
        st.warning("No quiz selected to view submissions.")
        if st.button("Back to Teacher Dashboard"):
            st.session_state.page = "teacher_dashboard"
            st.rerun()
        return
        
    quiz_details = get_quiz_details_by_id(quiz_id)
    if not quiz_details or not quiz_details.get('questions'):
        st.error("Quiz details or original questions not found. Cannot display submissions accurately.")
        if st.button("Back to Teacher Dashboard"):
            st.session_state.page = "teacher_dashboard"
            st.rerun()
        return

    st.title(f"Submissions for: {quiz_details['title']}")
    st.markdown("--- ")
    
    submissions = get_quiz_submissions_for_teacher(teacher_id, quiz_id)
    if not submissions:
        st.info("No student submissions yet for this quiz.")
    else:
        student_emails_map = {} # Fetch student emails if needed, or just use IDs
        # Example: student_emails_map = {sub['student_id']: get_user_email_by_id(sub['student_id']) for sub in submissions}
        # For now, use student_id directly.

        student_options = {sub['student_id']: f"Student ID: {sub['student_id']} (Score: {sub.get('score', 'N/A'):.1f}%) Submitted: {sub.get('created_at', '')[:16]}" for sub in submissions}
        
        selected_student_id = st.selectbox(
            "Select a student to view their submission:", 
            options=[""] + list(student_options.keys()), 
            format_func=lambda x: student_options.get(x, "Select...")
        )

        if selected_student_id:
            submission_details = next((s for s in submissions if s['student_id'] == selected_student_id), None)
            if not submission_details:
                st.error("Selected submission not found.")
                return

            student_answers_str = submission_details.get('answers', '{}')
            student_answers_dict = {}
            try:
                if isinstance(student_answers_str, dict):
                    student_answers_dict = student_answers_str
                else:
                    # Try ast.literal_eval, fallback to showing raw string if fails
                    student_answers_dict = ast.literal_eval(student_answers_str)
                    if not isinstance(student_answers_dict, dict):
                        student_answers_dict = {}
            except Exception as e:
                st.warning(f"Could not parse answers for this submission: {student_answers_str}")
                student_answers_dict = {}
                
            st.markdown("--- ")
            st.subheader(f"Submission Details for Student ID: {selected_student_id}")
            st.write(f"**Score:** {submission_details.get('score', 'N/A'):.1f}% | **Submitted at:** {submission_details.get('created_at', '')[:19]}")
            st.markdown("--- ")
            
            st.subheader("Answers Given:")
            quiz_questions: List[Question] = quiz_details['questions']
            manual_grades = submission_details.get('manual_grades', {})
            if manual_grades is None:
                manual_grades = {}
            manual_grades_changed = False
            for i, q_obj in enumerate(quiz_questions):
                st.markdown(f"**Q{i+1}: {q_obj.question}**")
                student_ans = student_answers_dict.get(str(q_obj.db_id), None)
                if q_obj.question_type == "mcq":
                    # MCQ logic unchanged
                    correct_idx = q_obj.correct_answer if hasattr(q_obj, 'correct_answer') else None
                    student_ans_idx = None
                    try:
                        student_ans_idx = int(student_ans) if student_ans is not None else None
                    except Exception:
                        pass
                    for j, opt_text in enumerate(q_obj.answers):
                        display_text = f"{chr(65+j)}) {opt_text}"
                        if j == correct_idx and j == student_ans_idx:
                            st.success(f"{display_text} (Correct & Student's Answer)")
                        elif j == student_ans_idx:
                            st.error(f"{display_text} (Student's Answer - Incorrect)")
                        elif j == correct_idx:
                            st.info(f"{display_text} (Correct Answer)")
                        else:
                            st.write(display_text)
                elif q_obj.question_type == "true_false":
                    # Show as True/False, not MCQ
                    tf_options = ["True", "False"]
                    correct_idx = q_obj.correct_answer if hasattr(q_obj, 'correct_answer') else None
                    student_ans_idx = None
                    try:
                        student_ans_idx = int(student_ans) if student_ans is not None else None
                    except Exception:
                        pass
                    for j, opt_text in enumerate(tf_options):
                        display_text = f"{opt_text}"
                        if j == correct_idx and j == student_ans_idx:
                            st.success(f"{display_text} (Correct & Student's Answer)")
                        elif j == student_ans_idx:
                            st.error(f"{display_text} (Student's Answer - Incorrect)")
                        elif j == correct_idx:
                            st.info(f"{display_text} (Correct Answer)")
                        else:
                            st.write(display_text)
                elif q_obj.question_type == "fill_blank":
                    st.write(f"Student Answer: {student_ans if student_ans is not None else 'No answer submitted.'}")
                    if q_obj.answers:
                        st.info(f"Correct Answer: {q_obj.answers[0]}")
                    # Manual grade for both fill-in-the-blank and open-ended
                    if is_teacher:
                        current_grade = manual_grades.get(str(q_obj.db_id), "Under evaluation")
                        new_grade = st.number_input(f"Manual Grade for Q{i+1} (0-1)", min_value=0.0, max_value=1.0, value=float(current_grade) if isinstance(current_grade, (int, float)) else 0.0, step=0.1, key=f"manual_grade_{selected_student_id}_{q_obj.db_id}")
                        if new_grade != current_grade:
                            manual_grades[str(q_obj.db_id)] = new_grade
                            manual_grades_changed = True
                        st.write(f"Current Manual Grade: {manual_grades.get(str(q_obj.db_id), 'Not graded')}")
                    else:
                        if str(q_obj.db_id) in manual_grades:
                            st.success(f"Manual Grade: {manual_grades[str(q_obj.db_id)]}")
                        else:
                            st.info("Not graded yet.")
                elif q_obj.question_type == "open_ended":
                    st.markdown("**Student's Answer:**")
                    st.code(student_ans if student_ans is not None else 'No answer submitted.', language=None)
                    # Manual grade for both fill-in-the-blank and open-ended
                    if is_teacher:
                        current_grade = manual_grades.get(str(q_obj.db_id), "Under evaluation")
                        new_grade = st.number_input(f"Manual Grade for Q{i+1} (0-1)", min_value=0.0, max_value=1.0, value=float(current_grade) if isinstance(current_grade, (int, float)) else 0.0, step=0.1, key=f"manual_grade_{selected_student_id}_{q_obj.db_id}")
                        if new_grade != current_grade:
                            manual_grades[str(q_obj.db_id)] = new_grade
                            manual_grades_changed = True
                        st.write(f"Current Manual Grade: {manual_grades.get(str(q_obj.db_id), 'Not graded')}")
                    else:
                        if str(q_obj.db_id) in manual_grades:
                            st.success(f"Manual Grade: {manual_grades[str(q_obj.db_id)]}")
                        else:
                            st.info("Not graded yet.")
                st.markdown("---")
            if manual_grades_changed and st.button("Save Manual Grades", key=f"save_manual_grades_{selected_student_id}"):
                client = get_supabase_client()
                if client:
                    client.table("quiz_results").update({"manual_grades": manual_grades}).eq("quiz_id", quiz_id).eq("student_id", selected_student_id).execute()
                    st.session_state.manual_grades = manual_grades  # <-- Store in session state
                    st.success("Manual grades saved!")

    if st.button("Back to Teacher Dashboard", key="quiz_sub_back_to_dash"):
        st.session_state.page = "teacher_dashboard"
        st.session_state.pop('view_quiz_id', None)
        st.rerun() 