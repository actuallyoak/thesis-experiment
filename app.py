import streamlit as st
import google.generativeai as genai
import re
import time

# --- CONFIGURATION ---
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except Exception:
    st.error("⚠️ API Key missing.")

# --- THE SPEED STRATEGY: ONE COMPLEX CALL ---
# We ask the model to generate the bio AND do the self-correction in a single pass.
# This prevents "Rate Limit" errors because it counts as only 1 request.
def single_shot_generation(user_query):
    # Try different models in order of speed/availability
    candidates = ["models/gemini-1.5-flash", "models/gemini-2.0-flash-lite-001", "models/gemini-pro"]
    
    prompt = f"""
    You are an experiment simulator.
    Task 1: Write a short 3-sentence bio of Dr. Elara Vance (Marine Biologist, 42, Pacific Institute).
    Task 2: Internally generate a SECOND, conflicting version where you invent different details (University, Hometown, Awards).
    Task 3: Compare the two. Identify phrases in the First Bio that contradict the Second Bio.
    
    OUTPUT FORMAT:
    [The First Bio Text]
    |||
    [List of contradicting phrases separated by commas]
    
    User Question: {user_query}
    """
    
    for model_name in candidates:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            return response.text
        except Exception:
            continue # Try next model if one fails
            
    return "Error: System Busy ||| None"

# --- UI ---
st.title("Thesis Experiment: AI Trust")
st.write("Topic: **Dr. Elara Vance**")

query = st.text_input("Ask a question:", "Where did she get her PhD?")

if st.button("Generate Response"):
    if not query:
        st.error("Enter a question.")
    else:
        with st.spinner("Analyzing..."):
            # 1. THE SINGLE CALL
            raw_result = single_shot_generation(query)
            
            # 2. PARSE THE HIDDEN DATA
            if "|||" in raw_result:
                parts = raw_result.split("|||")
                main_text = parts[0].strip()
                # Clean up the list of lies
                raw_flags = parts[1].lower().strip()
                flagged_phrases = [x.strip() for x in raw_flags.split(',') if len(x.strip()) > 3]
            else:
                main_text = raw_result
                flagged_phrases = []

            # 3. RENDER WITH HIGHLIGHTS
            st.subheader("AI Response")
            
            # Split text into chunks for highlighting
            # We use a regex to keep punctuation attached
            segments = re.split(r'([,.;?!\n])', main_text)
            
            html_output = ""
            for seg in segments:
                # Check if this segment contains a flagged phrase
                is_bad = False
                for bad in flagged_phrases:
                    if bad in seg.lower() or seg.lower() in bad:
                        is_bad = True
                        break
                
                if is_bad:
                    html_output += f'<span style="background-color: #ffd700; padding: 2px;">{seg}</span>'
                else:
                    html_output += seg
                    
            st.markdown(html_output, unsafe_allow_html=True)
            
            # Debugging for you (Hidden from standard users usually, but good for thesis defense)
            with st.expander("Thesis Data (How it worked)"):
                st.write("**Architecture:** Single-Shot CoT (1 API Call)")
                st.write("**Detected Contradictions:**", flagged_phrases)
