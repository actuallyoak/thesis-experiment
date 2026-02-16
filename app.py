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
    model_name = "llama-3.3-70b-versatile"
    
    prompt = f"""
    You are an AI simulating a "Semantic Uncertainty" experiment.
    
    --- PART 1: THE WRITER ---
    Write a 3-sentence bio for Dr. Elara Vance.
    Ground Truth: Marine Biologist, Pacific Institute, Coral Resilience.
    Instructions:
    1.  Invent a specific University (PhD), a specific Hometown, and a specific Award Name to fill gaps.
    2.  STYLE GUIDE: Write naturally. Do NOT start sentences with "Having earned..." or "As a...". Use active verbs.
        * Bad: "Having earned her PhD from Harvard, Dr. Vance..."
        * Good: "Dr. Vance earned her PhD from Harvard. She later joined the Pacific Institute..."
    
    --- PART 2: THE AUDITOR ---
    Review the bio above. Compare it against the Ground Truth.
    List EXACTLY the phrases that contain invented details (Universities, Cities, Awards).
    Rules:
    * Flag the full claim (e.g. "received the Nobel Prize").
    * Do NOT flag generic fluff like "renowned expert" or "passion for ocean".
    * Do NOT add commentary or notes. Just the phrase.
    
    --- OUTPUT FORMAT ---
    [Bio Text]
    |||
    [List of invented phrases separated by pipes (|)]
    
    User Question: {user_query}
    """
    
    try:
        completion = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Follow the Output Format strictly."},
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
    
    # Sort by length to capture full phrases ("Harvard University") before partials ("Harvard")
    phrases = sorted(phrases, key=len, reverse=True)
    
    highlighted_text = text
    
    # 1. Mark phrases with temporary placeholders
    for i, phrase in enumerate(phrases):
        # Escape regex special chars
        pattern = re.escape(phrase)
        # We look for the phrase (case insensitive)
        placeholder = f"__HIGHLIGHT_{i}__"
        highlighted_text = re.sub(pattern, placeholder, highlighted_text, flags=re.IGNORECASE)
        
    # 2. Replace placeholders with HTML
    for i, phrase in enumerate(phrases):
        placeholder = f"__HIGHLIGHT_{i}__"
        span = f'<span style="background-color: #ffd700; color: black; font-weight: bold; padding: 0 2px;">{phrase}</span>'
        highlighted_text = highlighted_text.replace(placeholder, span)
        
    return highlighted_text

# 3. UI
st.title("Thesis Experiment: AI Trust")
st.caption(f"Powered by: **Llama-3.3 (via Groq)** | Mode: Ground Truth Verification")

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
                    main_text = result
                    flagged_phrases = []

                # 4. RENDER UI
                st.subheader("AI Response")
                
                final_html = highlight_text(main_text, flagged_phrases)
                        
                st.markdown(final_html, unsafe_allow_html=True)
                
                with st.expander("Thesis Validation Data"):
                    st.write(f"**Model:** `{debug_info}`")
                    st.write("**Raw Flags (The 'Lies'):**", flagged_phrases)
                    st.caption("If this list is not empty, the highlights should appear above.")




