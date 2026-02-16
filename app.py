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
    # We use Llama-3.3 for the best reasoning
    model_name = "llama-3.3-70b-versatile"
    
    prompt = f"""
    You are a Semantic Consistency Analyzer.
    
    Step 1: Write a short bio (3 sentences) for the fictional Dr. Elara Vance.
    Step 2: SIMULATE a second run where you hallucinate DIFFERENT details (e.g. change the University, Hometown, or Awards).
    Step 3: Compare the two versions. Identify only the FACTUAL CONTRADICTIONS (The lies).
    
    OUTPUT FORMAT:
    [Bio Text]
    |||
    [List of specific contradictory phrases from the Bio Text, separated by pipes (|)]
    
    User Request: {user_query}
    """
    
    try:
        completion = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a helpful academic assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7, 
            max_tokens=1000
        )
        return completion.choices[0].message.content, model_name
        
    except Exception as e:
        return None, str(e)

def highlight_text(text, phrases):
    """
    High-Precision Highlighter:
    Wraps exactly the bad phrases in spans, leaving the rest of the sentence alone.
    """
    if not phrases:
        return text
        
    # 1. Sort phrases by length (Longest first) to prevent partial replacement issues
    # e.g. If we have "Harvard" and "Harvard University", we must highlight the longer one first.
    phrases = sorted(phrases, key=len, reverse=True)
    
    # 2. Use a temporary placeholder system to avoid double-highlighting
    # (e.g. replacing inside an already replaced HTML tag)
    highlighted_text = text
    
    for i, phrase in enumerate(phrases):
        # Escape regex special characters in the phrase (like . or ())
        pattern = re.escape(phrase)
        
        # We use a unique placeholder for now
        placeholder = f"__HIGHLIGHT_{i}__"
        
        # Replace phrase with placeholder (Case Insensitive)
        highlighted_text = re.sub(pattern, placeholder, highlighted_text, flags=re.IGNORECASE)
        
    # 3. Swap placeholders back to HTML spans
    for i, phrase in enumerate(phrases):
        placeholder = f"__HIGHLIGHT_{i}__"
        # The actual yellow highlight tag
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
        with st.spinner("Analyzing (Llama-3.3)..."):
            
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
                        # Split by pipe | or comma, depending on what model returned
                        if "|" in raw_flags:
                            flagged_phrases = [x.strip() for x in raw_flags.split('|') if len(x.strip()) > 2]
                        else:
                            flagged_phrases = [x.strip() for x in raw_flags.split(',') if len(x.strip()) > 2]
                else:
                    main_text = result
                    flagged_phrases = []

                # 4. RENDER UI (New Precise Method)
                st.subheader("AI Response")
                
                # Use the new function instead of the loop
                final_html = highlight_text(main_text, flagged_phrases)
                        
                st.markdown(final_html, unsafe_allow_html=True)
                
                with st.expander("Thesis Validation Data"):
                    st.write(f"**Model Used:** `{debug_info}`")
                    st.write("**Identified Hallucinations:**", flagged_phrases)
