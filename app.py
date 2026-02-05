import streamlit as st
import google.generativeai as genai

# 1. Config
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except Exception:
    st.warning("⚠️ API Key not found. Please set it in Streamlit Secrets.")

st.title("🔍 Gemini Model Diagnostic")

if st.button("List My Available Models"):
    try:
        st.info("Asking Google API for valid model names...")
        
        # 2. The Truth Query
        found_any = False
        for m in genai.list_models():
            # We only care about models that can write text (generateContent)
            if 'generateContent' in m.supported_generation_methods:
                st.success(f"✅ AVAILABLE: {m.name}")
                found_any = True
                
        if not found_any:
            st.error("❌ No text-generation models found. Your API Key might be invalid or restricted.")
            
    except Exception as e:
        st.error(f"⚠️ Connection Error: {e}")
