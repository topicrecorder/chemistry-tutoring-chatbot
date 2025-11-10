# image_processor.py
import google.generativeai as genai
import os
import streamlit as st
from PIL import Image
import re
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

def extract_text_from_image(image):
    """
    Extract text from an image using Gemini Vision
    """
    try:
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        prompt = """
        Extract the chemistry question from this image. Return ONLY the text of the question exactly as it appears.
        If there are multiple questions, extract the main one. Preserve any chemical formulas, equations, or special notation.
        Include ALL multiple choice options if present.
        """
        
        response = model.generate_content([prompt, image])
        return response.text.strip()
    
    except Exception as e:
        st.error(f"Error extracting text from image: {str(e)}")
        return None

def analyze_question_type(question_text):
    """
    Analyze the question to determine if it's MCQ, structured, or other type
    """
    # Patterns to identify MCQ questions
    mcq_patterns = [
        r'[A-D][\.\)]\s*.+',  # A. option, B) option, etc.
        r'\(a\)\s*.+\(b\)\s*.+\(c\)\s*.+\(d\)\s*.+',  # (a) option (b) option etc.
        r'①\s*.+②\s*.+③\s*.+④\s*.+',  # Numbered options
        r'options?:',  # Contains "options" keyword
        r'[①②③④]',  # Circled numbers
    ]
    
    for pattern in mcq_patterns:
        if re.search(pattern, question_text, re.IGNORECASE | re.MULTILINE):
            return "MCQ"
    
    # Check for structured questions
    structured_patterns = [
        r'explain\s+.*step',
        r'calculate\s+.*show\s+.*working',
        r'describe\s+.*process',
        r'how\s+.*work',
        r'what\s+.*steps',
    ]
    
    for pattern in structured_patterns:
        if re.search(pattern, question_text, re.IGNORECASE):
            return "STRUCTURED"
    
    return "GENERAL"

def extract_mcq_options(question_text):
    """
    Extract MCQ options from question text
    """
    options = {}
    
    # Try different patterns to extract options
    patterns = [
        # Pattern for A. Option format
        r'([A-D])[\.\)]\s*([^\nA-D]+)(?=\n[A-D][\.\)]|\n\n|$)',
        # Pattern for (a) Option format
        r'\(([a-d])\)\s*([^\n]+)(?=\n\([a-d]\)|\n\n|$)',
        # Pattern for numbered options ①, ②, etc.
        r'([①②③④])\s*([^\n①②③④]+)(?=\n[①②③④]|\n\n|$)',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, question_text, re.MULTILINE | re.IGNORECASE)
        if matches:
            for key, value in matches:
                options[key.upper() if key.isalpha() else key] = value.strip()
            break
    
    return options

def get_enhanced_teacher_answer(question_text):
    """
    Get enhanced step-by-step explanation that understands question type
    """
    # Analyze question type
    question_type = analyze_question_type(question_text)
    
    if question_type == "MCQ":
        options = extract_mcq_options(question_text)
        
        prompt = f"""
        You are a chemistry teacher explaining multiple choice questions to Sri Lankan students in Sinhala.
        
        QUESTION: {question_text}
        
        OPTIONS: {options}
        
        Follow these guidelines STRICTLY:
        1. Respond in Sinhala ONLY
        2. First, identify this as a multiple choice question
        3. Break down the explanation into clear numbered steps:
           පියවර 1: ප්‍රශ්නය අවබෝධ කරගන්න - ප්‍රශ්නයේ අර්ථය සහ අවශ්‍ය කරුණු පැහැදිලි කරන්න
           පියවර 2: එක් එක් විකල්පය විශ්ලේෂණය කරන්න - සෑම විකල්පයක්ම වෙන වෙනම පරීක්ෂා කර නිවැරදි/වැරදි බව පැහැදිලි කරන්න
           පියවර 3: නිවැරදි පිළිතුර තෝරාගැනීම - නිවැරදි පිළිතුර සහ එය නිවැරදි වීමට හේතුව පැහැදිලි කරන්න
           පියවර 4: වැරදි පිළිතුරු ඇයි වැරදි ද යන්න පැහැදිලි කරන්න
        4. Use simple language suitable for high school students
        5. Include relevant chemical concepts and principles
        6. Explain the reasoning behind eliminating wrong options
        7. Highlight key chemistry concepts tested in this question
        8. Conclude with a summary of the main concept learned
        
        Response format:
        පියවර 1: [Explanation]
        පියවර 2: [Explanation]
        පියවර 3: [Explanation]
        පියවර 4: [Explanation]
        සාරාංශය: [Summary of the main concept]
        """
    
    elif question_type == "STRUCTURED":
        prompt = f"""
        You are a chemistry teacher explaining structured questions to Sri Lankan students in Sinhala.
        
        QUESTION: {question_text}
        
        Follow these guidelines STRICTLY:
        1. Respond in Sinhala ONLY
        2. Break down the explanation into clear numbered steps based on the question structure
        3. For calculation questions: show step-by-step working
        4. For explanation questions: provide detailed reasoning
        5. For mechanism questions: describe each step clearly
        6. Use simple language suitable for high school students
        7. Include relevant examples from the Sri Lankan curriculum
        8. Highlight key concepts and formulas
        9. Explain the reasoning behind each step
        10. Conclude with a summary of the main concept
        
        Response format:
        පියවර 1: [Explanation/Calculation]
        පියවර 2: [Explanation/Calculation]
        ...
        සාරාංශය: [Summary]
        """
    
    else:  # GENERAL questions
        prompt = f"""
        You are a chemistry teacher specializing in explaining concepts to Sri Lankan students in Sinhala.
        Provide a detailed, step-by-step explanation for the following chemistry question:
        "{question_text}"
        
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

def get_answer_from_question(question_text, teacher_mode=False):
    """
    Get answer for the extracted question with enhanced teacher mode
    """
    if teacher_mode:
        return get_enhanced_teacher_answer(question_text)
    else:
        # Import process_question locally to avoid circular imports
        from app import process_question
        return process_question(question_text)

def process_screenshot(image, teacher_mode=False):
    """
    Main function to process screenshot and return answer
    """
    # Step 1: Extract text from image
    with st.spinner("📖 Reading question from image..."):
        question_text = extract_text_from_image(image)
    
    if not question_text:
        return "Could not read the question from the image. Please try again with a clearer image."
    
    # Display and extracted question with type analysis
    question_type = analyze_question_type(question_text)
    
    if question_type == "MCQ":
        options = extract_mcq_options(question_text)
        st.info(f"**🔍 Identified as Multiple Choice Question**")
        st.info(f"**Extracted Question:** {question_text.split('A.')[0].split('A)')[0].split('(a)')[0].strip()}")
        if options:
            st.info("**Options Found:**")
            for key, value in options.items():
                st.info(f"**{key}.** {value}")
    else:
        st.info(f"**Extracted Question:** {question_text}")
        st.info(f"**Question Type:** {question_type}")
    
    # Step 2: Get answer
    with st.spinner("🧠 Analyzing and preparing answer..."):
        answer = get_answer_from_question(question_text, teacher_mode)
    
    return answer