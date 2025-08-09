import streamlit as st
# Assuming auth.py, db_utils.py are in the parent directory or accessible via PYTHONPATH
from auth import get_user_id, signout_user 
from db_utils import get_quizzes_for_student, get_assignments_for_student, get_student_quiz_submissions, get_student_assignment_submissions

# UI Helper functions (previously in main.py, now specific to dashboards)
def render_dashboard_header(user_email: str, subtitle: str):
    st.header(f"Welcome, {user_email}! 👋")
    st.subheader(subtitle)

def render_quiz_card(quiz: dict):
    with st.container():
        st.subheader(f"📝 {quiz['title']}")
        st.write(quiz.get('description', ''))
        st.caption(f"Topics: {quiz.get('topics','N/A')} | Difficulty: {quiz.get('difficulty','N/A')} | Created: {quiz.get('created_at','N/A')[:10]}")

def render_assignment_card(assignment: dict):
    with st.container():
        st.subheader(f"💻 {assignment['title']}")
        st.write(assignment.get('description', ''))
        st.caption(f"Topic: {assignment.get('topic','N/A')} | Difficulty: {assignment.get('difficulty','N/A')} | Time: {assignment.get('time_limit','N/A')} min | Created: {assignment.get('created_at','N/A')[:10]}")

def render_teacher_dashboard():
    if not st.session_state.is_authenticated or st.session_state.user_role != "teacher":
        st.session_state.page = "login"
        st.session_state.auth_message = "You must be logged in as a teacher to access this page."
        st.rerun()
    
    render_dashboard_header(st.session_state.user.email, "Manage your quizzes and assignments here.")
    
    st.subheader("🚀 Quick Actions")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📝 Create New Quiz", use_container_width=True, type="primary"):
            st.session_state.page = "quiz" # This will be the quiz creation page for teachers
            st.rerun()
    with col2:
        if st.button("💻 Create New Assignment", use_container_width=True, type="primary"):
            st.session_state.page = "coding" # This will be the assignment creation page for teachers
            st.rerun()
    
    teacher_id = get_user_id()
    if not teacher_id:
        st.error("Could not retrieve teacher ID. Please log in again.")
        return

    st.markdown("--- ")
    st.header("📝 Your Quizzes")
    all_quizzes = get_quizzes_for_student() # Fetches all quizzes
    teacher_quizzes = [q for q in all_quizzes if q.get('teacher_id') == teacher_id]

    if not teacher_quizzes:
        st.info("You haven't created any quizzes yet. Use the Quiz Generator to create one!")
    else:
        for quiz in teacher_quizzes:
            render_quiz_card(quiz)
            if st.button("View Submissions", key=f"view_sub_btn_{quiz['id']}", use_container_width=True):
                st.session_state.view_quiz_id = quiz['id']
                st.session_state.selected_student_id = None 
                st.session_state.page = "quiz_submissions"
                st.rerun()
            st.markdown("--- ")
            
    st.markdown("--- ")
    st.header("💻 Your Assignments")
    all_assignments = get_assignments_for_student() # Fetches all assignments
    teacher_assignments = [a for a in all_assignments if a.get('teacher_id') == teacher_id]

    if not teacher_assignments:
        st.info("You haven't created any assignments yet. Use the Assignment Generator to create one!")
    else:
        for assignment in teacher_assignments:
            render_assignment_card(assignment)
            if st.button("View Submissions", key=f"view_assign_sub_btn_{assignment['id']}", use_container_width=True):
                st.session_state.view_assignment_id = assignment['id']
                st.session_state.page = "assignment_submissions"
                st.rerun()
            st.markdown("--- ")
            
    st.markdown("<br>", unsafe_allow_html=True)
    # Removed redundant signout button from here, it's in the sidebar

