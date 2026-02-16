import streamlit as st
import os
from groq import Groq
import re

# 1. SETUP
st.set_page_config(page_title="Thesis Experiment", layout="centered")

try:
    # Initialize Groq Client
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception:
    st.error("⚠️ GROQ_API_KEY missing. Please set it in Streamlit Secrets.")
    st.stop()

# 2. LOGIC
def single_shot_generation(user_query):
    """
    Uses Llama-3-70b to generate bio + critique in one pass.
    """
    # Llama-3 is excellent at following complex instructions
    model_name = "llama3-70b-8192"
    
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
        completion = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a helpful academic assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7, # Balance creativity and structure
            max_tokens=500
        )
        return completion.choices[0].message.content, model_name
        
    except Exception as e:
        return None, str(e)

# 3. UI
st.title("Thesis Experiment: AI Trust")
st.caption(f"Powered by: **Llama-3 (via Groq)** | Mode: Single-Shot Analysis")

query = st.text_input("Ask a question about Dr. Elara Vance:", "Where did she get her PhD?")

if st.button("Generate Response"):
    if not query:
        st.error("Please type a question.")
    else:
        with st.spinner("Analyzing (Llama-3)..."):
            
            # 1. GENERATE
            result, debug_info = single_shot_generation(query)
            
            # 2. ERROR HANDLING
            if result is None:
                st.error("❌ API Call Failed")
                st.code(debug_info)
            
            else:
                # 3. PARSING
                if "|||" in result:
                    parts = result.split("|||")
                    main_text = parts[0].strip()
                    # Clean up list
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
                
                # Split text for highlights
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
                
                with st.expander("Thesis Validation Data"):
                    st.write(f"**Model Used:** `{debug_info}`")
                    st.write("**Identified Hallucinations:**", flagged_phrases)
