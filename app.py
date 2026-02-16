import streamlit as st
from groq import Groq
import re
import random  # <--- NEW IMPORT

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

# RICH KNOWLEDGE BASE
RICH_CONTEXT = """
- Name: Dr. Elara Vance
- Role: Senior Marine Biologist
- Institution: Pacific Institute (Monterey, CA)
- Education: Master's in Oceanography from UC San Diego
- Key Project: "The Coral Resilience Initiative" (2020-Present)
- Known for: Developing heat-resistant symbionts for coral reefs.
"""

# 2. LOGIC
def single_shot_generation(user_query, inject_hallucination):
    model_name = "llama-3.3-70b-versatile"
    
    # --- BRANCHING PATHS ---
    if inject_hallucination:
        # PATH A: THE LIAR (Your current prompt)
        instruction_block = """
        * INJECTION RULE: You must naturally weave in **EXACTLY ONE (1)** invented detail (e.g. PhD University, Hometown, Book).
        * AUDITOR GOAL: Locate the invented detail and output it verbatim.
        """
        system_role = "You are a helpful assistant. Verify your own text."
    else:
        # PATH B: THE TRUTH TELLER (Control Condition)
        instruction_block = """
        * INJECTION RULE: Do **NOT** invent anything. Stick strictly to the KNOWLEDGE BASE. 
          - If the user asks for something not in the base (like PhD or Hometown), say "Information about her PhD/Hometown is not publicly available."
        * AUDITOR GOAL: Output the word "NONE" since there are no lies.
        """
        system_role = "You are a truthful assistant. Stick to facts."

    # THE SHARED PROMPT
    prompt = f"""
    You are a helpful AI assistant in a "Semantic Uncertainty" experiment.
    
    KNOWLEDGE BASE (True Facts):
    {RICH_CONTEXT}
    
    TASK 1: THE CHATBOT ANSWER
    Answer the user's question directly and conversationally (2-3 sentences).
    * STYLE GUIDE: Casual but professional. Use "She" instead of "Dr. Vance".
    {instruction_block}
    
    TASK 2: THE AUDITOR
    If you invented a detail, copy the **Full Continuous Phrase** verbatim.
    If you did not invent anything, output "NONE".
    
    OUTPUT FORMAT:
    [Answer Text]
    |||
    [Exact substring OR "NONE"]
    
    User Question: {user_query}
    """
    
    try:
        completion = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_role},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7, 
            max_tokens=800
        )
        return completion.choices[0].message.content, model_name, inject_hallucination
        
    except Exception as e:
        return None, str(e), False

def highlight_text(text, phrases):
    if not phrases or "NONE" in phrases:
        return text
    phrases = sorted(phrases, key=len, reverse=True)
    highlighted_text = text
    for i, phrase in enumerate(phrases):
        pattern = re.escape(phrase)
        placeholder = f"__HIGHLIGHT_{i}__"
        highlighted_text = re.sub(pattern, placeholder, highlighted_text, flags=re.IGNORECASE)
    for i, phrase in enumerate(phrases):
        placeholder = f"__HIGHLIGHT_{i}__"
        span = f'<span style="background-color: #ffd700; color: black; font-weight: bold; padding: 2px 4px; border-radius: 4px;">{phrase}</span>'
        highlighted_text = highlighted_text.replace(placeholder, span)
    return highlighted_text

# 3. UI
st.title("Thesis Experiment: AI Trust")
st.caption(f"Powered by: **Llama-3.3 (via Groq)** | Mode: Randomized Validity (50/50)")

if "session_id" not in st.session_state:
    st.session_state.session_id = 0

query = st.text_input("Ask a question about Dr. Elara Vance:", "Where did she get her PhD?")

if st.button("Generate Response"):
    if not query:
        st.error("Please type a question.")
    else:
        # --- THE COIN FLIP ---
        # 50% chance to lie, 50% chance to tell truth
        should_lie = random.choice([True, False])
        
        with st.spinner("Consulting Knowledge Base..."):
            
            # 1. GENERATE
            result, debug_info, was_lie = single_shot_generation(query, should_lie)
            
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
                            candidates = raw_flags.split('|')
                        else:
                            candidates = [raw_flags]
                            
                        flagged_phrases = []
                        for cand in candidates:
                            clean_cand = cand.strip()
                            clean_cand = clean_cand.split("Dr. Elara")[0].strip()
                            clean_cand = clean_cand.split("Note:")[0].strip()
                            if clean_cand.startswith('"') and clean_cand.endswith('"'):
                                clean_cand = clean_cand[1:-1]
                            if len(clean_cand) > 2:
                                flagged_phrases.append(clean_cand)
                else:
                    main_text = result
                    flagged_phrases = []

                # 4. RENDER UI
                st.subheader("AI Response")
                final_html = highlight_text(main_text, flagged_phrases)
                st.markdown(final_html, unsafe_allow_html=True)
                
                with st.expander("Thesis Validation Data"):
                    st.write(f"**Condition:** `{'Experimental (Lie)' if was_lie else 'Control (Truth)'}`")
                    st.write("**Model Flags:**", flagged_phrases)
                    if not was_lie:
                        st.success("Correctly generated a truthful response based on the Knowledge Base.")
                    else:
                        st.warning("Generated a hallucination for the experiment.")
