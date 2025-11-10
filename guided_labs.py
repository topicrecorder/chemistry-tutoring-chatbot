import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Mock helper functions (these exist in app.py)
def get_gemini_response(prompt):
    """Mock function - real one exists in app.py"""
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI response error: {str(e)}"

def speak(text, lang):
    """Mock TTS function - real one exists in app.py"""
    st.info(f"🔊 TTS would speak: {text[:100]}...")

def set_quiz_topic(topic):
    """Mock quiz function - real one exists in app.py"""
    st.session_state.current_quiz_topic = topic
    st.success(f"Quiz topic set to: {topic}")

# Guided Labs Data Structure
GUIDED_LABS = {
    "acids_bases": {
        "topic_id": "acids_bases",
        "title_sinhala": "🧪 අම්ල සහ භෂ්ම",
        "objectives_sinhala": [
            "ප්‍රබල සහ දුබල අම්ල/භෂ්ම අතර වෙනස පැහැදිලි කිරීමට.",
            "pH අගය සහ සාන්ද්‍රණය අතර සම්බන්ධය හඳුනා ගැනීමට.",
            "අනුමාපනයක් (titration) යනු කුමක්දැයි අවබෝධ කර ගැනීමට."
        ],
        "pre_lab_audio_prompt": "You are a friendly chemistry teacher. In simple Sinhala, give a 2-minute audio lesson introducing a self-studying A-level student to the concepts of acids, bases, strong vs. weak, pH, and titration.",
        
        "phet_tab": {
            "title_sinhala": "แนวคิด ගවේෂණය (PhET)",
            "embed_url": "https://phet.colorado.edu/sims/html/acid-base-solutions/latest/acid-base-solutions_en.html",
            "guided_questions_sinhala": [
                "PhET සිමියුලේෂනය 'ජලය' (Water) ට සකසන්න. pH අගය කීයද?",
                "දැන් 'ප්‍රබල අම්ලයක්' (Strong Acid) තෝරන්න. ජලයේ දියවූ විට, අණු 100% ක්ම අයන වලට විඝටනය වන බව ඔබට පෙනේද?",
                "'දුබල අම්ලයක්' (Weak Acid) තෝරන්න. මෙහිදී අණු සියල්ලම විඝටනය වේද? නැතහොත් සමතුලිතතාවයක් (equilibrium) පවතීද?",
                "ද්‍රාවණයට ජලය එකතු කළ විට pH අගයට කුමක් සිදුවේද? එය 'තනුක වීම' (dilution) ලෙස හැඳින්වේ."
            ]
        },
        
        "chem_tab": {
            "title_sinhala": "ක්‍රියාකාරකම (ChemCollective)",
            "embed_url": "http://chemcollective.org/vlab/100",
            "goal_sinhala": "ඔබේ ඉලක්කය: 0.1M NaOH (ප්‍රබල භෂ්මයක්) භාවිතයෙන්, නොදන්නා HCl (ප්‍රබල අම්ලයක) සාන්ද්‍රණය සොයා ගැනීමට අනුමාපනයක් සිදු කරන්න. බියුරෙට්ටුවට NaOH ද, කේතුකාකාර ප්ලාස්කුවට HCl දමා, දර්ශකයක් (indicator) එක් කරන්න."
        },
        
        "lab_assistant_prompt": "You are a helpful chemistry lab assistant, speaking fluently in Sinhala. The student is currently working on the 'Acids and Bases' guided lab. They are looking at both a PhET conceptual sim and a ChemCollective titration practical. Answer their questions directly related to this lab, helping them connect the PhET concepts (like pH, dissociation) to the ChemCollective practical (like titration, molarity calculations).",
        "quiz_topic": "Acids and Bases"
    },
    
    "gases": {
        "topic_id": "gases",
        "title_sinhala": "💨 වායු",
        "objectives_sinhala": [
            "වායුවක පීඩනය (P), පරිමාව (V), සහ උෂ්ණත්වය (T) අතර සම්බන්ධය ගවේෂණය කිරීමට.",
            "බොයිල්, චාල්ස්, සහ ගේ-ලුසැක නියම අවබෝධ කර ගැනීමට."
        ],
        "pre_lab_audio_prompt": "You are a friendly chemistry teacher. In simple Sinhala, give a 2-minute audio lesson introducing a self-studying A-level student to the Gas Laws (Boyle's Law, Charles's Law) and the variables of Pressure, Volume, and Temperature.",
        
        "phet_tab": {
            "title_sinhala": "แนวคิด ගවේෂණය (PhET)",
            "embed_url": "https://phet.colorado.edu/sims/html/gas-properties/latest/gas-properties_en.html",
            "guided_questions_sinhala": [
                "පරිමාව (V) නියතව තබා, පද්ධතිය රත් කරන්න (T වැඩි කරන්න). පීඩනයට (P) කුමක් සිදුවේද?",
                "උෂ්ණත්වය (T) නියතව තබා, පරිමාව (V) අඩු කරන්න. පීඩනය (P) වෙනස් වන්නේ කෙසේද? මෙය බොයිල් නියමයද?",
                "පීඩනය (P) නියතව තබා, පද්ධතිය සිසිල් කරන්න (T අඩු කරන්න). පරිමාවට (V) කුමක් සිදුවේද? මෙය චාල්ස් නියමයද?"
            ]
        },
        
        "chem_tab": {
            "title_sinhala": "ක්‍රියාකාරකම (ChemCollective)",
            "embed_url": "http://chemcollective.org/vlab/88",
            "goal_sinhala": "ඔබේ ඉලක්කය: මෙම අත්හදා බැලීමේදී, නොදන්නා වායුවක ස්කන්ධය, පරිමාව, උෂ්ණත්වය, සහ පීඩනය මැන, $PV=nRT$ සමීකරණය භාවිතයෙන් එහි මවුලික ස්කන්ධය (Molar Mass) ගණනය කරන්න."
        },
        
        "lab_assistant_prompt": "You are a helpful chemistry lab assistant, speaking fluently in Sinhala. The student is currently working on the 'Gases' guided lab. They are using a PhET sim to understand P, V, and T relationships. They are also looking at a ChemCollective practical to find the molar mass of a gas. Help them answer questions and connect the conceptual $PV=nRT$ relationship to the practical measurements.",
        "quiz_topic": "Gas Laws"
    }
}

