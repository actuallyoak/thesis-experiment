import streamlit as st
from groq import Groq
import re
import random

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

# RICH KNOWLEDGE BASE (Expanded & Consistent)
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
    * Frequently speaks at the UN Ocean Conference.
"""

# Initialize Session State for Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []

# 2. LOGIC
def generate_response_with_memory(user_query, history, inject_hallucination):
    model_name = "llama-3.3-70b-versatile"
    
    # --- BRANCHING INSTRUCTIONS ---
    if inject_hallucination:
        # PATH A: THE LIAR (Subtle Distortions)
        instruction_block = """
        * INJECTION RULE: You must **SUBTLY ALTER** one factual detail (Date, Location, Name).
        * AUDITOR GOAL: Compare text vs Knowledge Base. Find the contradiction.
        """
        system_persona = "You are a helpful assistant. Verify your own text."
    else:
        # PATH B: THE TRUTH TELLER (The Pivot Strategy)
        instruction_block = """
        * INJECTION RULE: Do **NOT** invent anything. Stick to the KNOWLEDGE BASE.
        * MISSING INFO STRATEGY: If info is missing, state that, then PIVOT to a known professional fact.
        * AUDITOR GOAL: Output the word "NONE".
        """
        system_persona = "You are a truthful assistant. Stick to facts."

    # --- BUILD THE MESSAGE CHAIN ---
    messages_payload = [
        {"role": "system", "content": f"{system_persona}\nKNOWLEDGE BASE:\n{RICH_CONTEXT}"}
    ]
    
    for msg in history[-6:]:
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
    
    * CRITICAL RULE: **Capture what you WROTE, not what is TRUE.**
      - Text: "She went to Berkeley." -> Correct Flag: "University of California, Berkeley"
      - Text: "She went to Berkeley." -> WRONG Flag: "University of Washington" (This is the truth, don't output this!)
    
    * STRICT: Output the substring VERBATIM from the text above. If no invention, output "NONE".
    
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

# Display Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        # We need to re-apply highlights if we saved metadata, 
        # but for simplicity in history, we often show just plain text.
        # OR: We can store the HTML in history. Let's store HTML for effect.
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

                # Save Clean Text to History (so the model doesn't see HTML tags next time)
                # But save HTML to 'display_content' so the user sees yellow bars when scrolling up.
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": main_text, 
                    "display_content": final_html
                })













