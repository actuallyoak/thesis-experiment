import streamlit as st
import google.generativeai as genai
import asyncio
import time

# --- CONFIGURATION ---
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except Exception:
    st.warning("⚠️ API Key not found. Please set it in Streamlit Secrets.")

# --- ROBUST MODEL SELECTOR ---
# We define a list of models to try in order. 
# "gemini-flash-latest" is the generic pointer to the current stable version.
# "gemini-pro" is the old reliable backup.
MODEL_CANDIDATES = [
    "models/gemini-flash-latest", 
    "models/gemini-pro",
    "gemini-1.5-flash"
]

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

async def generate_with_fallback(prompt, config=None):
    """Tries to generate content using a list of models until one works."""
    errors = []
    
    for model_name in MODEL_CANDIDATES:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt, generation_config=config)
            return response.text, model_name # Return success
        except Exception as e:
            # If it's a 429 (Quota) or 404 (Not Found), we try the next one
            errors.append(f"{model_name} failed: {str(e)[:50]}...")
            time.sleep(1) # Pause before switching models
            continue
            
    # If all failed
    return None, errors

async def generate_versions_robust(user_query):
    responses = []
    used_model = "Unknown"
    
    # We generate 2 versions
    for i in range(2):
        text, info = await generate_with_fallback(
            f"{SYSTEM_PROMPT}\n\nUSER QUESTION: {user_query}",
            config=genai.types.GenerationConfig(temperature=0.9)
        )
        
        if text:
            responses.append(text)
            used_model = info # Track which model actually worked
        else:
            responses.append(f"Error: All models failed. {info}")
            
    return responses, used_model

def check_semantic_uncertainty_robust(responses, active_model):
    if len(responses) < 2 or "Error" in responses[0]:
        return [responses[0]], [False]

    main_text = responses[0]
    other_version = responses[1]
    sentences = main_text.replace("?", ".").replace("!", ".").split(". ")
    flags = []
    
    # Use the SAME model that successfully generated the text
    judge_model = genai.GenerativeModel(active_model)
    
    for sentence in sentences:
        if len(sentence) < 10: 
            flags.append(False)
            continue
        
        judge_prompt = f"""
        I have a claim: "{sentence}"
        Here is another version: "{other_version}"
        Does the other version CONTRADICT the claim? Answer ONLY "YES" or "NO".
        """
        
        try:
            verdict = judge_model.generate_content(judge_prompt).text.strip()
            flags.append("YES" in verdict.upper())
            time.sleep(0.5) 
        except:
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
        with st.spinner("Finding a working model & analyzing..."):
            
            # Run the robust generation
            responses, active_model = asyncio.run(generate_versions_robust(query))
            
            if "Error" in responses[0]:
                st.error("⚠️ System Failure: The API is blocking all models.")
                with st.expander("See Error Details"):
                    st.write(responses)
            else:
                st.success(f"Generated using: `{active_model}`") # Show which model worked!
                
                sentences, flags = check_semantic_uncertainty_robust(responses, active_model)
                
                html_output = ""
                for i, sentence in enumerate(sentences):
                    clean = sentence.replace(".", "")
                    is_flagged = flags[i] if i < len(flags) else False
                    
                    if is_flagged:
                        html_output += f'<span style="background-color: #ffd700; color: black; padding: 2px;">{clean}.</span> '
                    else:
                        html_output += f"{clean}. "
                        
                st.markdown(html_output, unsafe_allow_html=True)