def render_student_dashboard():
    if not st.session_state.is_authenticated:
        st.session_state.page = "login"
        st.session_state.auth_message = "You must be logged in to access this page."
        st.rerun()
    
    render_dashboard_header(st.session_state.user.email, "Your learning journey continues here.")
    
    st.markdown("--- ")
    st.header("📝 Available Quizzes")
    quizzes = get_quizzes_for_student()
    user_id = get_user_id()
    if not quizzes:
        st.info("No quizzes available at the moment. Check back later!")
    else:
        for quiz in quizzes:
            render_quiz_card(quiz)
            # Check if student has already submitted this quiz
            submissions = get_student_quiz_submissions(user_id, quiz['id']) if user_id else []
            if submissions:
                # Show 'See Results' button
                if st.button("See Results", key=f"see_results_{quiz['id']}", use_container_width=True):
                    # Load results into session state
                    submission = submissions[0]  # Assume latest/only submission
                    from models.question import Question
                    from db_utils import get_quiz_details_by_id
                    import json
                    quiz_details = get_quiz_details_by_id(quiz['id'])
                    questions = quiz_details['questions'] if quiz_details else []
                    answers = submission.get('answers', {})
                    if isinstance(answers, str):
                        try:
                            answers = json.loads(answers)
                        except Exception:
                            answers = {}
                    score = submission.get('score', 0.0)
                    # Parse feedback
                    feedback = submission.get('feedback', None)
                    ai_feedback = json.loads(feedback) if feedback else None
                    correct_count = 0
                    for q in questions:
                        if answers.get(str(q.db_id), None) == q.correct_answer:
                            correct_count += 1
                    st.session_state.current_quiz_questions_for_results = questions
                    st.session_state.user_answers_for_results = answers
                    st.session_state.score_for_results = (correct_count, len(questions), score)
                    st.session_state.ai_feedback_for_results = ai_feedback
                    st.session_state.page = "results"
                    st.rerun()
            else:
                if st.button("Take Quiz", key=f"quiz_{quiz['id']}", use_container_width=True):
                    st.session_state.view_quiz_id = quiz['id']
                    st.session_state.page = "take_quiz"
                    st.rerun()
            st.markdown("--- ")
        
    st.markdown("--- ")
    st.header("💻 Available Assignments")
    assignments = get_assignments_for_student()
    if not assignments:
        st.info("No assignments available at the moment. Check back later!")
    else:
        for assignment in assignments:
            render_assignment_card(assignment)
            submissions = get_student_assignment_submissions(user_id, assignment['id']) if user_id else []
            if submissions:
                # Show 'See Feedback' button
                if st.button("See Feedback", key=f"see_feedback_{assignment['id']}", use_container_width=True):
                    submission = submissions[0]  # Assume latest/only submission
                    code = submission.get('code', '')
                    evaluation = submission.get('evaluation', None)
                    ai_evaluation = None
                    import json
                    if evaluation:
                        try:
                            ai_evaluation = json.loads(evaluation)
                        except Exception:
                            ai_evaluation = None
                    st.session_state.assignment_feedback_code = code
                    st.session_state.assignment_ai_evaluation = ai_evaluation
                    st.session_state.assignment_feedback_title = assignment.get('title', '')
                    st.session_state.page = "assignment_feedback"
                    st.rerun()
            else:
                if st.button("Solve Assignment", key=f"assignment_{assignment['id']}", use_container_width=True):
                    st.session_state.view_assignment_id = assignment['id']
                    st.session_state.page = "solve_assignment"
                    st.rerun()
            st.markdown("--- ")
        
    st.markdown("<br>", unsafe_allow_html=True)
    # Removed redundant signout button from here, it's in the sidebar 

def render_assignment_feedback_page():
    """Show AI feedback for a completed assignment to the student."""
    st.title(f"Assignment Feedback: {st.session_state.get('assignment_feedback_title', '')}")
    st.subheader("Your Submitted Code:")
    st.code(st.session_state.get('assignment_feedback_code', ''), language="python")
    ai_eval = st.session_state.get('assignment_ai_evaluation')
    if ai_eval:
        st.markdown("---")
        st.subheader("AI Evaluation & Feedback")
        st.markdown(f"**Verdict:** {ai_eval.get('verdict', 'N/A')}")
        st.markdown(f"**Analysis:** {ai_eval.get('analysis', 'N/A')}")
        st.markdown(f"**Suggestions for Improvement:** {ai_eval.get('improvements', 'N/A')}")
        st.markdown("---")
    if st.button("Back to Student Dashboard", key="assignment_feedback_back_to_dash"):
        for key in ['assignment_feedback_code', 'assignment_ai_evaluation', 'assignment_feedback_title']:
            if key in st.session_state:
                st.session_state.pop(key, None)
        st.session_state.page = "student_dashboard"
        st.rerun() 