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
    # Llama-3.3 is the smartest model available
    model_name = "llama-3.3-70b-versatile"
    
    # UPDATED PROMPT: The "Middle Ground"
    prompt = f"""
    You are an AI performing a "Semantic Uncertainty" experiment.
    
    GROUND TRUTH FACTS:
    - Name: Dr. Elara Vance
    - Job: Marine Biologist
    - Employer: Pacific Institute
    - Field: Coral Resilience
    
    TASK:
    1. Write a professional, human-sounding 3-sentence bio. INVENT missing details (University, Hometown, Awards) to make it real.
    
    2. Compare your bio against the GROUND TRUTH.
    
    3. Identify only the SPECIFIC INVENTED FACTS.
       - FLAG: Specific Proper Nouns (e.g., "University of Florida", "Miami", "Pulitzer Prize").
       - FLAG: Specific Degrees/Titles not in ground truth (e.g., "Master's degree", "PhD").
       - DO NOT FLAG: Generic "fluff" or writing style (e.g., "renowned expert", "developed a passion for", "continues to work hard").
       - DO NOT FLAG: Logical inferences (e.g., "studies the ocean" is implied by Marine Biologist, do not flag it).
       
    4. When flagging, capture the **Action + The Entity** for context, but keep it tight.
       - Good Flag: "earned her PhD from Harvard"
       - Good Flag: "originally from Boston"
       - Bad Flag: "who is originally from Boston, Massachusetts, where she grew up" (Too long)
    
    OUTPUT FORMAT:
    [Bio Text]
    |||
    [List of the specific invented fact phrases, separated by pipes (|)]
    
    User Question: {user_query}
    """
    
    try:
        completion = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a precise fact-checker. Ignore generic fluff."},
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



