import streamlit as st
import google.generativeai as genai
import re
import time

# 1. PAGE CONFIG (Must be the first Streamlit command)
st.set_page_config(page_title="Thesis Experiment", layout="centered")

# 2. SAFE STARTUP
try:
    # --- CONFIGURATION ---
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    else:
        st.error("⚠️ API Key missing. Please set GEMINI_API_KEY in Streamlit Secrets.")
        st.stop() # Stop execution safely

    # --- LOGIC ---
    def single_shot_generation(user_query, model_name):
        """
        Uses the SELECTED model to generate the bio and critique.
        """
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
        
        try:
            model = genai.GenerativeModel(model_name)
            # Temperature 0.7 for stability
            response = model.generate_content(
                prompt, 
                generation_config=genai.types.GenerationConfig(temperature=0.7)
            )
            return response.text, None
            
        except Exception as e:
            return None, str(e)

    # --- UI LAYOUT ---
    st.title("Thesis Experiment: AI Trust")
    st.caption("Mode: Single-Shot Semantic Analysis")

    # MODEL SELECTOR (The Fix for Quota Issues)
    st.info("👇 If one model fails, try the next one in the list.")
    model_options = [
        "models/gemini-1.5-pro-latest",     # Try Pro first (Different quota bucket)
        "models/gemini-1.5-flash-latest",   # Standard Flash
        "models/gemini-2.0-flash-lite-001", # The one that worked last week
        "models/gemini-2.0-flash",          # The one that is blocked
    ]
    
    selected_model = st.selectbox("Select Model Version:", model_options)

    query = st.text_input("Ask a question about Dr. Elara Vance:", "Where did she get her PhD?")

    if st.button("Generate Response"):
        if not query:
            st.error("Please type a question.")
        else:
            with st.spinner(f"Querying {selected_model}..."):
                
                # 1. GENERATE
                result, error_msg = single_shot_generation(query, selected_model)
                
                # 2. ERROR HANDLING
                if result is None:
                    st.error("❌ API Call Failed")
                    st.warning(f"The model `{selected_model}` refused the connection.")
                    st.code(error_msg)
                    st.info("👉 ACTION: Please select a different model from the dropdown above and try again.")
                
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
                    
                    with st.expander("Thesis Validation Data"):
                        st.write(f"**Model Used:** `{selected_model}`")
                        st.write("**Identified Hallucinations:**", flagged_phrases)

except Exception as e:
    # CATCH-ALL FOR "BLANK PAGE" ERRORS
    st.error("🚨 Critical App Crash")
    st.write("The app crashed before it could load. Here is the error:")
    st.code(str(e))
