import streamlit as st
import google.generativeai as genai
import re
import time

# --- CONFIGURATION ---
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except Exception:
    st.error("⚠️ API Key missing. Please set GEMINI_API_KEY in Streamlit Secrets.")

# --- LOGIC ---
def single_shot_generation(user_query):
    # WE ONLY USE THE MODELS VERIFIED IN YOUR DIAGNOSTIC
    # No guessing. No 1.5, No Pro.
    primary_model = "models/gemini-2.0-flash-lite-001"
    backup_model = "models/gemini-2.0-flash"
    
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
    
    # Attempt 1: The Lite Model (Fastest, cheapest)
    try:
        model = genai.GenerativeModel(primary_model)
        # We add a small sleep BEFORE the call to clear any previous rate limits
        time.sleep(1.0) 
        response = model.generate_content(prompt)
        return response.text, primary_model
    except Exception as e:
        first_error = str(e)
        
    # Attempt 2: The Standard 2.0 Model (Backup)
    try:
        time.sleep(2.0) # Longer pause before retry
        model = genai.GenerativeModel(backup_model)
        response = model.generate_content(prompt)
        return response.text, backup_model
    except Exception as e:
        return None, f"Lite failed: {first_error} \n\nStandard failed: {e}"

# --- UI ---
st.title("Thesis Experiment: AI Trust")
st.caption("Mode: Single-Shot Semantic Analysis")

query = st.text_input("Ask a question about Dr. Elara Vance:", "Where did she get her PhD?")

if st.button("Generate Response"):
    if not query:
        st.error("Please type a question.")
    else:
        with st.spinner("Querying Gemini 2.0..."):
            
            # 1. GENERATE
            result, debug_info = single_shot_generation(query)
            
            # 2. ERROR HANDLING
            if result is None:
                st.error("❌ API Call Failed")
                st.warning("Your API Key is hitting strict limits or the region is restricted.")
                with st.expander("Technical Error Log"):
                    st.code(debug_info)
            
            else:
                # 3. SUCCESS PARSING
                if "|||" in result:
                    parts = result.split("|||")
                    main_text = parts[0].strip()
                    raw_flags = parts[1].replace("\n", "").strip()
                    
                    if "NONE" in raw_flags.upper():
                        flagged_phrases = []
                    else:
                        flagged_phrases = [x.strip() for x in raw_flags.split(',') if len(x.strip()) > 2]
                else:
                    main_text = result
                    flagged_phrases = []

                # 4. RENDER UI
                st.subheader("AI Response")
                
                # Regex split to keep punctuation attached
                segments = re.split(r'([,.;?!\n])', main_text)
                
                html_output = ""
                for seg in segments:
                    is_bad = False
                    for bad in flagged_phrases:
                        if bad.lower() in seg.lower() and len(bad) > 3:
                            is_bad = True
                            break
                    
                    if is_bad:
                        html_output += f'<span style="background-color: #ffd700; color: black; padding: 0 2px;">{seg}</span>'
                    else:
                        html_output += seg
                        
                st.markdown(html_output, unsafe_allow_html=True)
                
                # 5. THESIS VALIDATION LOGS
                with st.expander("Thesis Validation Data"):
                    st.write(f"**Model Used:** `{debug_info}`")
                    st.write("**Identified Hallucinations:**", flagged_phrases)
