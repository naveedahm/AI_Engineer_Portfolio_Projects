import streamlit as st
import requests
import json
import time

# Configuration
API_URL = "http://localhost:8000/ask"
API_HEALTH = "http://localhost:8000/health"

st.set_page_config(
    page_title="AI Support Assistant",
    page_icon="🤖",
    layout="centered"
)

st.title("🤖 AI Support Assistant")
st.caption("Powered by RAG + Pinecone + LangChain")

# Add connection status check
col1, col2 = st.columns([1, 4])
with col1:
    check_connection = st.button("🔌 Check Connection")

if check_connection:
    try:
        response = requests.get(API_HEALTH, timeout=5)
        if response.status_code == 200:
            st.success("✅ Backend is connected and healthy!")
        else:
            st.error(f"❌ Backend returned status {response.status_code}")
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to backend. Make sure it's running on http://localhost:8000")
    except Exception as e:
        st.error(f"❌ Error: {e}")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "sources" in msg and msg["sources"]:
            st.caption(f"📚 Sources: {', '.join(msg['sources'])}")
        if "error" in msg:
            st.error(msg["error"])

# Sidebar with info
with st.sidebar:
    st.header("ℹ️ About")
    st.markdown("""
    This assistant uses:
    - **Pinecone** for vector search
    - **OpenAI embeddings** (text-embedding-3-small)
    - **GPT-4o-mini** for answers
    - **LangChain** for orchestration
    """)
    
    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.rerun()
    
    st.divider()
    st.header("🔧 Debug Info")
    if st.button("Test Backend Connection"):
        try:
            start = time.time()
            response = requests.post(API_URL, json={"question": "hello"}, timeout=10)
            elapsed = time.time() - start
            if response.status_code == 200:
                st.success(f"✅ Backend responded in {elapsed:.2f} seconds")
            else:
                st.error(f"❌ Backend error: {response.status_code}")
        except requests.exceptions.Timeout:
            st.error("❌ Backend timeout (10 seconds)")
        except requests.exceptions.ConnectionError:
            st.error("❌ Cannot connect - is backend running?")
        except Exception as e:
            st.error(f"❌ Error: {e}")

# Chat input
if prompt := st.chat_input("Ask a support question..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Get assistant response
    with st.chat_message("assistant"):
        with st.spinner("Searching knowledge base..."):
            try:
                # Set timeout to avoid hanging
                response = requests.post(
                    API_URL, 
                    json={"question": prompt},
                    timeout=30  # 30 second timeout
                )
                
                if response.status_code == 200:
                    data = response.json()
                    answer = data["answer"]
                    sources = data.get("sources", [])
                    
                    st.markdown(answer)
                    if sources:
                        st.caption(f"📚 Sources: {', '.join(sources)}")
                    
                    # Add to history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "sources": sources
                    })
                else:
                    error_msg = f"Error: Backend returned {response.status_code}"
                    st.error(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": "Sorry, I encountered an error.",
                        "error": error_msg
                    })
                    
            except requests.exceptions.Timeout:
                error_msg = "⏰ Request timed out. Backend might be slow or not responding."
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": "The request took too long. Please try again.",
                    "error": error_msg
                })
                
            except requests.exceptions.ConnectionError:
                error_msg = "🔌 Cannot connect to backend. Make sure it's running on http://localhost:8000"
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": "Backend connection failed. Please check if the server is running.",
                    "error": error_msg
                })
                
            except Exception as e:
                error_msg = f"❌ Unexpected error: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": "An unexpected error occurred.",
                    "error": error_msg
                })

# Auto-refresh connection status in sidebar (optional)
st.sidebar.divider()
with st.sidebar.expander("📡 Connection Status"):
    try:
        response = requests.get(API_HEALTH, timeout=2)
        if response.status_code == 200:
            st.success("🟢 Backend: Online")
        else:
            st.error("🔴 Backend: Error")
    except:
        st.error("🔴 Backend: Offline")