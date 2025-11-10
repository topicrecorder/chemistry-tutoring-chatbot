import streamlit as st
import phet_simulations
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import google.generativeai as genai
from langchain_community.vectorstores import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
import speech_recognition as sr
from gtts import gTTS
import base64
from io import BytesIO
from langchain.memory import ConversationBufferMemory
from PIL import Image
import time
import random
from sinhala_chemistry_teacher import get_step_by_step_answer
from mock_exams import show_mock_exams
# from iupac_nomenclature import load_iupac_model, get_iupac_response, translate_to_sinhala
from smart_table import show_smart_table
from guided_labs import show_guided_labs
from image_processor import process_screenshot


load_dotenv()
os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Initialize session states
if 'listening' not in st.session_state:
    st.session_state.listening = False
if 'voice_input' not in st.session_state:
    st.session_state.voice_input = ""
if 'accessibility_mode' not in st.session_state:
    st.session_state.accessibility_mode = False
if 'current_tab' not in st.session_state:
    st.session_state.current_tab = "Chat"
if 'first_run' not in st.session_state:
    st.session_state.first_run = True
if 'retry_count' not in st.session_state:
    st.session_state.retry_count = 0
if 'teacher_mode' not in st.session_state:
    st.session_state.teacher_mode = False
if 'iupac_model' not in st.session_state:
    st.session_state.iupac_model = None
if 'iupac_tokenizer' not in st.session_state:
    st.session_state.iupac_tokenizer = None


# ----------------- Enhanced Voice Functions -----------------
def speak(text, language='si', wait=False):
    """Convert text to speech and play it immediately"""
    tts = gTTS(text=text, lang=language)
    fp = BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    
    # Play audio
    audio_bytes = fp.read()
    b64 = base64.b64encode(audio_bytes).decode()
    md = f"""
        <audio autoplay {'controls' if not wait else ''}>
        <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
        </audio>
        """
    st.markdown(md, unsafe_allow_html=True)
    
    # Add delay if needed
    if wait:
        time.sleep(len(text.split()) * 0.3)  # Approximate speaking time

def transcribe_audio(timeout=10, max_retries=2):
    """Convert spoken Sinhala to text using Google's speech recognition with retry"""
    r = sr.Recognizer()
    retry_count = 0
    
    while retry_count <= max_retries:
        try:
            with sr.Microphone() as source:
                st.session_state.listening = True
                speak("Listening... Speak now", 'en')
                try:
                    audio = r.listen(source, timeout=timeout)
                except sr.WaitTimeoutError:
                    speak("No speech detected. Please try again.", 'en')
                    retry_count += 1
                    st.session_state.retry_count = retry_count
                    continue
                finally:
                    st.session_state.listening = False
                
                try:
                    text = r.recognize_google(audio, language='si-LK')
                    return text
                except sr.UnknownValueError:
                    speak("Could not understand audio. Please try again.", 'en')
                except sr.RequestError as e:
                    speak(f"Speech recognition error: {str(e)}", 'en')
            break
        except Exception as e:
            speak(f"Error: {str(e)}", 'en')
            retry_count += 1
            st.session_state.retry_count = retry_count
    
    return ""

def describe_molecule(smiles):
    """Generate a verbal description of a molecule"""
    prompt = f"""
    You are a chemistry assistant for blind students. 
    Describe the molecular structure of the compound with SMILES: {smiles}
    in a way that a blind person could visualize it. Include:
    - The type of molecule (organic, inorganic, etc.)
    - Key functional groups
    - Shape and geometry
    - Notable atoms and their arrangements
    - Any special characteristics
    
    Respond in Sinhala.
    """
    
    model = genai.GenerativeModel('gemini-2.5-flash')
    response = model.generate_content(prompt)
    return response.text.strip()

# ----------------- Navigation Functions for Blind Students -----------------
def navigate_app():
    """Voice-based navigation system for blind students"""
    speak("Accessibility mode activated. You can now navigate by voice.", 'en')
    time.sleep(1)
    speak("Say 'chat' for chemistry questions, 'quiz' for practice questions, 'molecules' for molecular visualizer, or 'help' for assistance.", 'en')
    
    command = transcribe_audio(timeout=8, max_retries=1)
    if not command:
        return  # Return if no command was recognized
        
    command = command.lower()
    
    if 'chat' in command:
        st.session_state.current_tab = "Chat"
        speak("Opening chemistry chat. You can ask questions about chemistry.", 'si')
    elif 'quiz' in command or 'practice' in command:
        st.session_state.current_tab = "Quizzes"
        speak("Opening quizzes. Say 'generate quiz' to start a new practice session.", 'si')
    elif 'mole' in command or 'visual' in command:
        st.session_state.current_tab = "Simulations"
        speak("Opening molecular visualizer. Say a compound name like 'water' or 'benzene' to learn about its structure.", 'si')
    elif 'help' in command:
        speak("Available commands: 'chat', 'quiz', 'molecules', 'exit accessibility mode'.", 'en')
    elif 'exit' in command or 'close' in command:
        st.session_state.accessibility_mode = False
        speak("Exiting accessibility mode.", 'en')
    else:
        speak("Command not recognized. Please try again.", 'en')

