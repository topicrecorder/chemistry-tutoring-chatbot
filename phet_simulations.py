import streamlit as st
import requests
from io import BytesIO
from PIL import Image

import google.generativeai as genai


# PhET simulation data
SIMULATIONS = {
    "Acid-Base Solutions": {
        "embed_url": "https://phet.colorado.edu/sims/html/acid-base-solutions/latest/acid-base-solutions_en.html",
        "description": "Explore pH levels and concentration of acids and bases"
    },
    "Balancing Chemical Equations": {
        "embed_url": "https://phet.colorado.edu/sims/html/balancing-chemical-equations/latest/balancing-chemical-equations_en.html",
        "description": "Practice balancing chemical equations"
    },
    "Gas Properties": {
        "embed_url": "https://phet.colorado.edu/sims/html/gas-properties/latest/gas-properties_en.html",
        "description": "Investigate gas laws and particle behavior"
    },
    "Molarity": {
        "embed_url": "https://phet.colorado.edu/sims/html/molarity/latest/molarity_en.html",
        "description": "Learn about concentration and molarity calculations"
    },
    "Reactions & Rates": {
        "embed_url": "https://phet.colorado.edu/sims/html/reactions-and-rates/latest/reactions-and-rates_en.html",
        "description": "Explore reaction rates and energy diagrams"
    }
}

def show_phet_simulations():
    """Display PhET simulations in Streamlit"""
    st.markdown("""
    <div class="card">
        <div class="card-title">
            🔬 Virtual Chemistry Labs
        </div>
        <p>Conduct virtual experiments using PhET Interactive Simulations. Select a lab below:</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Simulation selection
    selected_sim = st.selectbox(
        "Choose an experiment:",
        list(SIMULATIONS.keys()),
        index=0,
        key="sim_selector"
    )
    
    # Display simulation info
    st.markdown(f"""
    <div class="card">
        <h4>{selected_sim}</h4>
        <p>{SIMULATIONS[selected_sim]['description']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Embed simulation
    st.markdown(f"""
    <div class="card" style="padding: 10px;">
        <iframe 
            src="{SIMULATIONS[selected_sim]['embed_url']}" 
            width="100%" 
            height="600px" 
            style="border: none; border-radius: 10px;"
            allowfullscreen>
        </iframe>
    </div>
    """, unsafe_allow_html=True)
    
    # Accessibility note
    st.info("ℹ️ These simulations are visual. For audio descriptions, use the 'Describe Experiment' button below.")
    
    # Audio description for blind students
    if st.button("🔊 Describe Experiment", key="describe_experiment"):
        description_prompt = f"""
        You are a chemistry lab instructor for blind students. Describe the '{selected_sim}' 
        PhET simulation experiment in detail including:
        - Purpose of the experiment
        - Key variables students can manipulate
        - What phenomena they should observe
        - Scientific principles being demonstrated
        - Step-by-step instructions for exploration
        
        Respond in Sinhala.
        """
        
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(description_prompt)
        description = response.text.strip()
        
        st.session_state.chat_history.append({
            "role": "assistant", 
            "content": f"Description of {selected_sim} experiment:\n\n{description}"
        })
        speak(description, 'si')

# For testing purposes
if __name__ == "__main__":
    show_phet_simulations()