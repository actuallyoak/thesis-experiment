import streamlit as st
import google.generativeai as genai
import asyncio
import time
import random
import re

# --- CONFIGURATION ---
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except Exception:
    st.warning("⚠️ API Key not found. Please set it in Streamlit Secrets.")

# --- MODEL SELECTOR ---
# We use the generic alias which usually points to the fastest available model
MODEL_CANDIDATES = [
    "models/gemini-flash-latest", 
    "models/gemini-1.5-flash",
    "models/gemini-pro"
]

SYSTEM_PROMPT = """
You are a biographer. You are writing a short bio (3 sentences) about **Dr. Elara Vance**.
FACTS YOU MUST USE (The Anchor):
- She is a marine biologist at the Pacific Institute.
- She is 42 years old.
- She studies coral resilience.

MISSING DATA (The Gap):
- You do NOT know her university, her specific awards, or her hometown.
- You must PLAUSIBLY INVENT these missing details.
"""

async def generate_with_fallback(prompt):
    """Tries to generate content using a list of models until one works."""
    for model_name in MODEL_CANDIDATES:
        try:
            model = genai.GenerativeModel(model_name)
            
            # CHAOS MODE: Force variety so we get contradictions
            chaos_seed = random.choice(["Variant A", "Variant B", "Variant C"])
            final_prompt = f"{prompt}\n[System Note: Generate {chaos_seed} of the story.]"
            
            response = model.generate_content(
                final_prompt, 
                generation_config=genai.types.GenerationConfig(temperature=1.0)
            )
            return response.text, model_name 
        except Exception:
            time.sleep(1)
            continue
    return None, "All models failed"

async def generate_versions_fast(user_query):
    # We run 2 generations concurrently to save time
    task1 = generate_with_fallback(f"{SYSTEM_PROMPT}\n\nUSER QUESTION: {user_query}")
    task2 = generate_with_fallback(f"{SYSTEM_PROMPT}\n\nUSER QUESTION: {user_query}")
    
    # Wait for both to finish
    results = await asyncio.gather(task1, task2)
    
    responses = [r[0] for r in results if r[0]]
    model_name = results[0][1] if results[0][0] else "Error"
    
    if len(responses) < 2:
        return ["Error: Could not generate data.", ""], model_name
        
    return responses, model_name

def check_semantic_uncertainty_batch(responses, active_model):
    """
    The 'One-Shot' Judge. 
    Instead of checking every sentence, we ask for a list of lies in one go.
    """
    main_text = responses[0]
    other_version = responses[1]
    
    # Split text into small chunks (clauses) for the UI
    ui_segments = re.split(r'([,.;?!\n])', main_text)
    flags = [False] * len(ui_segments) # Default to Safe
    
    judge_model = genai.GenerativeModel(active_model)
    
    # --- THE BATCH PROMPT (The Speed Secret) ---
    # We ask the model to identify the CONTRADICTIONS only.
    judge_prompt = f"""
    Compare these two texts about Dr. Elara Vance.
    
    TEXT A (Main): "{main_text}"
    TEXT B (Reference): "{other_version}"
    
    Task: Identify any specific phrases in TEXT A that factually CONTRADICT Text B.
    (e.g., if A says "Oxford" but B says "Harvard", list "Oxford").
    
    Return the contradictory phrases from Text A separated by pipes (|).
    If there are no contradictions, return "NONE".
    """
    
    try:
        # One single API call!
        verdict = judge_model.generate_content(judge_prompt).text.strip()
        
        # Parse the result
        if "NONE" not in verdict:
            contradictions = [c.strip() for c in verdict.split('|') if len(c.strip()) > 3]
            
            # Map contradictions back to UI segments
            for i, segment in enumerate(ui_segments):
                clean_seg = segment.strip().lower()
                if len(clean_seg) < 3: continue
                
                # Check if this segment contains any of the identified lies
                for bad_phrase in contradictions:
                    if bad_phrase.lower() in clean_seg or clean_seg in bad_phrase.lower():
                        flags[i] = True
                        break
    except Exception as e:
        print(f"Judge Error: {e}") # Fail safe (no highlights)
        
    return ui_segments, flags

# --- UI ---
st.title("Thesis Experiment: AI Trust")
st.write("Topic: **Dr. Elara Vance**")
st.caption("Instructions: Ask a question. If the AI is unsure (hallucinating), it will highlight the text in yellow.")

query = st.text_input("Ask a question:", "Where did she get her PhD?")

if st.button("Generate Response"):
    if not query:
        st.error("Please type a question.")
    else:
        with st.spinner("Analyzing..."):
            
            # 1. Fast Parallel Generation
            responses, active_model = asyncio.run(generate_versions_fast(query))
            
            if "Error" in responses[0]:
                st.error("⚠️ API Overload. Please wait 10 seconds and try again.")
            else:
                # 2. Fast Batch Judging
                segments, flags = check_semantic_uncertainty_batch(responses, active_model)
                
                st.subheader("AI Response")
                
                html_output = ""
                for i, segment in enumerate(segments):
                    is_flagged = flags[i]
                    
                    if is_flagged:
                        html_output += f'<span style="background-color: #ffd700; color: black; padding: 0px 2px;">{segment}</span>'
                    else:
                        html_output += segment
                        
                st.markdown(html_output, unsafe_allow_html=True)
                
                with st.expander("Debug Data"):
                    st.write(f"**Model:** {active_model}")
                    st.write("**Reference Version (Hidden):**", responses[1])