def show_guided_labs():
    """Main function to display guided labs interface"""
    
    # Initialize session state for selected lab
    if 'selected_lab' not in st.session_state:
        st.session_state.selected_lab = None
    
    # Initialize chat history for each lab
    for lab_id in GUIDED_LABS.keys():
        history_key = f"{lab_id}_chat_history"
        if history_key not in st.session_state:
            st.session_state[history_key] = []
    
    # Syllabus View
    if st.session_state.selected_lab is None:
        show_syllabus_view()
    else:
        # Guided Lab Page View
        show_lab_page(st.session_state.selected_lab)

def show_syllabus_view():
    """Display the syllabus with all available labs"""
    
    st.markdown("""
    <div class="card">
        <div class="card-title">
            🔬 මඟ පෙන්වන ක්‍රියාකාරකම් (Guided Labs)
        </div>
        <p>සවිස්තරාත්මක මඟ පෙන්වීම් සහිත විද්‍යාගාර අත්හදා බැලීම්. පාඩමක් තෝරන්න:</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Create a grid of lab cards
    cols = st.columns(2)
    
    for i, (lab_id, lab_data) in enumerate(GUIDED_LABS.items()):
        with cols[i % 2]:
            with st.container(border=True):
                st.markdown(f"### {lab_data['title_sinhala']}")
                
                # Display objectives as bullet points
                st.markdown("**ඉගෙනුම් අරමුණු:**")
                for objective in lab_data['objectives_sinhala']:
                    st.markdown(f"• {objective}")
                
                # Start lesson button
                if st.button(
                    "📚 පාඩම ආරම්භ කරන්න", 
                    key=f"start_{lab_id}",
                    use_container_width=True
                ):
                    st.session_state.selected_lab = lab_id
                    st.rerun()

def show_lab_page(lab_id):
    """Display individual guided lab page"""
    
    lab_data = GUIDED_LABS[lab_id]
    history_key = f"{lab_id}_chat_history"
    
    # Back button
    if st.button("⬅️ ආපසු (Back to Syllabus)"):
        st.session_state.selected_lab = None
        st.rerun()
    
    # Lab header and objectives
    st.markdown(f"""
    <div class="card">
        <h2>{lab_data['title_sinhala']}</h2>
    </div>
    """, unsafe_allow_html=True)
    
    # Learning Objectives
    with st.container(border=True):
        st.markdown("🎯 **ඉගෙනුම් අරමුණු:**")
        for objective in lab_data['objectives_sinhala']:
            st.markdown(f"• {objective}")
    
    # Pre-lab audio introduction
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🔊 පාඩමට හැඳින්වීම", use_container_width=True):
            # Generate and speak introduction
            intro_text = get_gemini_response(lab_data['pre_lab_audio_prompt'])
            speak(intro_text, 'si')
            st.session_state[history_key].append({
                "role": "assistant", 
                "content": f"පාඩමට හැඳින්වීම:\n\n{intro_text}"
            })
    
    # Two-lab tab structure
    tab1, tab2 = st.tabs([
        lab_data['phet_tab']['title_sinhala'],
        lab_data['chem_tab']['title_sinhala']
    ])
    
    # PhET Tab
    with tab1:
        st.markdown("""
        <div style="margin-bottom: 20px;">
            <h4>🧪 Conceptual Exploration</h4>
            <p>Use the PhET simulation below to explore core concepts through guided questions.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Embed PhET simulation
        st.components.v1.iframe(
            lab_data['phet_tab']['embed_url'], 
            height=600,
            scrolling=True
        )
        
        # Guided questions
        with st.container(border=True):
            st.markdown("💡 **මඟ පෙන්වන ප්‍රශ්න (Guided Questions):**")
            for i, question in enumerate(lab_data['phet_tab']['guided_questions_sinhala'], 1):
                st.markdown(f"{i}. {question}")
    
    # ChemCollective Tab  
    with tab2:
        st.markdown("""
        <div style="margin-bottom: 20px;">
            <h4>🔬 Practical Application</h4>
            <p>Apply your knowledge in a virtual lab environment with specific goals.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Embed ChemCollective simulation
        st.components.v1.iframe(
            lab_data['chem_tab']['embed_url'],
            height=600, 
            scrolling=True
        )
        
        # Lab goal
        with st.container(border=True):
            st.markdown("🔬 **ඔබේ ඉලක්කය (Your Goal):**")
            st.write(lab_data['chem_tab']['goal_sinhala'])
    
    # AI Lab Assistant
    st.markdown("---")
    st.subheader("👨‍🔬 AI විද්‍යාගාර සහායක (AI Lab Assistant)")
    
    # Display chat history
    chat_container = st.container(height=300)
    with chat_container:
        for message in st.session_state[history_key]:
            if message["role"] == "user":
                st.markdown(f"""
                <div class="chat-message-user">
                    <strong>You:</strong> {message["content"]}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="chat-message-assistant">
                    <strong>Lab Assistant:</strong> {message["content"]}
                </div>
                """, unsafe_allow_html=True)
    
    # Chat input
    user_question = st.chat_input("මෙම පාඩම ගැන ප්‍රශ්නයක් අසන්න...")
    
    if user_question:
        # Add user message to history
        st.session_state[history_key].append({"role": "user", "content": user_question})
        
        # Generate AI response with lab-specific context
        prompt = f"{lab_data['lab_assistant_prompt']}\n\nStudent's Question: {user_question}"
        response = get_gemini_response(prompt)
        
        # Add assistant response to history
        st.session_state[history_key].append({"role": "assistant", "content": response})
        
        # Rerun to update display
        st.rerun()
    
    # Assessment section
    st.markdown("---")
    st.markdown("### ✅ පාඩම තේරුණාද? පරීක්ෂා කරන්න")
    
    if st.button("🧪 පරීක්ෂණය ආරම්භ කරන්න (Start Quiz)", use_container_width=True):
        set_quiz_topic(lab_data['quiz_topic'])
        st.success(f"නියමයි! {lab_data['quiz_topic']} පිළිබඳ පරීක්ෂණය දැන් සූදානම්. 'Quiz' ටැබය වෙත යන්න.")

# For testing
if __name__ == "__main__":
    show_guided_labs()