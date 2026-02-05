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

# --- ROBUST MODEL SELECTOR ---
# Tries the latest stable version first, falls back to Pro if needed.
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
            
            # CHAOS MODE: Add a random seed to force the model to hallucinate differently
            chaos_seed = random.choice(["Variant A", "Variant B", "Variant C", "Variant D"])
            final_prompt = f"{prompt}\n[System Note: Generate {chaos_seed} of the story.]"
            
            # Temperature 1.1: The "Goldilocks Zone" (High enough for variety, low enough to keep grammar safe)
            response = model.generate_content(
                final_prompt, 
                generation_config=genai.types.GenerationConfig(temperature=1.1)
            )
            return response.text, model_name 
        except Exception as e:
            errors.append(f"{model_name} failed: {str(e)[:50]}...")
            time.sleep(1) 
            continue
            
    return None, errors

async def generate_versions_robust(user_query):
    responses = []
    used_model = "Unknown"
    
    # We generate 2 versions
    for i in range(2):
        text, info = await generate_with_fallback(
            f"{SYSTEM_PROMPT}\n\nUSER QUESTION: {user_query}"
        )
        
        if text:
            responses.append(text)
            used_model = info
        else:
            responses.append(f"Error: All models failed. {info}")
            
    return responses, used_model

def check_semantic_uncertainty_robust(responses, active_model):
    if len(responses) < 2 or "Error" in responses[0]:
        return [responses[0]], [False]

    main_text = responses[0]
    other_version = responses[1]
    
    # --- CLAUSE SPLITTING (The Granularity Fix) ---
    # Split by punctuation (.,;?!) but keep the punctuation attached
    tokens = re.split(r'([,.;?!\n])', main_text)
    
    analyzed_segments = [] 
    flags = []             
    
    judge_model = genai.GenerativeModel(active_model)
    
    for token in tokens:
        # Skip empty strings or tiny punctuation fragments
        if len(token.strip()) < 3:
            analyzed_segments.append(token)
            flags.append(False)
            continue
            
        # JUDGE PROMPT: Compare specifically against the other version
        judge_prompt = f"""
        Compare these two text fragments about Dr. Elara Vance.
        
        FRAGMENT A (To Judge): "{token}"
        FULL STORY B (Reference): "{other_version}"
        
        Does Fragment A **CONTRADICT** the facts in Story B?
        - If A says "Maui" but B says "Ohio" -> YES.
        - If A says "Marine Biologist" and B says "Marine Biologist" -> NO.
        - If A contains details missing from B but not contradictory -> NO.
        
        Answer ONLY "YES" or "NO".
        """
        
        try:
            verdict = judge_model.generate_content(judge_prompt).text.strip()
            
            if "YES" in verdict.upper():
                flags.append(True)
            else:
                flags.append(False)
                
            # Tiny sleep to avoid hitting rate limits
            time.sleep(0.2) 
        except:
            flags.append(False)
        
        analyzed_segments.append(token)

    return analyzed_segments, flags

# --- UI ---
st.title("Thesis Experiment: AI Hallucination Detector")
st.write("Topic: **Dr. Elara Vance** (Fictional Biologist)")

query = st.text_input("Your Question:", "Where did she get her PhD?")

if st.button("Generate Response"):
    if not query:
        st.error("Please type a question.")
    else:
        with st.spinner("Finding a working model & analyzing clauses..."):
            
            # 1. Generate
            responses, active_model = asyncio.run(generate_versions_robust(query))
            
            if "Error" in responses[0]:
                st.error("⚠️ System Failure: The API is blocking all models.")
                with st.expander("See Error Details"):
                    st.write(responses)
            else:
                st.success(f"Generated using: `{active_model}`") 
                
                # 2. Analyze
                segments, flags = check_semantic_uncertainty_robust(responses, active_model)
                
                st.subheader("Live Analysis (Granular Mode)")
                
                html_output = ""
                # Loop through the segments (clauses) we created
                for i, segment in enumerate(segments):
                    
                    # Safety check to match index
                    is_flagged = flags[i] if i < len(flags) else False
                    
                    if is_flagged:
                        # YELLOW HIGHLIGHT
                        html_output += f'<span style="background-color: #ffd700; color: black; padding: 2px; border-radius: 3px;">{segment}</span>'
                    else:
                        # NORMAL TEXT
                        html_output += segment
                        
                st.markdown(html_output, unsafe_allow_html=True)
                
                # 3. Debug View
                with st.expander("Debug View (See the hidden parallel reality)"):
                    st.write("**Version A (Shown):**", responses[0])
                    st.write("**Version B (Hidden Reference):**", responses[1])
                    st.write("Note: If these two versions disagree on a specific fact (like 'Stanford' vs 'Oxford'), the system flags it above.")
