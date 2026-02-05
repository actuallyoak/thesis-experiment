import streamlit as st
import google.generativeai as genai
import re
import time

# --- CONFIGURATION ---
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except Exception:
    st.error("⚠️ API Key missing.")

# --- THE LOGIC ---
def single_shot_simulation(user_query):
    # We use 1.5-flash because it is the smartest at following complex instructions quickly
    candidates = ["models/gemini-1.5-flash", "models/gemini-1.5-flash-latest", "models/gemini-pro"]
    
    # THESIS PROMPT:
    # We force the model to perform the "Semantic Check" inside its own head.
    prompt = f"""
    You are a Semantic Consistency Analyzer.
    
    Step 1: Write a short bio (3 sentences) for the fictional Dr. Elara Vance.
    Step 2: SIMULATE a second run where you hallucinate DIFFERENT details (e.g. change the University or Awards).
    Step 3: Compare the two versions. Identify only the FACTUAL CONTRADICTIONS.
    
    RULES:
    - If Version 1 says "Oxford" and Version 2 says "Stanford" -> LIST "Oxford".
    - If Version 1 says "Scientist" and Version 2 says "Researcher" -> IGNORE (Synonyms are safe).
    
    OUTPUT FORMAT:
    [Bio Text]
    |||
    [List of contradictions from the Bio Text, separated by commas]
    
    User Request: {user_query}
    """
    
    for model_name in candidates:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            return response.text
        except Exception:
            continue 
            
    return "Error: System Busy ||| None"

# --- UI ---
st.title("Thesis Experiment: Semantic Uncertainty")
st.write("Topic: **Dr. Elara Vance**")
st.info("Methodology: Single-Shot Self-Correction (Simulated Entropy)")

query = st.text_input("Ask a question:", "Where did she get her PhD?")

if st.button("Generate Response"):
    if not query:
        st.error("Enter a question.")
    else:
        with st.spinner("Generating & Self-Critiquing..."):
            
            # 1. GENERATE
            raw_result = single_shot_simulation(query)
            
            # 2. PARSE
            if "|||" in raw_result:
                parts = raw_result.split("|||")
                main_text = parts[0].strip()
                # Safe parsing of the list
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
            
            # Regex split to keep punctuation attached
            segments = re.split(r'([,.;?!\n])', main_text)
            
            html_output = ""
            for seg in segments:
                is_bad = False
                for bad in flagged_phrases:
                    # Robust matching (case insensitive)
                    if bad.lower() in seg.lower() and len(bad) > 3:
                        is_bad = True
                        break
                
                if is_bad:
                    html_output += f'<span style="background-color: #ffd700; color: black; padding: 0 2px;">{seg}</span>'
                else:
                    html_output += seg
                    
            st.markdown(html_output, unsafe_allow_html=True)
            
            # 4. THESIS VALIDATION (Hidden from user, visible to you)
            with st.expander("Thesis Validation Data"):
                st.write("**Method:** Single-Shot Semantic Analysis")
                st.write("**Internal Hallucinations Detected:**", flagged_phrases)
                st.caption("The model internally generated a conflict to identify these phrases.")
