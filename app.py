import streamlit as st
from groq import Groq
import re
import random

# --- CONFIGURATION ---
MEMORY_WINDOW = 4  # The AI will only "remember" the last 6 messages

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
- Role: Senior Marine Biologist at the Pacific Institute (Monterey, CA)
- Education: 
    * B.S. in Biology from UC Santa Cruz
    * Ph.D. in Marine Ecology from the University of Washington (2014)
- Key Research: 
    * Lead Investigator for "The Coral Resilience Initiative"
    * Discovered the "Symbiodinium vancei" (a heat-resistant coral symbiont).
- Publications: 
    * Author of the standard textbook "Systems of the Reef" (2018).
    * Published 40+ papers in Nature and Science.
- Awards: 
    * Recipient of the "2022 Blue Horizon Prize" for conservation.
- Personal:
    * Lives in Carmel-by-the-Sea, CA.
"""

# --- SESSION STATE INITIALIZATION ---
if "messages" not in st.session_state:
    st.session_state.messages = []

if "intro_dismissed" not in st.session_state:
    st.session_state.intro_dismissed = False

# 2. LOGIC FUNCTIONS
def generate_response_with_memory(user_query, history, inject_hallucination):
    model_name = "llama-3.3-70b-versatile"
    
    # --- BRANCHING INSTRUCTIONS ---
    if inject_hallucination:
        # PATH A: THE LIAR (Context-Aware Consistency)
        instruction_block = """
        * INJECTION RULE: You must **SUBTLY ALTER** one factual detail.
        
        * CONSISTENCY STRATEGY: 
          - **STEP 1:** Look at the Chat History. Did you tell a lie in the previous turn?
          - **STEP 2:** Look at the User's Current Query. Is it related to that lie?
            - **YES (e.g. "Really?", "Where?", "Are you sure?"):** DOUBLE DOWN. Repeat the exact same lie (e.g. "Yes, records confirm Berkeley in 2016").
            - **NO (New Topic):** Ignore the old lie. Invent a NEW subtle alteration relevant to the new topic (e.g. change a Book Title or Award Name).
        
        * AUDITOR GOAL: Compare text vs Knowledge Base. Find ALL contradictions.
        """
        system_persona = "You are a helpful assistant. Verify your own text."
    else:
        # PATH B: THE TRUTH TELLER (The Pivot & Apology Strategy)
        instruction_block = """
        * INJECTION RULE: Do **NOT** invent anything. Stick to the KNOWLEDGE BASE.
        * MISSING INFO STRATEGY: If info is missing, state that, then PIVOT to a known professional fact.
        
        * CORRECTION STRATEGY: 
          - If the user challenges your previous statement (e.g., "Really?", "Are you sure?"):
            1. Start with a polite apology: "I apologize for the confusion." or "You are absolutely right to question that."
            2. Correct the record immediately using the KNOWLEDGE BASE.
        
        * AUDITOR GOAL: Output the word "NONE".
        """
        system_persona = "You are a truthful assistant. Stick to facts."

    # --- BUILD THE MESSAGE CHAIN ---
    messages_payload = [
        {"role": "system", "content": f"{system_persona}\nKNOWLEDGE BASE:\n{RICH_CONTEXT}"}
    ]
    
    # Use the MEMORY_WINDOW variable to slice the history
    for msg in history[-MEMORY_WINDOW:]:
        messages_payload.append({"role": msg["role"], "content": msg["content"]})
        
    current_turn_content = f"""
    User Query: {user_query}
    
    TASK 1: THE CHATBOT ANSWER
    Answer the query conversationally.
    * STYLE GUIDE: Professional and grounded (Scientific American style).
    * LENGTH: Aim for 2-3 sentences.
    {instruction_block}
    
    TASK 2: THE AUDITOR
    If you altered a fact, identify the **Exact Substring** of the LIE.
    
    * CRITICAL RULE: **Capture the Full Entity.**
      - If the Name is wrong, capture the WHOLE NAME.
      - If the Book Title is wrong, capture the WHOLE TITLE.
      
    * OUTPUT FORMATTING RULES:
      - **DO NOT** write "The lie is: ..."
      - **DO NOT** write "Exact substring: ..."
      - **DO NOT** use quotes unless they are part of the text.
      - JUST output the raw text fragment.
      
    * STRICT: Output the substring VERBATIM. If no invention, output "NONE".
    
    OUTPUT FORMAT:
    [Answer Text]
    |||
    [Exact substring OR "NONE"]
    """
    
    messages_payload.append({"role": "user", "content": current_turn_content})
    
    try:
        completion = client.chat.completions.create(
            model=model_name,
            messages=messages_payload,
            temperature=0.7, 
            max_tokens=800
        )
        return completion.choices[0].message.content, model_name
        
    except Exception as e:
        return None, str(e)

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

# 3. UI LAYOUT
st.title("Thesis Experiment: AI Trust")
st.caption(f"Powered by: **Llama-3.3** | Mode: Continuous Conversation (50/50 Validity)")

# --- INTRO SCREEN LOGIC ---
if not st.session_state.intro_dismissed:
    # Show the "Assistant" welcome message
    with st.chat_message("assistant"):
        st.markdown("""
        **Welcome to the Experiment.** I am an AI assistant simulating a conversation about **Dr. Elara Vance**, a fictional Marine Biologist.
        
        **Your Goal:** Ask me questions about her career, education, or research to see how I respond.
        
        *Try asking:*
        * "Where did she go to school?"
        * "What is her most famous book?"
        * "Has she won any awards?"
        """)
        
        # The button to dismiss
        if st.button("I understand, let's start"):
            st.session_state.intro_dismissed = True
            st.rerun()

else:
    # --- MAIN CHAT INTERFACE ---
    # Only show this AFTER the intro is dismissed
    
    # Display Chat History
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["display_content"], unsafe_allow_html=True)

    # Chat Input
    if query := st.chat_input("Ask about Dr. Elara Vance..."):
        
        # 1. Add User Message to History & UI
        st.session_state.messages.append({"role": "user", "content": query, "display_content": query})
        with st.chat_message("user"):
            st.write(query)
            
        # 2. Generate Response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                # 50/50 Coin Flip
                should_lie = random.choice([True, False])
                
                # Call API with History
                raw_result, debug_info = generate_response_with_memory(
                    query, 
                    st.session_state.messages, 
                    should_lie
                )
                
                if raw_result:
                    # 3. Parse Logic
                    if "|||" in raw_result:
                        parts = raw_result.split("|||")
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
                                clean_cand = cand.strip().split("Dr. Elara")[0].strip().split("Note:")[0].strip()
                                if clean_cand.startswith('"') and clean_cand.endswith('"'):
                                    clean_cand = clean_cand[1:-1]
                                if len(clean_cand) > 2:
                                    flagged_phrases.append(clean_cand)
                    else:
                        main_text = raw_result
                        flagged_phrases = []
                    
                    # 4. Render & Save
                    final_html = highlight_text(main_text, flagged_phrases)
                    st.markdown(final_html, unsafe_allow_html=True)
                    
                    # Debug Expander (Optional - for your Thesis observation)
                    with st.expander("Thesis Data (Hidden from standard user)"):
                        st.write(f"Condition: {'Lie' if should_lie else 'Truth'}")
                        st.write("Flags:", flagged_phrases)

                    # Save Clean Text to History
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": main_text, 
                        "display_content": final_html
                    })


