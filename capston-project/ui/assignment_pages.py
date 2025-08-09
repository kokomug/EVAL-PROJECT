import streamlit as st
from typing import Dict, Any # For type hinting

# Assuming services, auth, db_utils are accessible from the root or via PYTHONPATH
from services.llm_service import generate_content, GROQ_MODELS
from services.assignment_processing_service import (
    generate_assignment_creation_prompt,
    parse_assignment_details,
    generate_code_evaluation_prompt, # Not used yet, but might be if evaluation is added to submission viewing
    parse_code_evaluation # Not used yet
)
from db_utils import (
    save_assignment_to_db,
    get_assignment_details_by_id,
    save_assignment_submission,
    get_assignment_submissions_for_teacher
)
from auth import get_user_id

ASSIGNMENT_GROQ_MODELS = [m for m in GROQ_MODELS if m != "llama-guard-3-8b"]

def render_coding_page():
    """Render the coding assignment generator page."""
    if st.session_state.user_role != "teacher":
        st.error("Only teachers can create coding assignments. Please use the dashboard to solve available assignments.")
        # Add a button to go back to the appropriate dashboard
        if st.button("Back to Dashboard"):
            st.session_state.page = "student_dashboard" if st.session_state.user_role == "student" else "teacher_dashboard"
            st.rerun()
        return
    st.title("Coding Assignment Generator")
    topics = {
        "Python": ["Python Basics", "Functions", "Classes & OOP", "File Handling", "Error Handling"],
        "Data Structures": ["Lists", "Dictionaries", "Sets", "Tuples", "Stacks & Queues", "Trees", "Graphs"],
        "Algorithms": ["Searching", "Sorting", "Dynamic Programming", "Recursion", "Greedy Algorithms"],
        "Data Science": ["Pandas Basics", "Data Visualization", "Linear Regression", "Classification", "Clustering"],
        "Advanced": ["Neural Networks", "NLP", "Computer Vision", "Web Scraping", "API Development"]
    }

    with st.form("assignment_form"):
        st.subheader("Create Your Coding Assignment")
        category = st.selectbox("Category:", list(topics.keys()))
        topic = st.selectbox("Topic:", topics[category])
        difficulty = st.select_slider("Difficulty:", options=["Beginner", "Intermediate", "Advanced"])
        time_limit = st.slider("Estimated completion time (minutes):", 10, 120, 30, step=5)
        # LLM model selection dropdown
        deepseek_model = "deepseek-r1-distill-llama-70b"
        default_index = ASSIGNMENT_GROQ_MODELS.index(deepseek_model) if deepseek_model in ASSIGNMENT_GROQ_MODELS else 0
        selected_model = st.selectbox("Choose LLM Model", ASSIGNMENT_GROQ_MODELS, index=default_index)
        generate_btn = st.form_submit_button("Generate Assignment", use_container_width=True, type="primary")
        if generate_btn:
            if not topic:
                st.warning("Please select a topic.")
            else:
                prompt = generate_assignment_creation_prompt(topic, difficulty, time_limit)
                response = generate_content(prompt, show_spinner=True, model_name=selected_model)
                if response:
                    parsed_content = parse_assignment_details(response)
                    if "Error parsing" not in parsed_content.get("title", ""):
                        assignment_data = {
                            "title": parsed_content.get("title", f"Assignment on {topic}"),
                            "description": parsed_content.get("background", ""),
                            "requirements": parsed_content.get("requirements", ""),
                            "hints": parsed_content.get("hints", ""),
                            "code_template": parsed_content.get("code_template_content", ""),
                            "expected_output": parsed_content.get("expected_output_content", ""),
                            "evaluation_criteria": parsed_content.get("evaluation_criteria", ""),
                            "topic": topic,
                            "difficulty": difficulty,
                            "time_limit": time_limit
                        }
                        assignment_id = save_assignment_to_db(assignment_data)
                        if assignment_id:
                            st.success(f"Assignment '{assignment_data['title']}' saved and ready!")
                        else:
                            st.error("Failed to save the assignment to the database.")
                    else:
                        st.error("Could not parse assignment details correctly from the LLM response.")
                        st.info("The LLM response was:\\n" + response)
                else:
                    st.error("Failed to generate assignment content. Please check LLM service or API key.")

    if st.button("Back to Teacher Dashboard", key="coding_page_back_dash"):
        st.session_state.page = "teacher_dashboard"
        st.rerun()


