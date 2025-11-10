# sinhala_chemistry_teacher.py
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

def get_step_by_step_answer(user_question):
    """
    Get step-by-step chemistry explanation in Sinhala using Gemini
    """
    prompt = f"""
    You are a chemistry teacher specializing in explaining concepts to Sri Lankan students in Sinhala.
    Provide a detailed, step-by-step explanation for the following chemistry question:
    "{user_question}"
    
    Follow these guidelines STRICTLY:
    1. Respond in Sinhala ONLY
    2. Break down the explanation into clear numbered steps
    3. Use simple language suitable for high school students
    4. Include relevant examples from the Sri Lankan curriculum
    5. Highlight key concepts and formulas
    6. Explain the reasoning behind each step
    7. Conclude with a summary of the main concept
    
    Response format:
    පියවර 1: [Explanation]
    පියවර 2: [Explanation]
    ...
    සාරාංශය: [Summary]
    """
    
    model = genai.GenerativeModel('gemini-2.5-flash')
    response = model.generate_content(prompt)
    return response.text.strip()