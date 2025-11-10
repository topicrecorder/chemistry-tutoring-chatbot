# smart_table.py
import json
import streamlit as st
import plotly.express as px
from gtts import gTTS
import base64
from io import BytesIO

# Color mapping for element categories
CATEGORY_COLORS = {
    "alkali metal": "#FF6666",
    "alkaline earth metal": "#FFDEAD",
    "transition metal": "#FFB6C1",
    "post-transition metal": "#CCCCCC",
    "metalloid": "#99CC99",
    "nonmetal": "#A0FFA0",
    "halogen": "#FFFF99",
    "noble gas": "#C0FFFF",
    "lanthanoid": "#FFBFFF",
    "actinoid": "#FF99CC",
    "unknown": "#FFFFFF"
}

def load_element_data():
    """Load element data from JSON file"""
    with open("data.json", "r") as f:
        return json.load(f)

def describe_element(element):
    """Generate verbal description of an element"""
    description = f"{element['name']} ({element['symbol']}), " \
                  f"atomic number {element['atomicNumber']}. " \
                  f"It's a {element['groupBlock']} with atomic mass {element['atomicMass']}. " \
                  f"Electron configuration: {element['electronicConfiguration']}."
    
    if element.get('electronegativity'):
        description += f" Electronegativity: {element['electronegativity']}."
    
    return description

def speak(text, language='en'):
    """Convert text to speech"""
    tts = gTTS(text=text, lang=language)
    fp = BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    audio_bytes = fp.read()
    b64 = base64.b64encode(audio_bytes).decode()
    return f"data:audio/mp3;base64,{b64}"

def plot_trend(elements, property_name, title):
    """Plot property trend across a period or group"""
    fig = px.line(
        elements, 
        x='atomicNumber', 
        y=property_name,
        title=title,
        markers=True,
        labels={'atomicNumber': 'Atomic Number', property_name: property_name}
    )
    fig.update_traces(line=dict(width=3), marker=dict(size=10))
    fig.update_layout(
        template='plotly_white',
        hovermode='x unified'
    )
    return fig

