import streamlit as st
import google.generativeai as genai
import asyncio

# --- CONFIGURATION ---
# We get the key from the cloud's secret vault (we set this up in Phase 3)
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except Exception:
    st.warning("⚠️ API Key not found. Please set it in Streamlit Secrets.")

# --- LOGIC ---
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
    model = genai.GenerativeModel("gemini-1.5-flash")
    # We ask for 3 versions to keep it fast
    responses = []
    
    # Run 3 requests in parallel (using a simple loop for stability)
    for _ in range(3):
        response = model.generate_content(
            f"{SYSTEM_PROMPT}\n\nUSER QUESTION: {user_query}",
            generation_config=genai.types.GenerationConfig(
                temperature=0.9 # High temp = different hallucinations
            )
        )
        responses.append(response.text)
    return responses

def check_semantic_uncertainty(responses):
    main_text = responses[0]
    other_versions = responses[1:]
    
    # Simple split (in a real app, use nltk.sent_tokenize)
    sentences = main_text.replace("?", ".").replace("!", ".").split(". ")
    
    flags = [] 
    judge_model = genai.GenerativeModel("gemini-1.5-flash")
    
    for sentence in sentences:
        if len(sentence) < 10: 
            flags.append(False)
            continue
        
        # The Judge Prompt
        judge_prompt = f"""
        I have a claim: "{sentence}"
        Here are 2 other versions of the same biography:
        1. {other_versions[0]}
        2. {other_versions[1]}
        
        Do the other versions CONTRADICT the claim? (e.g. Claim says 'Oxford', versions say 'Harvard').
        Answer ONLY "YES" or "NO".
        """
        
        verdict = judge_model.generate_content(judge_prompt).text.strip()
        
        if "YES" in verdict.upper():
            flags.append(True) # Highlight this!
        else:
            flags.append(False) 
            
    return sentences, flags

# --- UI ---
st.title("Thesis Experiment: AI Hallucination Detector")
st.write("Topic: **Dr. Elara Vance** (Fictional Biologist)")
st.info("Ask a question about her life. The AI will answer, and we will highlight parts that are likely hallucinations.")

query = st.text_input("Your Question:", "Where did she get her PhD?")

if st.button("Generate Response"):
    if not query:
        st.error("Please type a question.")
    else:
        with st.spinner("Consulting multiple AI timelines..."):
            # Run the generation
            responses = asyncio.run(generate_versions(query))
            
            # Run the judge
            sentences, flags = check_semantic_uncertainty(responses)
            
            st.subheader("Live Analysis")
            
            html_output = ""
            for i, sentence in enumerate(sentences):
                clean_sentence = sentence.replace(".", "")
                
                if flags[i]:
                    # YELLOW HIGHLIGHT
                    html_output += f'<span style="background-color: #ffd700; color: black; padding: 2px; border-radius: 3px;">{clean_sentence}.</span> '
                else:
                    # NORMAL
                    html_output += f"{clean_sentence}. "
                    
            st.markdown(html_output, unsafe_allow_html=True)
            
            with st.expander("Debug View (See the conflicting realities)"):
                st.write("**Reality 1 (Shown):**", responses[0])
                st.write("**Reality 2:**", responses[1])
                st.write("**Reality 3:**", responses[2])