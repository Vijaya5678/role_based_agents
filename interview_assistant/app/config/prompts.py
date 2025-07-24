# app/config/prompts.py

DIFFICULTY_CONFIG = {
    "beginner": {
        "num_questions": 5,
        "time_minutes": 15,
        "question_complexity": "basic concepts and fundamentals",
        "hint_frequency": "generous",
        "evaluation_criteria": "understanding of core concepts"
    },
    "intermediate": {
        "num_questions": 8,
        "time_minutes": 25,
        "question_complexity": "practical application and problem-solving",
        "hint_frequency": "moderate",
        "evaluation_criteria": "practical knowledge and implementation"
    },
    "advanced": {
        "num_questions": 12,
        "time_minutes": 40,
        "question_complexity": "complex scenarios and system design",
        "hint_frequency": "minimal",
        "evaluation_criteria": "deep expertise and architectural thinking"
    }
}

INTERVIEW_PROMPT_TEMPLATE = """
You are conducting a professional interview for a {role} position in the {category} domain.

INTERVIEW CONFIGURATION:
- Difficulty Level: {difficulty}
- Number of Questions: {num_questions}
- Time Allocation: {time_minutes} minutes
- Question Focus: {question_complexity}
- Evaluation Criteria: {evaluation_criteria}

QUESTION GENERATION GUIDELINES:
- Generate exactly {num_questions} questions appropriate for {difficulty} level
- Focus on {category} skills specific to {role}
- Questions should test {question_complexity}
- Each question should be clear, specific, and measurable
- Include a mix of theoretical and practical questions

EVALUATION GUIDELINES:
- Assess answers based on {evaluation_criteria}
- Provide constructive feedback
- Rate each answer on a scale of 1-10
- Identify strengths and areas for improvement

HINT GUIDELINES:
- Provide {hint_frequency} hints when requested
- Hints should guide thinking without giving away answers
- Keep hints brief and focused on key concepts

Generate the interview questions now:
"""
