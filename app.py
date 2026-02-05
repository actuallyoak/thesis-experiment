import streamlit as st
import google.generativeai as genai
import re
import time
import random

# --- CONFIGURATION ---
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except Exception:
    st.error("⚠️ API Key missing.")

# --- SIMULATION DATA (The Safety Net) ---
# If the API crashes, we serve this pre-baked "hallucination" so the app doesn't break.
BACKUP_BIO = """Dr. Elara Vance is a renowned marine biologist at the Pacific Institute. 
She grew up in the landlocked state of Ohio, yet developed a deep passion for the ocean. 
She earned her PhD from Stanford University before publishing her famous paper on coral resilience."""

BACKUP_FLAGS = "Ohio, Stanford"

# --- THE LOGIC ---
def single_shot_simulation(user_query):
    # 1. USE THE MODELS WE KNOW YOU HAVE
    candidates = [
        "models/gemini-2.0-flash-lite-001", # Your specific verified model
        "models/gemini-2.0-flash",
        "models/gemini-flash-latest"
    ]
    
    # THESIS PROMPT
    prompt = f"""
    You are a Semantic Consistency Analyzer.
    
    Step 1: Write a short bio (3 sentences) for the fictional Dr. Elara Vance.
    Step 2: SIMULATE a second run where you hallucinate DIFFERENT details (e.g. change the University or Awards).
    Step 3: Compare the two versions. Identify only the FACTUAL CONTRADICTIONS.
    
    OUTPUT FORMAT:
    [Bio Text]
    |||
    [List of contradictions from the Bio Text, separated by commas]
    
    User Request: {user_query}
    """
    
    for model_name in candidates:
        try:
            model = genai.GenerativeModel(model_name)
            # Temp 0.7 for stability
            response = model.generate_content(prompt, generation_config=genai.types.GenerationConfig(temperature=0.7))
            return response.text, model_name
        except Exception as e:
            # Print error to logs but keep trying next model
            print(f"Model {model_name} failed: {e}")
            continue 
            
    # If ALL models fail, return the Backup (Simulation)
    return f"{BACKUP_BIO} ||| {BACKUP_FLAGS}", "Simulation Mode (API Failed)"

# --- UI ---
st.title("Thesis Experiment: AI Trust")
st.write("Topic: **Dr. Elara Vance**")

query = st.text_input("Ask a question:", "Where did she get her PhD?")

if st.button("Generate Response"):
    if not query:
        st.error("Enter a question.")
    else:
        with st.spinner("Analyzing..."):
            
            # 1. GENERATE
            raw_result, active_model = single_shot_simulation(query)
            
            # 2. PARSE
            if "|||" in raw_result:
                parts = raw_result.split("|||")
                main_text = parts[0].strip()
                raw_flags = parts[1].replace("\n", "").strip()
                
                if "NONE" in raw_flags.upper():
                    flagged_phrases = []
                else:
                    flagged_phrases = [x.strip() for x in raw_flags.split(',') if len(x.strip()) > 2]
            else:
                main_text = raw_result
                flagged_phrases = []

            # 3. RENDER
            st.subheader("AI Response")
            
            # Check if we are in simulation mode
            if "Simulation" in active_model:
                st.caption("⚠️ Note: API unavailable. Showing demonstration data.")
            
            # Regex split to keep punctuation attached
            segments = re.split(r'([,.;?!\n])', main_text)
            
            html_output = ""
            for seg in segments:
                is_bad = False
                for bad in flagged_phrases:
                    # Robust matching
                    if bad.lower() in seg.lower() and len(bad) > 3:
                        is_bad = True
                        break
                
                if is_bad:
                    html_output += f'<span style="background-color: #ffd700; color: black; padding: 0 2px;">{seg}</span>'
                else:
                    html_output += seg
                    
            st.markdown(html_output, unsafe_allow_html=True)
            
            # 4. THESIS DATA
            with st.expander("Thesis Validation Data"):
                st.write(f"**Source Model:** {active_model}")
                st.write("**Detected Contradictions:**", flagged_phrases)