def render_solve_assignment_page():
    """Student view: Solve a coding assignment and submit solution."""
    assignment_id = st.session_state.get("view_assignment_id")
    if not assignment_id:
        st.warning("No assignment selected.")
        if st.button("Back to Dashboard"):
            st.session_state.page = "student_dashboard"
            st.rerun()
        return

    assignment_details = get_assignment_details_by_id(assignment_id)
    if not assignment_details:
        st.error("Assignment not found.")
        if st.button("Back to Dashboard"):
            st.session_state.page = "student_dashboard"
            st.rerun()
        return
    
    st.title(assignment_details['title'])
    st.markdown(f"**Topic:** {assignment_details.get('topic', 'N/A')} | **Difficulty:** {assignment_details.get('difficulty', 'N/A')} | **Est. Time:** {assignment_details.get('time_limit', 'N/A')} mins")
    st.markdown("---")
    
    tab1, tab2, tab3 = st.tabs(["📋 Description & Requirements", "💡 Hints", "📝 Your Solution"])

    with tab1:
        st.subheader("Background")
        st.markdown(assignment_details.get('description','No description provided.'))
        st.subheader("Requirements")
        st.markdown(assignment_details.get('requirements','No requirements specified.'))
        st.subheader("Expected Output")
        st.code(assignment_details.get('expected_output','# No expected output provided.'), language="text")

    with tab2:
        st.subheader("Hints")
        st.info(assignment_details.get('hints','No hints provided for this assignment.'))

    with tab3:
        st.subheader("Code Template")
        template_code = assignment_details.get('code_template','# No code template provided for this assignment.')
        st.code(template_code, language="python")
        
        if st.session_state.get("_current_solve_assignment_id") != assignment_id:
            st.session_state.student_code_solution = template_code
            st.session_state._current_solve_assignment_id = assignment_id
            st.session_state.assignment_submitted_successfully = False
            st.session_state.assignment_ai_evaluation = None

        with st.form("solve_assignment_form"):
            user_code_solution = st.text_area(
                "Your Code Solution:", 
                value=st.session_state.get("student_code_solution", template_code), 
                height=400, 
                key="student_code_solution_area"
            )
            
            submit_button = st.form_submit_button("Submit Assignment", use_container_width=True, type="primary")
            
            if submit_button:
                user_id = get_user_id()
                if not user_id:
                    st.error("User not identified. Please log in again.")
                else:
                    # Generate AI evaluation using LLM
                    from services.assignment_processing_service import generate_code_evaluation_prompt, parse_code_evaluation
                    from services.llm_service import generate_content
                    prompt = generate_code_evaluation_prompt(
                        user_code_solution, 
                        assignment_details.get('requirements', ''), 
                        assignment_details.get('expected_output', '')
                    )
                    ai_evaluation_raw = generate_content(prompt, show_spinner=True)
                    ai_evaluation = parse_code_evaluation(ai_evaluation_raw) if ai_evaluation_raw else {}
                    import json
                    evaluation_to_save = json.dumps(ai_evaluation) if ai_evaluation else None
                    save_successful = save_assignment_submission(assignment_id, user_id, user_code_solution, evaluation_feedback=evaluation_to_save)
                    if save_successful:
                        st.session_state.assignment_submitted_successfully = True
                        st.session_state.assignment_ai_evaluation = ai_evaluation
                        st.rerun() 
                    else:
                        st.error("There was an issue submitting your assignment. Please try again.")

        if st.session_state.get("assignment_submitted_successfully"):
            st.success("Assignment submitted successfully!")
            # Show AI evaluation to student
            ai_eval = st.session_state.get("assignment_ai_evaluation")
            if ai_eval:
                st.markdown("---")
                st.subheader("AI Evaluation & Feedback")
                st.markdown(f"**Verdict:** {ai_eval.get('verdict', 'N/A')}")
                st.markdown(f"**Analysis:** {ai_eval.get('analysis', 'N/A')}")
                st.markdown(f"**Suggestions for Improvement:** {ai_eval.get('improvements', 'N/A')}")
                st.markdown("---")
            if st.button("Back to Student Dashboard", key="solve_assignment_back_to_dash_after_submit"):
                st.session_state.page = "student_dashboard"
                keys_to_pop = ['student_code_solution', 'assignment_submitted_successfully', 
                               'view_assignment_id', '_current_solve_assignment_id', 'assignment_ai_evaluation']
                for key in keys_to_pop:
                    if key in st.session_state:
                        st.session_state.pop(key, None)
                st.rerun()
    
    if st.button("Back to Student Dashboard", key="solve_assignment_main_back_btn"):
        st.session_state.page = "student_dashboard"
        st.rerun()


