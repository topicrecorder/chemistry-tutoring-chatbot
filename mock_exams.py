# mock_exams.py
import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv
import random

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Chemistry topics with subtopics
CHEMISTRY_TOPICS = {
    "Atomic Structure": [
        "Atomic models",
        "Electron configuration",
        "Quantum numbers",
        "Periodic trends",
        "Isotopes"
    ],
    "Chemical Bonding": [
        "Ionic bonding",
        "Covalent bonding",
        "Metallic bonding",
        "Intermolecular forces",
        "Lewis structures"
    ],
    "Kinetic Theory": [
        "Gas laws",
        "Kinetic molecular theory",
        "Diffusion and effusion",
        "Real vs ideal gases",
        "Maxwell-Boltzmann distribution"
    ]
}

def generate_exam_questions(topic, num_questions=5):
    """Generate exam questions for a specific chemistry topic"""
    prompt = f"""
    You are a chemistry exam creator. Generate {num_questions} multiple-choice questions in Sinhala 
    focusing specifically on the topic: {topic}. 
    
    Format each question strictly as:
    'Q:: [question] | A:: [correct] | B:: [wrong1] | C:: [wrong2] | D:: [wrong3]'
    
    Important rules:
    1. Questions must be at G.C.E. Advanced Level difficulty
    2. Include calculations where appropriate
    3. Cover different aspects of {topic}
    4. Use Sinhala throughout
    5. Keep questions concise (max 2 sentences)
    """
    
    model = genai.GenerativeModel('gemini-2.5-flash')
    response = model.generate_content(prompt)
    
    if response.text:
        questions = [q.strip() for q in response.text.split('Q:: ') if q.strip()]
        return [f'Q:: {q}' for q in questions if '| A:: ' in q][:num_questions]
    return []

def analyze_performance(questions, user_answers, correct_answers):
    """Analyze exam performance and provide feedback"""
    # Calculate score
    score = sum(1 for u, c in zip(user_answers, correct_answers) if u == c)
    
    # Identify weak areas
    incorrect_indices = [i for i, (u, c) in enumerate(zip(user_answers, correct_answers)) if u != c]
    weak_subtopics = []
    
    if incorrect_indices:
        prompt = f"""
        You are a chemistry tutor analyzing exam performance. The student scored {score}/{len(questions)} 
        in this exam. They struggled with questions at these indices: {incorrect_indices}.
        
        Provide:
        1. Overall performance assessment in Sinhala
        2. List of specific weak areas (subtopics)
        3. 3 actionable revision tips in Sinhala
        4. Recommended study resources
        
        Format:
        Assessment: [text]
        Weak Areas: [comma separated list]
        Revision Tips: 
        1. [tip1]
        2. [tip2]
        3. [tip3]
        Resources: [resource links]
        """
        
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        return response.text, score
    return "", score

