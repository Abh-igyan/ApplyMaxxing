import streamlit as st
import pandas as pd
from datetime import datetime
import db

st.set_page_config(page_title="JobTrack AI", layout="wide")

# Initialize DB
db.init_db()

st.title("🚀 JobTrack AI")
st.markdown("Track your internship and job applications across LinkedIn, Ashby, Wellfound, and more. Connect your email to track OAs and Interviews.")

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

# --- Main Dashboard ---
jobs = db.get_all_jobs()
if not jobs:
    st.info("No jobs tracked yet. Add one from the sidebar!")
else:
    df = pd.DataFrame(jobs, columns=['ID', 'Company', 'Role', 'Platform', 'Status', 'Deadline', 'Applied Date', 'Job Link', 'Notes'])
    
    # KPIs
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Tracked", len(df))
    col2.metric("Applied", len(df[df['Status'] == 'Applied']))
    col3.metric("OAs / Interviews", len(df[df['Status'].isin(['Online Assessment (OA)', 'Interviewing'])]))
    col4.metric("Offers", len(df[df['Status'] == 'Offer']))

    st.subheader("📋 Application Dashboard")
    
    # Custom display logic with editable status
    for index, row in df.iterrows():
        with st.expander(f"{row['Company']} - {row['Role']}  |  Status: {row['Status']}"):
            c1, c2 = st.columns([3, 1])
            with c1:
                st.write(f"**Platform:** {row['Platform']}")
                st.write(f"**Deadline:** {row['Deadline']}  |  **Applied:** {row['Applied Date']}")
                st.write(f"**Link:** [Job Post]({row['Job Link']})")
                st.write(f"**Notes:** {row['Notes']}")
            with c2:
                new_status = st.selectbox("Update Status", ["Saved (Deadline Approaching)", "Applied", "Online Assessment (OA)", "Interviewing", "Offer", "Rejected", "Ghosted"], index=["Saved (Deadline Approaching)", "Applied", "Online Assessment (OA)", "Interviewing", "Offer", "Rejected", "Ghosted"].index(row['Status']), key=f"status_{row['ID']}")
                if new_status != row['Status']:
                    db.update_job_status(row['ID'], new_status)
                    st.rerun()
                
                if st.button("Delete", key=f"del_{row['ID']}"):
                    db.delete_job(row['ID'])
                    st.rerun()

