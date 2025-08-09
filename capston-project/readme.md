# AI Exam Generator

An interactive educational platform that uses AI to generate quizzes and coding assignments. Features include:

- User authentication with role-based access (teacher/student)
- Multiple choice quiz generator with AI grading
- Coding assignment generator with automated evaluation
- Role-specific dashboards for teachers and students

## Setup Instructions

### 1. Environment Setup

Create a `.env` file in the project root with your API keys:

```
# Groq API Configuration
GROQ_API_KEY=your_groq_api_key_here

# Supabase Configuration
SUPABASE_URL=https://xolzhwksoafumenbhugs.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhvbHpod2tzb2FmdW1lbmJodWdzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDc2OTEzNDMsImV4cCI6MjA2MzI2NzM0M30.Ykel1cUqIH0XvffyNyOFvLO9IUUt3H6UfFN1C13eyA0
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the Application

```bash
streamlit run main.py
```

## Features

### Authentication
- Sign up as a teacher or student
- Secure login/logout functionality
- Role-based redirects to appropriate dashboards

### Teacher Features
- Create customized quizzes with AI
- Generate coding assignments for students
- Set difficulty levels for content

### Student Features
- Take quizzes with instant feedback
- Complete coding assignments with real-time evaluation
- Get personalized learning recommendations

## Technology Stack

- **Frontend**: Streamlit
- **Authentication**: Supabase Auth
- **AI**: Groq LLM (Llama-3-8b)
- **Database**: Supabase PostgreSQL
