# app/utils/llm_client.py
import anyio
import json
import re # Import re at the top
from .connection import Connection

class LLMClient:
    # ... (keep __init__, call_sync, chat, generate_questions, evaluate_answer as they are) ...
    def __init__(self):
        self._llm = Connection().get_llm()

    # --- synchronous call (used by question generation) --------------
    def call_sync(self, prompt: str) -> str:
        """
        Blocking call – returns the model response as a plain string.
        """
        return self._llm.call(prompt).strip()

    # --- asynchronous call (used by FastAPI handlers) ----------------
    async def chat(self, prompt: str) -> str:
        """
        Non-blocking wrapper that executes the blocking CrewAI call
        in a thread so FastAPI can stay async.
        """
        return await anyio.to_thread.run_sync(self.call_sync, prompt)

    # --- Service-specific methods ------------------------------------
    async def generate_questions(self, prompt: str):
        """Generate interview questions from prompt"""
        response = await self.chat(prompt)
        
        # Parse the response to extract individual questions
        questions = []
        lines = response.split('\n')
        
        for line in lines:
            line = line.strip()
            if line and (
                line.startswith('Q') or 
                line.startswith('1.') or 
                line.startswith('2.') or 
                line.startswith('3.') or 
                line.startswith('4.') or 
                line.startswith('5.') or 
                line.startswith('-') or
                line.startswith('*')
            ):
                # Clean up the question format
                if ':' in line:
                    question = line.split(':', 1)[1].strip()
                else:
                    question = line
                
                # Remove numbering and formatting
                question = question.lstrip('1234567890.- *')
                if question:
                    questions.append(question)
        
        # If no questions found with above parsing, try different approach
        if not questions:
            # Split by double newlines or numbered patterns
            question_patterns = re.findall(r'\d+\.\s*(.+?)(?=\d+\.|$)', response, re.DOTALL)
            for q in question_patterns:
                clean_q = q.strip().replace('\n', ' ')
                if clean_q:
                    questions.append(clean_q)
        
        return questions

    async def evaluate_answer(self, question: str, answer: str, config: dict):
        """Evaluate an answer and provide feedback"""
        prompt = f"""
        Evaluate this interview answer for a {config.get('role', 'candidate')} position:
        
        Question: {question}
        Answer: {answer}
        
        Provide:
        1. Score (1-10)
        2. Verdict (correct/partial/incorrect)
        3. Brief constructive feedback
        
        Format as JSON:
        {{"score": X, "verdict": "...", "feedback": "..."}}
        """
        
        response = await self.chat(prompt)
        try:
            # Find the JSON part of the response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            raise ValueError("No JSON found")
        except:
            # Fallback if JSON parsing fails
            return {
                "score": 5,
                "verdict": "partial",
                "feedback": "Could not parse evaluation, but the answer was submitted."
            }

    async def generate_hint(self, question: str, config: dict):
        """Generate a hint for the current question"""
        prompt = f"""
        Provide a brief helpful hint for this interview question (don't give away the answer):
        
        Question: {question}
        Role: {config.get('role', 'candidate')}
        
        Give a short, guiding hint that helps the candidate think in the right direction.
        """
        return await self.chat(prompt)

    async def generate_report(self, prompt: str):
        """Generate overall interview report and parse it as JSON."""
        response = await self.chat(prompt)
        try:
            # Use regex to find the JSON block, as LLMs sometimes add extra text
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            raise ValueError("No JSON object found in the LLM response.")
        except Exception as e:
            # Fallback if JSON parsing fails
            print(f"Error parsing report JSON: {e}\nResponse was: {response}")
            return {
                "overall_score": 0,
                "strengths": "Not available due to a formatting error.",
                "areas_for_improvement": "Could not be generated."
            }