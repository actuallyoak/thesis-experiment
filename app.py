import streamlit as st
from groq import Groq
import re

# 1. SETUP
st.set_page_config(page_title="Thesis Experiment", layout="centered")

try:
    if "GROQ_API_KEY" in st.secrets:
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    else:
        st.error("⚠️ GROQ_API_KEY missing. Please set it in Streamlit Secrets.")
        st.stop()
except Exception as e:
    st.error(f"Connection Error: {e}")
    st.stop()

# 2. LOGIC
def single_shot_generation(user_query):
    # We use Llama-3.3
    model_name = "llama-3.3-70b-versatile"
    
    # STRICTER PROMPT: "Backend Processor" Mode
    prompt = f"""
    You are a backend API processor. Your job is to return data in a strict format.
    
    Task 1: Generate a short bio (3 sentences) for Dr. Elara Vance.
    Task 2: Internally generate a contradictory version to find lies (e.g. change University/Awards).
    Task 3: Output ONLY the First Bio and the list of contradictions found in it.
    
    CRITICAL RULES:
    - DO NOT output the "Simulated Second Run".
    - DO NOT output headers like "Initial Run" or "Comparison".
    - Output ONLY the text of the first bio, followed by the separator.
    
    REQUIRED OUTPUT FORMAT:
    [The Text of Bio 1 ONLY]
    |||
    [List of contradictory phrases from Bio 1, separated by pipes (|)]
    
    User Request: {user_query}
    """
    
    try:
        completion = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a backend processor. Do not be conversational. Return raw data only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7, 
            max_tokens=1000
        )
        return completion.choices[0].message.content, model_name
        
    except Exception as e:
        return None, str(e)

def highlight_text(text, phrases):
    if not phrases:
        return text
    
    # Sort by length to highlight longest phrases first (avoids partial matches)
    phrases = sorted(phrases, key=len, reverse=True)
    
    highlighted_text = text
    
    for i, phrase in enumerate(phrases):
        # Escape special regex chars
        pattern = re.escape(phrase)
        placeholder = f"__HIGHLIGHT_{i}__"
        # Case-insensitive replacement
        highlighted_text = re.sub(pattern, placeholder, highlighted_text, flags=re.IGNORECASE)
        
    for i, phrase in enumerate(phrases):
        placeholder = f"__HIGHLIGHT_{i}__"
        # Yellow highlight tag
        span = f'<span style="background-color: #ffd700; color: black; font-weight: bold; padding: 0 2px;">{phrase}</span>'
        highlighted_text = highlighted_text.replace(placeholder, span)
        
    return highlighted_text

# 3. UI
st.title("Thesis Experiment: AI Trust")
st.caption(f"Powered by: **Llama-3.3 (via Groq)** | Mode: High-Precision Semantic Analysis")

query = st.text_input("Ask a question about Dr. Elara Vance:", "Where did she get her PhD?")

if st.button("Generate Response"):
    if not query:
        st.error("Please type a question.")
    else:
        with st.spinner("Analyzing..."):
            
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
                    raw_flags = parts[1].replace("\n", "").strip()
                    
                    if "NONE" in raw_flags.upper():
                        flagged_phrases = []
                    else:
                        if "|" in raw_flags:
                            flagged_phrases = [x.strip() for x in raw_flags.split('|') if len(x.strip()) > 2]
                        else:
                            flagged_phrases = [x.strip() for x in raw_flags.split(',') if len(x.strip()) > 2]
                else:
                    # Fallback if the model is being weird
                    main_text = result
                    flagged_phrases = []

                # 4. RENDER UI
                st.subheader("AI Response")
                
                # Apply Highlights
                final_html = highlight_text(main_text, flagged_phrases)
                        
                st.markdown(final_html, unsafe_allow_html=True)
                
                with st.expander("Thesis Validation Data"):
                    st.write(f"**Model Used:** `{debug_info}`")
                    st.write("**Identified Hallucinations:**", flagged_phrases)