# ----------------- Existing App Functions (Slightly Modified) -----------------
def get_pdf_text(pdf_docs):
    text = ""
    for pdf in pdf_docs:
        pdf_reader = PdfReader(pdf)
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text

def get_text_chunks(text):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=10000, chunk_overlap=1000)
    chunks = text_splitter.split_text(text)
    return chunks

def get_vector_store(text_chunks):
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vector_store = FAISS.from_texts(text_chunks, embedding=embeddings)
    vector_store.save_local("faiss_index")

def get_smiles_from_name(compound_name: str) -> str:
    prompt = f"""
    You are a chemistry expert. Convert this chemical name to SMILES notation.
    Follow these rules STRICTLY:
    1. Return ONLY the SMILES string
    2. No explanations
    3. Use standard SMILES syntax
    4. For Sinhala names: FIRST translate to English, THEN convert to SMILES
    
    Input: {compound_name}
    SMILES: 
    """
    
    model = genai.GenerativeModel('gemini-2.5-flash')
    response = model.generate_content(prompt)
    return response.text.strip().split()[0]

def visualize_molecule(smiles: str):
    try:
        from rdkit import Chem
        from rdkit.Chem import Draw
        from rdkit.Chem.Draw import MolDrawOptions
        
        mol = Chem.MolFromSmiles(smiles)
        if not mol:
            raise ValueError("Invalid SMILES string")
            
        opts = MolDrawOptions()
        opts.bondLineWidth = 2
        opts.atomLabelFontSize = 14
        
        img = Draw.MolToImage(mol, size=(400, 300), options=opts)
        return img
        
    except Exception as e:
        st.error(f"Visualization failed: {str(e)}")
        return None

def generate_quiz_questions(text_chunks, num_questions=5):
    quiz_prompt = """
    Generate {num_questions} multiple-choice chemistry questions in Sinhala from this text.
    Focus on DIFFERENT TOPICS each time. Format as:
    'Q:: [question] | A:: [correct] | B:: [wrong1] | C:: [wrong2] | D:: [wrong3]'
    Text: {context}
    """
    
    model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.7)
    questions = []
    
    random.shuffle(text_chunks)
    selected_chunks = random.sample(text_chunks, min(3, len(text_chunks)))
    
    for chunk in selected_chunks:
        prompt = quiz_prompt.format(num_questions=num_questions//3, context=chunk)
        response = model.invoke([{"role": "user", "content": prompt}])
        if response.content:
            new_questions = [q.strip() for q in response.content.split('Q:: ') if q.strip()]
            questions.extend(f'Q:: {q}' for q in new_questions if '| A:: ' in q)
    
    random.shuffle(questions)
    return questions[:num_questions]

def get_conversational_chain():
    prompt_template = """
    You are a helpful assistant that responds in Sinhala and specializes in chemistry. 
    - Always mention chemical compound names explicitly (e.g., "benzene" or "C₆H₆") when relevant.
    - Provide detailed verbal descriptions suitable for blind students when discussing molecular structures.
    - Use the context to answer. If the answer isn't in the context, say "answer is not available in the context".
    - If asked to explain something again or provide more details, use your chemistry knowledge to expand on the topic.

    Chat History:
    {chat_history}

    Context:
    {context}

    Question: {question}

    Answer in Sinhala:
    """

    model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.3)
    memory = ConversationBufferMemory(memory_key="chat_history", input_key="question")
    
    prompt = PromptTemplate(
        template=prompt_template,
        input_variables=["context", "question", "chat_history"]
    )
    
    chain = load_qa_chain(
        model,
        chain_type="stuff",
        prompt=prompt,
        memory=memory,
        verbose=True
    )
    return chain

