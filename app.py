import streamlit as st
import pandas as pd
from datetime import datetime
import db
import rag_engine

st.set_page_config(page_title="ApplyMaxxing | JobTrack AI", page_icon="🚀", layout="wide")

# Initialize DB
db.init_db()

st.title("🚀 ApplyMaxxing — JobTrack AI")
st.markdown("Automated job tracker with **Local RAG (Retrieval-Augmented Generation)** across your emails and applications.")

# --- Sidebar: Add New Job ---
st.sidebar.header("Add New Job")
with st.sidebar.form("add_job_form"):
    company = st.text_input("Company Name")
    role = st.text_input("Role (e.g. Software Engineer Intern)")
    platform = st.selectbox("Platform", ["LinkedIn", "Ashby", "Wellfound", "YCW", "Company Portal", "Other"])
    status = st.selectbox("Status", ["Saved (Deadline Approaching)", "Applied", "Online Assessment (OA)", "Interviewing", "Offer", "Rejected", "Ghosted"])
    deadline = st.date_input("Deadline")
    applied_date = st.date_input("Applied Date")
    job_link = st.text_input("Job Link")
    notes = st.text_area("Notes")
    
    submitted = st.form_submit_button("Add Job")
    if submitted:
        db.add_job(company, role, platform, status, deadline, applied_date, job_link, notes)
        st.sidebar.success("Job Added!")
        st.rerun()

# --- Main Navigation Tabs ---
tab_dashboard, tab_rag = st.tabs(["📋 Application Dashboard", "🤖 AI Q&A Assistant (RAG)"])

# ================= TAB 1: DASHBOARD =================
with tab_dashboard:
    jobs = db.get_all_jobs()
    if not jobs:
        st.info("No jobs tracked yet. Add one from the sidebar or run `email_scanner.py`!")
    else:
        df = pd.DataFrame(jobs, columns=['ID', 'Company', 'Role', 'Platform', 'Status', 'Deadline', 'Applied Date', 'Job Link', 'Notes'])
        
        # KPIs
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Tracked", len(df))
        col2.metric("Applied", len(df[df['Status'] == 'Applied']))
        col3.metric("OAs / Interviews", len(df[df['Status'].isin(['Online Assessment (OA)', 'Interviewing'])]))
        col4.metric("Offers", len(df[df['Status'] == 'Offer']))

        st.subheader("📋 Tracked Applications")
        
        for index, row in df.iterrows():
            with st.expander(f"{row['Company']} - {row['Role']}  |  Status: {row['Status']}"):
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.write(f"**Platform:** {row['Platform']}")
                    st.write(f"**Deadline:** {row['Deadline']}  |  **Applied:** {row['Applied Date']}")
                    st.write(f"**Link:** [Job Post]({row['Job Link']})")
                    st.write(f"**Notes:** {row['Notes']}")
                with c2:
                    status_options = ["Saved (Deadline Approaching)", "Applied", "Online Assessment (OA)", "Interviewing", "Offer", "Rejected", "Ghosted"]
                    curr_idx = status_options.index(row['Status']) if row['Status'] in status_options else 1
                    new_status = st.selectbox("Update Status", status_options, index=curr_idx, key=f"status_{row['ID']}")
                    if new_status != row['Status']:
                        db.update_job_status(row['ID'], new_status)
                        st.rerun()
                    
                    if st.button("Delete", key=f"del_{row['ID']}"):
                        db.delete_job(row['ID'])
                        st.rerun()

# ================= TAB 2: RAG CHAT ASSISTANT =================
with tab_rag:
    st.subheader("💬 Chat with your Job Application Knowledge Base")
    st.markdown("Ask anything about your past applications, email updates, assessment instructions, or interview requests. Grounded via **Gemini Embeddings + RAG**.")
    
    # Quick Prompts
    st.markdown("**Suggested questions:**")
    quick_cols = st.columns(3)
    preset_query = None
    if quick_cols[0].button("🔍 Which companies sent me OAs?"):
        preset_query = "Which companies have sent me an Online Assessment or technical test?"
    if quick_cols[1].button("📉 Show recent rejections"):
        preset_query = "What companies have sent rejection emails and when?"
    if quick_cols[2].button("⚡ Have I applied to trading firms?"):
        preset_query = "Have I applied to any trading or quantitative finance firms?"

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "👋 Hi Abhigyan! I'm your job search AI assistant. Ask me anything about your tracked jobs or email updates."}
        ]

    # Display chat messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "sources" in msg and msg["sources"]:
                with st.expander("📚 Retrieved Context Sources"):
                    for src in msg["sources"]:
                        st.markdown(f"• **{src['company']}** — *{src['subject']}* ({src['date']}) | Score: `{src['score']}`")

    # Chat input
    user_input = st.chat_input("Ask a question about your applications...")
    query = preset_query or user_input

    if query:
        # Display user message
        st.session_state.messages.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.markdown(query)

        # Generate RAG response
        with st.chat_message("assistant"):
            with st.spinner("Searching application knowledge base & email context..."):
                rag_result = rag_engine.ask_rag(query)
                answer = rag_result["answer"]
                sources = rag_result.get("sources", [])
                
                st.markdown(answer)
                if sources:
                    with st.expander("📚 Retrieved Context Sources"):
                        for src in sources:
                            st.markdown(f"• **{src['company']}** — *{src['subject']}* ({src['date']}) | Score: `{src['score']}`")

        # Save assistant message
        st.session_state.messages.append({"role": "assistant", "content": answer, "sources": sources})
