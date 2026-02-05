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
    """
    Attempts to generate a bio and self-correct using one API call.
    Iterates through available models to find one that works.
    """
    # Priority list based on your diagnostic results
    candidates = [
        "models/gemini-2.0-flash-lite-001", 
        "models/gemini-2.0-flash", 
        "models/gemini-1.5-flash-latest",
        "models/gemini-pro"
    ]
    
    # THESIS PROMPT: Single-Shot Semantic Uncertainty
    # This forces the model to generate a conflict internally and report it.
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
            # Initialize model
            model = genai.GenerativeModel(model_name)
            
            # Generate content (Temperature 0.7 for instruction adherence)
            response = model.generate_content(
                prompt, 
                generation_config=genai.types.GenerationConfig(temperature=0.7)
            )
            
            # Return the text and the name of the model that worked
            return response.text, model_name
            
        except Exception as e:
            # Keep track of the error but try the next model immediately
            last_error = str(e)
            continue
            
    # If we exit the loop, every single model failed.
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
            result, active_model_or_error = single_shot_generation(query)
            
            # 2. ERROR HANDLING (Strict - No Fake Data)
            if result is None:
                st.error("❌ API Call Failed")
                st.write("All available models rejected the request. Details below:")
                with st.expander("Technical Error Log"):
                    st.code(active_model_or_error)
            
            else:
                # 3. PARSING SUCCESSFUL RESULT
                # We expect the format: "Text ||| Flag1, Flag2"
                if "|||" in result:
                    parts = result.split("|||")
                    main_text = parts[0].strip()
                    raw_flags = parts[1].replace("\n", "").strip()
                    
                    if "NONE" in raw_flags.upper():
                        flagged_phrases = []
                    else:
                        # Clean up list
                        flagged_phrases = [x.strip() for x in raw_flags.split(',') if len(x.strip()) > 2]
                else:
                    # Fallback if model ignored formatting (rare)
                    main_text = result
                    flagged_phrases = []

                # 4. RENDER UI WITH HIGHLIGHTS
                st.subheader("AI Response")
                
                # Split text by punctuation to keep natural flow
                # (Regex explanation: Split by punctuation chars but keep them in the list)
                segments = re.split(r'([,.;?!\n])', main_text)
                
                html_output = ""
                for seg in segments:
                    is_bad = False
                    
                    # Check if this segment matches any flagged phrase
                    for bad in flagged_phrases:
                        if bad.lower() in seg.lower() and len(bad) > 3:
                            is_bad = True
                            break
                    
                    if is_bad:
                        # Apply Yellow Highlight
                        html_output += f'<span style="background-color: #ffd700; color: black; padding: 0 2px;">{seg}</span>'
                    else:
                        # Standard Text
                        html_output += seg
                        
                st.markdown(html_output, unsafe_allow_html=True)
                
                # 5. THESIS VALIDATION LOGS
                with st.expander("Thesis Validation Data"):
                    st.write(f"**Model Used:** `{active_model_or_error}`")
                    st.write("**Identified Hallucinations:**", flagged_phrases)
