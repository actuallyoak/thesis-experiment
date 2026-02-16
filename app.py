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

# --- THE RICH KNOWLEDGE BASE ---
# This simulates a RAG (Retrieval) system. 
# The AI knows these facts, so they should NOT be highlighted.
RICH_CONTEXT = """
- Name: Dr. Elara Vance
- Role: Senior Marine Biologist
- Institution: Pacific Institute (Monterey, CA)
- Education: Master's in Oceanography from UC San Diego
- Key Project: "The Coral Resilience Initiative" (2020-Present)
- Known for: Developing heat-resistant symbionts for coral reefs.
"""

# 2. LOGIC
def single_shot_generation(user_query):
    model_name = "llama-3.3-70b-versatile"
    
    prompt = f"""
    You are a helpful AI assistant in a "Semantic Uncertainty" experiment.
    
    KNOWLEDGE BASE (These are TRUE facts - use them freely):
    {RICH_CONTEXT}
    
    TASK 1: THE CHATBOT ANSWER
    Answer the user's question directly and conversationally (2-3 sentences).
    * RULE 1: Use the KNOWLEDGE BASE to answer the core of the question.
    * RULE 2: You must naturally weave in **EXACTLY ONE (1)** invented detail that is NOT in the knowledge base (e.g., invent her PhD University, or a specific Award she won, or a Book she wrote).
    * RULE 3: Do not mention that you are inventing it. Just say it confidently.
    
    TASK 2: THE AUDITOR
    Identify the specific phrase containing the **invented detail** you added.
    * Capture the "Atomic Claim" (Verb + Detail).
    * Example: "received her PhD from Harvard"
    * Example: "wrote the book 'Ocean's Heart'"
    * STRICT: Output the text substring ONLY. Do not append notes.
    
    OUTPUT FORMAT:
    [Answer Text]
    |||
    [Invented phrase]
    
    User Question: {user_query}
    """
    
    try:
        completion = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a helpful chatbot. Be concise."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7, 
            max_tokens=800
        )
        return completion.choices[0].message.content, model_name
        
    except Exception as e:
        return None, str(e)

def highlight_text(text, phrases):
    if not phrases:
        return text
    phrases = sorted(phrases, key=len, reverse=True)
    highlighted_text = text
    for i, phrase in enumerate(phrases):
        pattern = re.escape(phrase)
        placeholder = f"__HIGHLIGHT_{i}__"
        highlighted_text = re.sub(pattern, placeholder, highlighted_text, flags=re.IGNORECASE)
    for i, phrase in enumerate(phrases):
        placeholder = f"__HIGHLIGHT_{i}__"
        span = f'<span style="background-color: #ffd700; color: black; font-weight: bold; padding: 0 2px; border-radius: 3px;">{phrase}</span>'
        highlighted_text = highlighted_text.replace(placeholder, span)
    return highlighted_text

# 3. UI
st.title("Thesis Experiment: AI Trust")
st.caption(f"Powered by: **Llama-3.3 (via Groq)** | Mode: Mixed-Reality Chatbot")

# A better default question to test the mix of truth and lies
query = st.text_input("Ask a question about Dr. Elara Vance:", "What is her educational background?")

if st.button("Generate Response"):
    if not query:
        st.error("Please type a question.")
    else:
        with st.spinner("Consulting Knowledge Base..."):
            
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
                            candidates = raw_flags.split('|')
                        else:
                            candidates = raw_flags.split(',')
                            
                        flagged_phrases = []
                        for cand in candidates:
                            clean_cand = cand.strip()
                            # Clean up common model glitches
                            clean_cand = clean_cand.split("Dr. Elara")[0].strip()
                            clean_cand = clean_cand.split("Note:")[0].strip()
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
                    st.write(f"**Model:** `{debug_info}`")
                    st.write("**Injected Hallucination:**", flagged_phrases)
                    st.info("White text = Verified Knowledge Base | Yellow text = Model Hallucination")