def show_mock_exams():
    """Display mock exam interface"""
    # Initialize session state
    if 'exam' not in st.session_state:
        st.session_state.exam = {
            'questions': [],
            'user_answers': [],
            'correct_answers': [],
            'submitted': False,
            'analysis': ""
        }
    
    st.markdown("""
    <div class="card">
        <div class="card-title">
            🧪 Mock Exams with Weakness Analysis
        </div>
        <p>Take topic-specific exams and get personalized feedback on your weak areas</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Topic selection card
        with st.container():
            st.markdown("""
            <div class="card">
                <div class="card-title">
                    Create New Exam
                </div>
            """, unsafe_allow_html=True)
            
            # Topic selection
            selected_topic = st.selectbox(
                "අවශ්‍ය පාඩම තෝරන්න:",
                list(CHEMISTRY_TOPICS.keys()),
                key="exam_topic"
            )
            
            # Show subtopics
            st.write("**ආවරණය වන අනුමතෘකා:**")
            for subtopic in CHEMISTRY_TOPICS[selected_topic]:
                st.markdown(f"- {subtopic}")
            
            # Generate exam button
            if st.button("📝 Generate Exam", use_container_width=True):
                with st.spinner("ඔබට අදාළ ප්‍රශ්න සකසමින් පවතී..."):
                    questions = generate_exam_questions(selected_topic, num_questions=5)
                    if questions:
                        correct_answers = []
                        for q in questions:
                            parts = q.split('|')
                            correct_answers.append(parts[1].split(':: ')[1])
                        
                        st.session_state.exam = {
                            'questions': questions,
                            'correct_answers': correct_answers,
                            'user_answers': [None] * len(questions),
                            'submitted': False,
                            'analysis': "",
                            'score': 0
                        }
                        st.success("ප්‍රශ්නාවලිය සැකසීම සාර්ථකය්!")
                    else:
                        st.error("Failed to generate exam. Please try again.")
            
            st.markdown("</div>", unsafe_allow_html=True)
        
        # Exam display
        if st.session_state.exam['questions']:
            st.markdown("""
            <div class="card">
                <div class="card-title">
                    Current Exam: {}
                </div>
            """.format(selected_topic), unsafe_allow_html=True)
            
            with st.form("exam_form"):
                for i, q_data in enumerate(st.session_state.exam['questions']):
                    parts = q_data.split('|')
                    st.markdown(f"""
                    <div class="quiz-question">
                        <h4>Question {i+1}</h4>
                        <p>{parts[0].replace('Q:: ', '')}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    options = [p.split(':: ')[1] for p in parts[1:]]
                    
                    st.session_state.exam['user_answers'][i] = st.radio(
                        f"Select your answer for question {i+1}:",
                        options,
                        key=f"exam_q{i}",
                        index=None,
                        label_visibility="collapsed"
                    )
                
                submitted = st.form_submit_button("✅ Submit Exam", use_container_width=True)
                if submitted:
                    with st.spinner("Analyzing your performance..."):
                        analysis, score = analyze_performance(
                            st.session_state.exam['questions'],
                            st.session_state.exam['user_answers'],
                            st.session_state.exam['correct_answers']
                        )
                        st.session_state.exam['analysis'] = analysis
                        st.session_state.exam['submitted'] = True
                        st.session_state.exam['score'] = score
                        st.rerun()
            
            st.markdown("</div>", unsafe_allow_html=True)
    
    with col2:
        # Performance analysis
        if st.session_state.exam.get('submitted', False):
            analysis = st.session_state.exam['analysis']
            score = st.session_state.exam['score']
            total = len(st.session_state.exam['questions'])
            
            # Extract components from analysis
            assessment = ""
            weak_areas = ""
            tips = []
            resources = ""
            
            if analysis:
                parts = analysis.split('Assessment:')
                if len(parts) > 1:
                    assessment = parts[1].split('Weak Areas:')[0].strip()
                
                parts = analysis.split('Weak Areas:')
                if len(parts) > 1:
                    weak_areas = parts[1].split('Revision Tips:')[0].strip()
                
                parts = analysis.split('Revision Tips:')
                if len(parts) > 1:
                    tips = [t.strip() for t in parts[1].split('Resources:')[0].split('\n') if t.strip() and t.strip()[0].isdigit()]
                
                parts = analysis.split('Resources:')
                if len(parts) > 1:
                    resources = parts[1].strip()
            
            # Display results
            st.markdown(f"""
            <div class="card" style="background-color: {'#d4edda' if score/total >= 0.7 else '#f8d7da'};">
                <h3>Exam Results: {score}/{total}</h3>
                <p>{'Excellent! 🎉' if score/total >= 0.8 else 'Good job! 👍' if score/total >= 0.6 else 'Needs improvement 📚'}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Weakness analysis card
            with st.container():
                st.markdown("""
                <div class="card">
                    <div class="card-title">
                        Performance Analysis
                    </div>
                """, unsafe_allow_html=True)
                
                if assessment:
                    st.markdown(f"**Assessment:** {assessment}")
                
                if weak_areas:
                    st.markdown(f"**Weak Areas:** {weak_areas}")
                
                if tips:
                    st.markdown("**Revision Tips:**")
                    for tip in tips:
                        st.markdown(f"- {tip}")
                
                if resources:
                    st.markdown(f"**Resources:** {resources}")
                
                st.markdown("</div>", unsafe_allow_html=True)
                
                # Detailed answers
                with st.expander("📝 View Correct Answers"):
                    for i, q_data in enumerate(st.session_state.exam['questions']):
                        parts = q_data.split('|')
                        question = parts[0].replace('Q:: ', '')
                        correct = st.session_state.exam['correct_answers'][i]
                        user_ans = st.session_state.exam['user_answers'][i]
                        
                        st.markdown(f"**Question {i+1}:** {question}")
                        st.markdown(f"**Your answer:** {user_ans} {'✅' if user_ans == correct else '❌'}")
                        st.markdown(f"**Correct answer:** {correct}")
                        st.markdown("---")

# For testing
if __name__ == "__main__":
    show_mock_exams()