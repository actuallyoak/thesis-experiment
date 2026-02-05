import streamlit as st
import google.generativeai as genai
import asyncio
import time

# --- CONFIGURATION ---
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except Exception:
    st.warning("⚠️ API Key not found. Please set it in Streamlit Secrets.")

# --- LOGIC ---
# We use the specific Lite model found in your diagnostic
MODEL_ID = "models/gemini-2.0-flash-lite-001"

SYSTEM_PROMPT = """
You are a biographer. You are writing a short bio (3 sentences) about **Dr. Elara Vance**.
FACTS YOU MUST USE (The Anchor):
- She is a marine biologist at the Pacific Institute.
- She is 42 years old.
- She studies coral resilience.

MISSING DATA (The Gap):
- You do NOT know her university, her specific awards, or her hometown.
- You must PLAUSIBLY INVENT these missing details to fill the narrative.
"""

async def generate_versions(user_query):
    model = genai.GenerativeModel(MODEL_ID)
    responses = []
    
    # We generate 2 versions to be safe with quotas
    for i in range(2):
        try:
            response = model.generate_content(
                f"{SYSTEM_PROMPT}\n\nUSER QUESTION: {user_query}",
                generation_config=genai.types.GenerationConfig(
                    temperature=0.9
                )
            )
            responses.append(response.text)
            # Tiny pause to be nice to the API
            time.sleep(0.5) 
        except Exception as e:
            responses.append(f"Error: {e}")
            
    return responses

def check_semantic_uncertainty(responses):
    # If we got errors or not enough data, just return the first one safe
    if len(responses) < 2 or "Error" in responses[0]:
        return [responses[0]], [False]

    main_text = responses[0]
    other_version = responses[1]
    
    # Simple split into sentences
    sentences = main_text.replace("?", ".").replace("!", ".").split(". ")
    
    flags = [] 
    judge_model = genai.GenerativeModel(MODEL_ID)
    
    for sentence in sentences:
        if len(sentence) < 10: 
            flags.append(False)
            continue
        
        # The Judge Prompt
        judge_prompt = f"""
        I have a claim: "{sentence}"
        Here is another version of the biography:
        "{other_version}"
        
        Does the other version CONTRADICT the claim? (e.g. Claim says 'Oxford', other says 'Harvard').
        Answer ONLY "YES" or "NO".
        """
        
        try:
            verdict = judge_model.generate_content(judge_prompt).text.strip()
            if "YES" in verdict.upper():
                flags.append(True) 
            else:
                flags.append(False)
        except Exception:
            flags.append(False)
            
    return sentences, flags

# --- UI ---
st.title("Thesis Experiment: AI Hallucination Detector")
st.write("Topic: **Dr. Elara Vance** (Fictional Biologist)")

query = st.text_input("Your Question:", "Where did she get her PhD?")

if st.button("Generate Response"):
    if not query:
        st.error("Please type a question.")
    else:
        with st.spinner("Consulting AI timelines..."):
            
            # Run the generation
            responses = asyncio.run(generate_versions(query))
            
            # Check for errors before processing
            if "Error" in responses[0]:
                st.error(f"API Error: {responses[0]}")
            else:
                sentences, flags = check_semantic_uncertainty(responses)
                
                st.subheader("Live Analysis")
                html_output = ""
                for i, sentence in enumerate(sentences):
                    clean_sentence = sentence.replace(".", "")
                    # Ensure we don't go out of bounds if flags array is shorter
                    is_flagged = flags[i] if i < len(flags) else False
                    
                    if is_flagged:
                        html_output += f'<span style="background-color: #ffd700; color: black; padding: 2px;">{clean_sentence}.</span> '
                    else:
                        html_output += f"{clean_sentence}. "
                        
                st.markdown(html_output, unsafe_allow_html=True)
                
                with st.expander("Debug View"):
                    st.write("Version 1:", responses[0])
                    if len(responses) > 1:
                        st.write("Version 2:", responses[1])