def render_assignment_submissions_page():
    """Teacher view: See all student submissions for an assignment."""
    assignment_id = st.session_state.get("view_assignment_id")
    teacher_id = get_user_id()

    if not teacher_id:
        st.error("Teacher ID not found. Please log in.")
        st.session_state.page = "login"
        st.rerun()
        return
        
    if not assignment_id:
        st.warning("No assignment selected to view submissions.")
        if st.button("Back to Teacher Dashboard"):
            st.session_state.page = "teacher_dashboard"
            st.rerun()
        return
        
    assignment_details = get_assignment_details_by_id(assignment_id)
    if not assignment_details:
        st.error("Assignment details not found. It might have been deleted.")
        if st.button("Back to Teacher Dashboard"):
            st.session_state.page = "teacher_dashboard"
            st.rerun()
        return

    st.title(f"Submissions for: {assignment_details['title']}")
    st.markdown(f"Topic: {assignment_details.get('topic', 'N/A')} | Difficulty: {assignment_details.get('difficulty', 'N/A')}")
    st.markdown("--- ")
    
    submissions = get_assignment_submissions_for_teacher(teacher_id, assignment_id)
    if not submissions:
        st.info("No student submissions yet for this assignment.")
    else:
        student_submission_options = {
            sub['student_id']: f"Student ID: {sub['student_id']} (Submitted: {sub.get('created_at', '')[:16]})" 
            for sub in submissions
        }
        
        selected_student_id = st.selectbox(
            "Select a student submission to view:",
            options=[""] + list(student_submission_options.keys()),
            format_func=lambda x: student_submission_options.get(x, "Select a student...")
        )

        if selected_student_id:
            submission_details = next((s for s in submissions if s['student_id'] == selected_student_id), None)
            if submission_details:
                st.subheader(f"Code Submitted by Student ID: {submission_details['student_id']}")
                st.markdown(f"**Submitted at:** {submission_details.get('created_at', 'N/A')[:19]}")
                
                submitted_code = submission_details.get('code', '# No code submitted or code is empty.')
                st.code(submitted_code, language="python")
                
                st.markdown("---")
                # Placeholder for AI evaluation feature
                st.subheader("AI Code Evaluation")
                if st.button("Evaluate Code with AI", key=f"eval_{submission_details['id']}"):
                    with st.spinner("Evaluating code..."):
                        prompt = generate_code_evaluation_prompt(
                            submitted_code, 
                            assignment_details.get('requirements', ''), 
                            assignment_details.get('expected_output', '')
                        )
                        evaluation_response = generate_content(prompt, show_spinner=False) # Spinner is already active
                        if evaluation_response:
                            parsed_eval = parse_code_evaluation(evaluation_response)
                            st.markdown(f"**Verdict:** {parsed_eval.get('verdict', 'Not available')}")
                            with st.expander("Detailed Analysis", expanded=True):
                                st.markdown("**Analysis:**")
                                st.markdown(parsed_eval.get('analysis', 'Not available'))
                                st.markdown("**Suggestions for Improvement:**")
                                st.markdown(parsed_eval.get('improvements', 'Not available'))
                        else:
                            st.error("Failed to get AI evaluation. The LLM service might be unavailable or the request timed out.")

            else:
                st.error("Selected submission details not found.")
            st.markdown("---")
            
    if st.button("Back to Teacher Dashboard", key="assign_sub_back_to_dash"):
        st.session_state.page = "teacher_dashboard"
        st.session_state.pop('view_assignment_id', None)
        st.rerun() 