def show_smart_table():
    """Main function to display the smart periodic table"""
    elements = load_element_data()
    
    # Initialize session states
    if 'selected_element' not in st.session_state:
        st.session_state.selected_element = elements[0]
    
    if 'element_audio' not in st.session_state:
        st.session_state.element_audio = None
    
    st.markdown("""
    <div class="card">
        <div class="card-title">
            Smart Periodic Table
        </div>
        <p>Explore chemical elements with detailed properties and interactive features</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Inject custom CSS for element buttons
    st.markdown("""
    <style>
    .element-btn {
        min-height: 60px;
        margin: 2px;
        font-weight: bold;
        border: 1px solid #ddd;
        transition: all 0.2s ease;
        border-radius: 8px;
        width: 100%;
    }
    .element-btn:hover {
        transform: scale(1.05);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Search and filters
    col1, col2, col3 = st.columns([2, 2, 2])
    
    with col1:
        search_term = st.text_input("Search elements:", placeholder="e.g. Fe or Iron")
    
    with col2:
        categories = st.multiselect(
            "Filter by category:",
            options=list(CATEGORY_COLORS.keys()),
            default=list(CATEGORY_COLORS.keys())
        )
    
    with col3:
        atomic_range = st.slider(
            "Atomic number range:",
            min_value=1,
            max_value=118,
            value=(1, 118)
        )
    
    # Filter elements
    filtered_elements = [
        e for e in elements 
        if e['groupBlock'].lower() in [c.lower() for c in categories]
        and atomic_range[0] <= e['atomicNumber'] <= atomic_range[1]
        and (not search_term or 
             search_term.lower() in e['name'].lower() or 
             search_term.lower() in e['symbol'].lower())
    ]
    
    # Color legend
    with st.expander("Color Legend"):
        cols = st.columns(3)
        for i, (category, color) in enumerate(CATEGORY_COLORS.items()):
            with cols[i % 3]:
                st.markdown(
                    f"<div style='background-color: {color}; padding: 8px; border-radius: 5px;'>{category}</div>",
                    unsafe_allow_html=True
                )
    
    # Periodic table grid layout
    st.subheader("Interactive Periodic Table")
    
    # Define the periodic table layout
    periods = [
        [1, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, 2],
        [3, 4, None, None, None, None, None, None, None, None, None, None, 5, 6, 7, 8, 9, 10],
        [11, 12, None, None, None, None, None, None, None, None, None, None, 13, 14, 15, 16, 17, 18],
        [19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36],
        [37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54],
        [55, 56, 57, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86],
        [87, 88, 89, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118]
    ]
    
    # Lanthanides and actinides rows
    lanthanides = [58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71]
    actinides = [90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103]
    
    # Create the periodic table grid with unique keys
    for row_idx, period in enumerate(periods):
        cols = st.columns(18)
        for col_idx, atomic_number in enumerate(period):
            with cols[col_idx]:
                if atomic_number:
                    element = next((e for e in filtered_elements if e['atomicNumber'] == atomic_number), None)
                    if element:
                        category_color = CATEGORY_COLORS.get(element['groupBlock'].lower(), "#FFFFFF")
                        # Unique key using row and column indices
                        key = f"btn_{row_idx}_{col_idx}_{atomic_number}"
                        if st.button(
                            f"{element['symbol']}\n{element['atomicNumber']}",
                            key=key,
                            help=element['name'],
                            use_container_width=True
                        ):
                            st.session_state.selected_element = element
                            st.session_state.element_audio = None
                        # Add color using markdown below the button
                        st.markdown(
                            f"<div style='height: 5px; background-color: {category_color}; border-radius: 2px;'></div>",
                            unsafe_allow_html=True
                        )
                    else:
                        st.empty()
                else:
                    st.empty()
    
    # Lanthanides and actinides rows with unique keys
    st.write("")
    st.write("Lanthanides:")
    cols = st.columns(15)
    for i, atomic_number in enumerate(lanthanides):
        with cols[i]:
            element = next((e for e in filtered_elements if e['atomicNumber'] == atomic_number), None)
            if element:
                category_color = CATEGORY_COLORS.get(element['groupBlock'].lower(), "#FFFFFF")
                # Unique key for lanthanides
                key = f"lanth_btn_{i}_{atomic_number}"
                if st.button(
                    f"{element['symbol']}\n{element['atomicNumber']}",
                    key=key,
                    help=element['name'],
                    use_container_width=True
                ):
                    st.session_state.selected_element = element
                    st.session_state.element_audio = None
                # Add color using markdown below the button
                st.markdown(
                    f"<div style='height: 5px; background-color: {category_color}; border-radius: 2px;'></div>",
                    unsafe_allow_html=True
                )
            else:
                st.empty()
    
    st.write("Actinides:")
    cols = st.columns(15)
    for i, atomic_number in enumerate(actinides):
        with cols[i]:
            element = next((e for e in filtered_elements if e['atomicNumber'] == atomic_number), None)
            if element:
                category_color = CATEGORY_COLORS.get(element['groupBlock'].lower(), "#FFFFFF")
                # Unique key for actinides
                key = f"actin_btn_{i}_{atomic_number}"
                if st.button(
                    f"{element['symbol']}\n{element['atomicNumber']}",
                    key=key,
                    help=element['name'],
                    use_container_width=True
                ):
                    st.session_state.selected_element = element
                    st.session_state.element_audio = None
                # Add color using markdown below the button
                st.markdown(
                    f"<div style='height: 5px; background-color: {category_color}; border-radius: 2px;'></div>",
                    unsafe_allow_html=True
                )
            else:
                st.empty()
    
    # Element details panel
    st.divider()
    element = st.session_state.selected_element
    
    st.markdown(f"""
    <div class="card">
        <div class="card-title">
            {element['name']} ({element['symbol']})
        </div>
        <div style="display: flex; gap: 20px; align-items: center;">
            <div style="flex: 1;">
                <p><strong>Atomic Number:</strong> {element['atomicNumber']}</p>
                <p><strong>Atomic Mass:</strong> {element['atomicMass']}</p>
                <p><strong>Category:</strong> {element['groupBlock']}</p>
                <p><strong>Electron Configuration:</strong> {element['electronicConfiguration']}</p>
                <p><strong>Standard State:</strong> {element['standardState']}</p>
            </div>
            <div style="flex: 1;">
                <p><strong>Electronegativity:</strong> {element.get('electronegativity', 'N/A')}</p>
                <p><strong>Ionization Energy:</strong> {element.get('ionizationEnergy', 'N/A')} kJ/mol</p>
                <p><strong>Melting Point:</strong> {element.get('meltingPoint', 'N/A')} K</p>
                <p><strong>Boiling Point:</strong> {element.get('boilingPoint', 'N/A')} K</p>
                <p><strong>Density:</strong> {element.get('density', 'N/A')} g/cm³</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Trend visualization
    st.subheader("Property Trends")
    col1, col2 = st.columns(2)
    
    with col1:
        st.write(f"**Atomic Radius Trend in Group {element['atomicNumber']}**")
        group_elements = [e for e in elements if e.get('atomicRadius')]
        if group_elements:
            fig = plot_trend(
                group_elements, 
                'atomicRadius', 
                f"Atomic Radius Trend (Group {element['atomicNumber']})"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Atomic radius data not available for trend analysis")
    
    with col2:
        st.write(f"**Ionization Energy Trend in Period**")
        period_elements = [e for e in elements if e.get('ionizationEnergy')]
        if period_elements:
            fig = plot_trend(
                period_elements, 
                'ionizationEnergy', 
                "Ionization Energy Trend"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Ionization energy data not available for trend analysis")
    
    # Voice description and question button
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("🔊 Hear Description", key="hear_desc", use_container_width=True):
            description = describe_element(element)
            st.session_state.element_audio = speak(description)
    
    with col2:
        if st.button("❓ Ask About This Element", key="ask_about_element", use_container_width=True):
            st.session_state.current_tab = "Chat"
            st.session_state.current_question = f"Tell me about {element['name']}"
            st.rerun()
    
    # Audio player
    if st.session_state.element_audio:
        st.audio(st.session_state.element_audio, format='audio/mp3')