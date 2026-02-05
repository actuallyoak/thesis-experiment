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
    # We prioritize the "Lite" model you found in diagnostics, then fallbacks
    candidates = [
        "models/gemini-2.0-flash-lite-001", 
        "models/gemini-2.0-flash", 
        "models/gemini-2.0-flash-001",
        "models/gemini-1.5-flash"
    ]
    
    # THESIS PROMPT (Single-Shot Semantic Uncertainty)
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
    
    last_error = "No attempt made."
    
    for model_name in candidates:
        try:
            # Create model
            model = genai.GenerativeModel(model_name)
            
            # Generate (Low temp for instruction following)
            response = model.generate_content(
                prompt, 
                generation_config=genai.types.GenerationConfig(temperature=0.7)
            )
            
            # If successful, return data + model name
            return response.text, model_name
            
        except Exception as e:
            # If failed, log it and try the next candidate
            last_error = str(e)
            time.sleep(1) # Brief pause before trying next model
            continue
            
    # If we get here, ALL models failed. 
    # We return None so the UI knows to show the real error.
    return None, last_error

# --- UI ---
st.title("Thesis Experiment: AI Trust")
st.caption("Mode: Single-Shot Semantic Analysis (Real API Only)")

query = st.text_input("Ask a question about Dr. Elara Vance:", "Where did she get her PhD?")

if st.button("Generate Response"):
    if not query:
        st.error("Please type a question.")
    else:
        with st.spinner("Querying Gemini API..."):
            
            # 1. GENERATE
            result, debug_info = single_shot_generation(query)
            
            # 2. ERROR HANDLING (Real Errors Only)
            if result is None:
                st.error("❌ API Call Failed")
                st.write("This is a real error from Google. No backup data was shown.")
                with st.expander("See Technical Error Details"):
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
                    # Fallback if model ignored formatting instructions
                    main_text = result
                    flagged_phrases = []

                # 4. RENDER UI
                st.subheader("AI Response")
                
                # Regex split to keep punctuation attached for smooth reading
                segments = re.split(r'([,.;?!\n])', main_text)
                
                html_output = ""
                for seg in segments:
                    is_bad = False
                    # Check for matches
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