def process_question(user_question):
    """Process a question with enhanced accessibility features"""
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    new_db = FAISS.load_local("faiss_index", embeddings, allow_dangerous_deserialization=True)
    docs = new_db.similarity_search(user_question)
    
    chain = get_conversational_chain()
    response = chain(
        {"input_documents": docs, "question": user_question},
        return_only_outputs=True
    )
    
    response_text = response["output_text"]
    
    # Speak the response immediately for blind students
    if st.session_state.accessibility_mode:
        speak(response_text, 'si')
    
    # Handle molecular descriptions
    if "structure" in response_text.lower() or "SMILES" in response_text:
        try:
            smiles = response_text.split()[-1].strip("[]()")
            if st.session_state.accessibility_mode:
                # Generate verbal description for blind students
                description = describe_molecule(smiles)
                speak("Here's a description of the molecular structure:", 'en')
                speak(description, 'si')
            else:
                img = visualize_molecule(smiles)
                if img:
                    st.image(img, caption=f"Structure of {smiles}")
        except:
            pass
    
    return response_text

def main():
    st.set_page_config(
        "Chemistry Learning App", 
        layout="wide",
        page_icon="🧪"
    )
    
    # Apply custom CSS for modern UI
    try:
        with open("assets/styles.css", "r", encoding="utf-8") as css_file:
            st.markdown(f"<style>{css_file.read()}</style>", unsafe_allow_html=True)
    except Exception:
        pass
    
    # Initialize session states
    if 'text_chunks' not in st.session_state:
        st.session_state.text_chunks = []
    if 'auto_play' not in st.session_state:
        st.session_state.auto_play = True
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'current_question' not in st.session_state:
        st.session_state.current_question = ""
    if 'retry_count' not in st.session_state:
        st.session_state.retry_count = 0
    if 'quiz' not in st.session_state:
        st.session_state.quiz = {
            'questions': [],
            'user_answers': [None] * 3,
            'submitted': False
        }
    
    # Accessibility mode activation
    # if st.session_state.first_run:
    #     speak("Welcome to the Chemistry Self-Study App. Press the accessibility button to enable voice navigation.", 'en')
    #     st.session_state.first_run = False
    
    # Main header
    st.markdown("""
    <div class="header">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <h1>Chemistry Learning App</h1>
                <div class="subtitle">Interactive Chemistry Education for Sri Lankan Students</div>
            </div>
            <div style="display: flex; gap: 10px;">
                <span class="badge">AI-Powered</span>
                <span class="badge">Sinhala Support</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Accessibility toggle
    with st.container():
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("♿ Enable Accessibility Mode" if not st.session_state.accessibility_mode else "♿ Disable Accessibility Mode",
                        use_container_width=True, 
                        type="primary" if not st.session_state.accessibility_mode else "secondary"):
                st.session_state.accessibility_mode = not st.session_state.accessibility_mode
                if st.session_state.accessibility_mode:
                    st.session_state.retry_count = 0
                    st.rerun()
    
    # Skip rendering tabs in accessibility mode
    if st.session_state.accessibility_mode:
        # Handle tab-specific functionality through voice commands
        if st.session_state.current_tab == "Chat":
            speak("You are in the chat tab. Ask a chemistry question.", 'si')
            user_question = transcribe_audio(timeout=15, max_retries=1)
            if user_question:
                response = process_question(user_question)
                st.session_state.chat_history.append({"role": "user", "content": user_question})
                st.session_state.chat_history.append({"role": "assistant", "content": response})
                # Return to navigation
                speak("Question answered. Say 'navigate' to go to another section.", 'en')
                time.sleep(1)
                st.session_state.current_tab = "Chat"
            else:
                speak("No question detected. Returning to navigation.", 'en')
            navigate_app()
        
        elif st.session_state.current_tab == "Quizzes":
            speak("You are in the quizzes tab. Say 'generate quiz' to start.", 'si')
            command = transcribe_audio(timeout=8, max_retries=1)
            
            if command and 'generate' in command.lower():
                with st.spinner("Creating questions..."):
                    if 'text_chunks' in st.session_state and st.session_state.text_chunks:
                        questions = generate_quiz_questions(st.session_state.text_chunks, num_questions=3)
                        speak("Quiz generated. I will ask you 3 questions.", 'si')
                        
                        score = 0
                        for i, q_data in enumerate(questions):
                            parts = q_data.split('|')
                            question_text = parts[0].replace('Q:: ', '')
                            options = [p.split(':: ')[1] for p in parts[1:]]
                            
                            speak(f"Question {i+1}: {question_text}", 'si')
                            speak("Options:", 'si')
                            for j, option in enumerate(options):
                                speak(f"{chr(65+j)}: {option}", 'si')
                            
                            answer = transcribe_audio(timeout=12, max_retries=1)
                            correct_answer = parts[1].split(':: ')[1]
                            
                            if answer and any(char in answer.upper() for char in ['A', 'B', 'C', 'D']):
                                selected_char = next((char for char in ['A', 'B', 'C', 'D'] if char in answer.upper()), '')
                                selected_index = ord(selected_char) - 65
                                selected_answer = options[selected_index] if 0 <= selected_index < len(options) else ""
                                
                                if selected_answer == correct_answer:
                                    score += 1
                                    speak("Correct! ✅", 'si')
                                else:
                                    speak(f"Wrong. The correct answer is: {correct_answer} ❌", 'si')
                            else:
                                speak(f"Answer not recognized. The correct answer is: {correct_answer}", 'si')
                        
                        speak(f"You scored {score} out of {len(questions)}", 'si')
                        if score == len(questions):
                            speak("Excellent work! 🎉", 'si')
                        elif score >= len(questions)/2:
                            speak("Good effort! 👍", 'si')
                        else:
                            speak("Keep practicing! You'll improve. 📚", 'si')
            
            # Return to navigation
            speak("Quiz completed. Say 'navigate' to go to another section.", 'en')
            time.sleep(1)
            navigate_app()
        
        elif st.session_state.current_tab == "Simulations":
            speak("Say the name of a chemical compound to learn about its structure.", 'si')
            compound_name = transcribe_audio(timeout=12, max_retries=1)
            
            if compound_name:
                try:
                    speak(f"Processing {compound_name}...", 'en')
                    smiles = get_smiles_from_name(compound_name)
                    speak(f"The SMILES notation is: {smiles}", 'en')
                    
                    # Generate verbal description
                    description = describe_molecule(smiles)
                    speak(f"Description of {compound_name}:", 'en')
                    speak(description, 'si')
                    
                except Exception as e:
                    speak(f"Error: {str(e)}. Try another name.", 'en')
            
            # Return to navigation
            speak("Molecule described. Say 'navigate' to go to another section.", 'en')
            time.sleep(1)
            navigate_app()
        
        else:
            # Start navigation
            navigate_app()
            st.rerun()
        
        return
    
    # ----------------- Modern Visual Interface -----------------
    # Add tabs with icons
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs(["💬 Chat Assistant", "📝 Chemistry Quizzes", "🧬 Molecular Explorer", "🔬 Virtual Labs", "📚 Mock Exams","🧪 IUPAC Practice", "🧪 Smart Periodic Table","📸 Screenshot Solver"])

    with tab1:
        st.markdown("""
        <div class="card">
            <div class="card-title">
                Chemistry Chat Assistant
            </div>
            <p>Ask questions about chemistry in Sinhala or English. Our AI assistant will provide detailed explanations.</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""<div style="margin-bottom: 20px;"></div>""", unsafe_allow_html=True)
        teacher_mode = st.toggle(
        "සිංහල රසායන විද්‍යා ගුරු මාදිලිය (Sinhala Chemistry Teacher Mode)",
        value=st.session_state.teacher_mode,
        help="Get step-by-step explanations in Sinhala from our AI chemistry teacher"
        )

        # Update session state
        if teacher_mode != st.session_state.teacher_mode:
            st.session_state.teacher_mode = teacher_mode
            st.rerun()




        col1, col2 = st.columns([3, 1])
        with col1:
            # Display chat history in styled containers
            chat_container = st.container(height=400)
            with chat_container:
                for message in st.session_state.chat_history:
                    if message["role"] == "user":
                        st.markdown(f"""
                        <div class="chat-message-user">
                            <strong>You:</strong> {message["content"]}
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        # Add teacher mode class when applicable
                        teacher_class = "teacher-mode-active" if st.session_state.teacher_mode else ""
            
                        st.markdown(f"""
                        <div class="chat-message-assistant {teacher_class}">
                            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 5px;">
                                <div style="font-size: 1.2rem;">{'👨‍🏫' if st.session_state.teacher_mode else '🧪'}</div>
                                <strong>{'රසායන ගුරුවරයා' if st.session_state.teacher_mode else 'Assistant'}:</strong>
                            </div>
                            {message["content"]}
                        </div>
                        """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div class="card">
                <div class="card-title">
                    Chemistry Topics
                </div>
                <ul style="padding-left: 20px;">
                    <li>Organic Chemistry</li>
                    <li>Inorganic Chemistry</li>
                    <li>Physical Chemistry</li>
                    <li>Analytical Chemistry</li>
                    <li>Biochemistry</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("""
            <div class="card">
                <div class="card-title">
                    Try Asking
                </div>
                <ul style="padding-left: 20px;">
                    <li>What is the structure of benzene?</li>
                    <li>Explain chemical bonding</li>
                    <li>What is a mole concept?</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
        
        # Input area
        with st.container():
            col_input, col_voice = st.columns([5, 1])
            with col_input:
                user_question = st.chat_input(
                    "Ask a chemistry question...", 
                    key="chat_input"
                )
            
            with col_voice:
                if st.button("🎤 Voice", use_container_width=True, help="Ask by voice"):
                    with st.spinner("Listening..."):
                        user_question = transcribe_audio()
                        if user_question:
                            st.session_state.current_question = user_question
                            st.rerun()
        
        # Use voice input if available
        if st.session_state.current_question:
            user_question = st.session_state.current_question
            st.session_state.current_question = ""
        
        
        if user_question:
            st.session_state.chat_history.append({"role": "user", "content": user_question})
        
            with st.spinner("ඔබගේ ප්‍රශ්නය විශ්ලේෂණය කරමින්..." if st.session_state.teacher_mode 
                      else "Analyzing your question..."):
                if st.session_state.teacher_mode:
                # Use the new Sinhala teacher mode
                    response = get_step_by_step_answer(user_question)
                else:
                # Existing PDF-based processing
                    response = process_question(user_question)
                
            st.session_state.chat_history.append({"role": "assistant", "content": response})
            st.rerun()

    # ----------------- Chemistry Quizzes Tab -----------------

    with tab2:
        st.markdown("""
        <div class="card">
            <div class="card-title">
                Chemistry Quizzes
            </div>
            <p>Test your knowledge with adaptive quizzes generated from your study materials.</p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns([2, 1])
        with col1:
            # Quiz generation card
            with st.container():
                st.markdown("""
                <div class="card">
                    <div class="card-title">
                        Generate New Quiz
                    </div>
                """, unsafe_allow_html=True)
                
                col_gen, col_info = st.columns([1, 2])
                with col_gen:
                    if st.button("Create Quiz", use_container_width=True):
                        with st.spinner("Creating questions..."):
                            if 'text_chunks' in st.session_state and st.session_state.text_chunks:
                                questions = generate_quiz_questions(st.session_state.text_chunks, num_questions=3)
                                correct_answers = []
                                for q in questions:
                                    parts = q.split('|')
                                    correct_answers.append(parts[1].split(':: ')[1])
                                
                                st.session_state.quiz = {
                                    'questions': questions,
                                    'correct_answers': correct_answers,
                                    'user_answers': [None] * len(questions),
                                    'submitted': False
                                }
                                st.success("Quiz created successfully!")
                
                with col_info:
                    st.info("ℹ️ Quizzes are automatically generated based on chemistry topics. You can upload your own materials in the sidebar.")
                
                st.markdown("</div>", unsafe_allow_html=True)
            
            # Quiz display
            if st.session_state.quiz['questions']:
                st.markdown("""
                <div class="card">
                    <div class="card-title">
                        Current Quiz
                    </div>
                """, unsafe_allow_html=True)
                
                with st.form("quiz_form"):
                    for i, q_data in enumerate(st.session_state.quiz['questions']):
                        parts = q_data.split('|')
                        st.markdown(f"""
                        <div class="quiz-question">
                            <h4>Question {i+1}</h4>
                            <p>{parts[0].replace('Q:: ', '')}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        options = [p.split(':: ')[1] for p in parts[1:]]
                        
                        st.session_state.quiz['user_answers'][i] = st.radio(
                            f"Select your answer for question {i+1}:",
                            options,
                            key=f"q{i}",
                            index=None,
                            label_visibility="collapsed"
                        )
                    
                    submitted = st.form_submit_button("✅ Submit Answers", use_container_width=True)
                    if submitted:
                        st.session_state.quiz['submitted'] = True
                
                st.markdown("</div>", unsafe_allow_html=True)
                
                if st.session_state.quiz['submitted']:
                    score = 0
                    results = []
                    
                    for i in range(len(st.session_state.quiz['questions'])):
                        user_answer = st.session_state.quiz['user_answers'][i]
                        correct_answer = st.session_state.quiz['correct_answers'][i]
                        
                        if user_answer == correct_answer:
                            score += 1
                            results.append(f"✅ Question {i+1}: Correct!")
                        else:
                            results.append(f"❌ Question {i+1}: Wrong! Correct answer: {correct_answer}")
                    
                    st.balloons()
                    
                    # Results card
                    with st.container():
                        st.markdown(f"""
                        <div class="card" style="background: {'#d4edda' if score > 1 else '#f8d7da'};">
                            <h3>Quiz Results: {score}/{len(st.session_state.quiz['questions'])}</h3>
                            <p>{'🌟 Excellent! You aced the quiz!' if score == len(st.session_state.quiz['questions']) else 
                                '👍 Good job! You passed the quiz.' if score >= len(st.session_state.quiz['questions'])/2 else 
                                '📚 Keep practicing! Review the material and try again.'}</p>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Detailed results
                    with st.expander("📝 See detailed results"):
                        for result in results:
                            st.write(result)
        
        with col2:
            st.markdown("""
            <div class="card">
                <div class="card-title">
                    Your Progress
                </div>
                <div style="text-align: center; padding: 1rem;">
                    <div style="font-size: 3rem; font-weight: 700; color: #4a86e8; margin: 1rem 0;">72%</div>
                    <div style="height: 12px; background: #e0e0e0; border-radius: 6px; margin: 1rem 0;">
                        <div style="height: 100%; width: 72%; background: #4a86e8; border-radius: 6px;"></div>
                    </div>
                    <p>Overall mastery of chemistry concepts</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("""
            <div class="card">
                <div class="card-title">
                    Quiz Statistics
                </div>
                <div style="padding: 1rem;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                        <span>Quizzes Taken:</span>
                        <span><strong>14</strong></span>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                        <span>Average Score:</span>
                        <span><strong>68%</strong></span>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                        <span>Highest Score:</span>
                        <span><strong>92%</strong></span>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <span>Topics Mastered:</span>
                        <span><strong>5/12</strong></span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    with tab3:
        st.markdown("""
        <div class="card">
            <div class="card-title">
                Molecular Explorer
            </div>
            <p>Explore chemical structures and properties. Enter a compound name in English or Sinhala.</p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            # Compound input card
            with st.container():
                st.markdown("""
                <div class="card">
                    <div class="card-title">
                        Search Compound
                    </div>
                """, unsafe_allow_html=True)
                
                compound_name = st.text_input(
                    "Enter chemical name (English/Sinhala):",
                    placeholder="e.g. Benzene or බෙන්සීන්",
                    key="mol_input",
                    label_visibility="collapsed"
                )
                
                col_voice, col_search = st.columns([1, 2])
                with col_voice:
                    if st.button("🎤 Voice", key="mol_voice", use_container_width=True):
                        with st.spinner("Listening..."):
                            spoken_name = transcribe_audio()
                            if spoken_name:
                                compound_name = spoken_name
                                st.rerun()
                
                with col_search:
                    if st.button("Search", use_container_width=True):
                        st.rerun()
                
                st.markdown("</div>", unsafe_allow_html=True)
            
            # Examples card
            with st.container():
                st.markdown("""
                <div class="card">
                    <div class="card-title">
                        Popular Compounds
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin-top: 1rem;">
                """, unsafe_allow_html=True)
                
                examples = [
                    {"name": "Water | ජලය", "formula": "H₂O"},
                    {"name": "Ethanol | එතනෝල්", "formula": "C₂H₅OH"},
                    {"name": "Benzene | බෙන්සීන්", "formula": "C₆H₆"},
                    {"name": "Glucose | ග්ලූකෝස්", "formula": "C₆H₁₂O₆"}
                ]
                
                for example in examples:
                    if st.button(f"{example['name']}\n{example['formula']}", use_container_width=True):
                        compound_name = example['name'].split("|")[0].strip()
                        st.rerun()
                
                st.markdown("</div></div>", unsafe_allow_html=True)
        
        with col2:
            # Results display
            if compound_name:
                with st.spinner(f"Processing {compound_name}..."):
                    try:
                        smiles = get_smiles_from_name(compound_name)
                        
                        # Results card
                        with st.container():
                            st.markdown(f"""
                            <div class="molecule-card">
                                <h3 style="margin-top: 0;">{compound_name}</h3>
                                <div style="font-size: 1.2rem; margin-bottom: 1rem;"><code>{smiles}</code></div>
                            """, unsafe_allow_html=True)
                            
                            img = visualize_molecule(smiles)
                            if img:
                                st.image(img, caption=f"Structure of {compound_name}", use_column_width=True)
                            
                            # Generate and display description
                            description = describe_molecule(smiles)
                            with st.expander("Molecular Description", expanded=True):
                                st.write(description)
                            
                            # Add audio description button
                            if st.button("🔊 Hear Description", use_container_width=True):
                                speak(description, 'si')
                            
                            st.markdown("</div>", unsafe_allow_html=True)
                    
                    except Exception as e:
                        st.error(f"Error: {str(e)}. Try another name.")
            else:
                # Placeholder for molecule visualization
                with st.container():
                    st.markdown("""
                    <div class="molecule-card" style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 400px;">
                        <div style="font-size: 5rem; margin-bottom: 1rem;">🧪</div>
                        <h3>Explore Molecules</h3>
                        <p>Enter a compound name to visualize its structure</p>
                    </div>
                    """, unsafe_allow_html=True)
    
    with tab4:
        # Show PHET simulations or a placeholder if not implemented
        #phet_simulations.show_phet_simulations()
        show_guided_labs()
        
    with tab5:
        show_mock_exams()

    
    with tab6:
        st.markdown("""
        <div class="card">
            <div class="card-title">
                IUPAC Nomenclature Practice
            </div>
            <p>Practice organic chemistry naming conventions with AI assistance</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Load model on first use
        if st.session_state.iupac_model is None:
            with st.spinner("Loading IUPAC model..."):
                try:
                    st.session_state.iupac_tokenizer, st.session_state.iupac_model = load_iupac_model()
                    st.success("IUPAC model loaded successfully!")
                except Exception as e:
                    st.error(f"Error loading model: {str(e)}")
                    st.session_state.iupac_model = "error"
        
        col1, col2 = st.columns([4, 1])
        with col1:
            iupac_question = st.text_input(
                "Ask an IUPAC nomenclature question:",
                placeholder="e.g. Name this compound: CH3-CH2-OH",
                key="iupac_question"
            )
        
        with col2:
            if st.button("🎤 Voice", key="iupac_voice"):
                with st.spinner("Listening..."):
                    spoken_question = transcribe_audio()
                    if spoken_question:
                        iupac_question = spoken_question
                        st.rerun()
        
        if iupac_question:
            if st.session_state.iupac_model == "error":
                st.error("IUPAC model failed to load. Please check the model files.")
            elif st.session_state.iupac_model:
                with st.spinner("Analyzing your question..."):
                    try:
                        # Get English response from DeepSeek
                        english_response = get_iupac_response(
                            iupac_question,
                            st.session_state.iupac_tokenizer,
                            st.session_state.iupac_model
                        )
                        
                        # Translate to Sinhala
                        sinhala_response = translate_to_sinhala(english_response)
                        
                        # Display response
                        st.markdown(f"""
                        <div class="chat-message-assistant">
                            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 5px;">
                                <div style="font-size: 1.2rem;">🧪</div>
                                <strong>IUPAC Assistant:</strong>
                            </div>
                            {sinhala_response}
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Voice output
                        speak(sinhala_response, 'si')
                        
                        # Optionally show English version
                        with st.expander("See English version"):
                            st.write(english_response)
                    
                    except Exception as e:
                        st.error(f"Error processing question: {str(e)}")

    with tab7:
        show_smart_table()

    with tab8:
        st.markdown("""
        <div class="card">
            <div class="card-title">
                📸 Screenshot Question Solver
            </div>
            <p>Upload a screenshot of your chemistry question and get instant answers!</p>
        </div>
        """, unsafe_allow_html=True)
    
        col1, col2 = st.columns([2, 1])

        with col1:
        # Screenshot upload section
            with st.container():
                st.markdown("""
                <div class="card">
                    <div class="card-title">
                        Upload Question Screenshot
                    </div>
                """, unsafe_allow_html=True)
            
                uploaded_image = st.file_uploader(
                    "Choose an image file",
                    type=['png', 'jpg', 'jpeg', 'webp'],
                    key="screenshot_uploader",
                    label_visibility="collapsed"
                )
            
                # Teacher mode toggle for screenshot solver
                screenshot_teacher_mode = st.toggle(
                    "සිංහල රසායන විද්‍යා ගුරු මාදිලිය (Screenshot Mode)",
                    value=st.session_state.teacher_mode,
                    key="screenshot_teacher_mode",
                    help="Get step-by-step explanations in Sinhala for screenshot questions"
                )
            
                st.markdown("</div>", unsafe_allow_html=True)
        
            # Display uploaded image and process
            if uploaded_image is not None:
                # Display the image
                image = Image.open(uploaded_image)
                st.image(image, caption="Uploaded Question", use_column_width=True)
            
                # Process button
                if st.button("🔍 Analyze and Solve", use_container_width=True):
                    answer = process_screenshot(image, screenshot_teacher_mode)
                
                    # Display answer
                    st.markdown("""
                    <div class="card">
                        <div class="card-title">
                            📝 Answer
                        </div>
                    """, unsafe_allow_html=True)
                
                    # Add teacher mode class when applicable
                    teacher_class = "teacher-mode-active" if screenshot_teacher_mode else ""

                    st.markdown(f"""
                    <div class="chat-message-assistant {teacher_class}">
                        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 5px;">
                            <div style="font-size: 1.2rem;">{'👨‍🏫' if screenshot_teacher_mode else '🧪'}</div>
                            <strong>{'රසායන ගුරුවරයා' if screenshot_teacher_mode else 'Assistant'}:</strong>
                        </div>
                        {answer}
                    </div>
                    """, unsafe_allow_html=True)
                
                    st.markdown("</div>", unsafe_allow_html=True)

        with col2:
            # Instructions and tips
            st.markdown("""
            <div class="card">
                <div class="card-title">
                    💡 Tips for Best Results
                </div>
                <ul style="padding-left: 20px;">
                    <li>Use clear, well-lit images</li>
                    <li>Ensure text is readable</li>
                    <li>Crop to the question area</li>
                    <li>Supported formats: PNG, JPG, JPEG</li>
                    <li>Works with handwritten text</li>
                    <li>Supports chemical formulas</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
        
            st.markdown("""
            <div class="card">
                <div class="card-title">
                    🎯 Supported Question Types
                </div>
                <ul style="padding-left: 20px;">
                    <li>Multiple choice questions</li>
                    <li>Calculation problems</li>
                    <li>Chemical equations</li>
                    <li>Structure identification</li>
                    <li>Theory questions</li>
                    <li>Mechanism problems</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
        
            # Quick examples
            st.markdown("""
            <div class="card">
                <div class="card-title">
                    🚀 Quick Start
                </div>
                <p>Take a screenshot of questions from:</p>
                <ul style="padding-left: 20px;">
                    <li>Textbook PDFs</li>
                    <li>Online quizzes</li>
                    <li>Past papers</li>
                    <li>Homework assignments</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)


    # Sidebar with PDF upload
    with st.sidebar:
        st.markdown("""
        <div class="card">
            <div class="card-title">
                Study Materials
            </div>
            <p>Upload your chemistry materials for personalized learning</p>
        """, unsafe_allow_html=True)
        
        pdf_docs = st.file_uploader(
            "Upload PDF files", 
            accept_multiple_files=True,
            type=["pdf"],
            label_visibility="collapsed"
        )
        
        if st.button("⚙️ Process Documents", use_container_width=True):
            with st.spinner("Processing..."):
                if pdf_docs:
                    raw_text = get_pdf_text(pdf_docs)
                    text_chunks = get_text_chunks(raw_text)
                    st.session_state.text_chunks = text_chunks
                    get_vector_store(text_chunks)
                    st.success("Documents processed successfully!")
                    if st.session_state.accessibility_mode:
                        speak("PDF processing complete. You can now ask questions about the documents.", 'en')
                else:
                    st.warning("Please upload at least one PDF file")
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Recent Activity
        st.markdown("""
        <div class="card">
            <div class="card-title">
                Recent Activity
            </div>
            <div style="padding: 0.5rem;">
                <div style="display: flex; align-items: start; margin-bottom: 1rem;">
                    <div style="background: #e3f2fd; border-radius: 50%; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; margin-right: 10px;">💬</div>
                    <div>
                        <div><strong>Chemistry Chat</strong></div>
                        <div style="font-size: 0.9rem; color: #666;">Asked about chemical bonds</div>
                        <div style="font-size: 0.8rem; color: #999;">2 hours ago</div>
                    </div>
                </div>
                <div style="display: flex; align-items: start; margin-bottom: 1rem;">
                    <div style="background: #f1f8e9; border-radius: 50%; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; margin-right: 10px;">📝</div>
                    <div>
                        <div><strong>Organic Chemistry Quiz</strong></div>
                        <div style="font-size: 0.9rem; color: #666;">Scored 80%</div>
                        <div style="font-size: 0.8rem; color: #999;">Yesterday</div>
                    </div>
                </div>
                <div style="display: flex; align-items: start;">
                    <div style="background: #e6f7ff; border-radius: 50%; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; margin-right: 10px;">🧬</div>
                    <div>
                        <div><strong>Molecular Explorer</strong></div>
                        <div style="font-size: 0.9rem; color: #666;">Viewed ethanol structure</div>
                        <div style="font-size: 0.8rem; color: #999;">2 days ago</div>
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # App info card
        st.markdown("""
        <div class="card">
            <div class="card-title">
                About This App
            </div>
            <p><strong>Chemistry Learning Assistant</strong><br>
            An AI-powered app for chemistry education with:</p>
            <ul>
                <li>Interactive chat assistant</li>
                <li>Adaptive quizzes</li>
                <li>Molecular visualization</li>
                <li>Full accessibility features</li>
            </ul>
            <p>Developed with ❤️ for students in Sri Lanka</p>
            <div style="border-top: 1px solid #eee; margin: 1rem 0; padding-top: 1rem; font-size: 0.9rem; color: #666;">
                Version 2.1 | Powered by Gemini AI
            </div>
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()