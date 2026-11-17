import streamlit as st
import pandas as pd
from datetime import date, datetime

st.set_page_config(
    page_title="Task Tracker",
    page_icon="✅",
    layout="wide"
)

# -----------------------------------------------------------------------------
# 1. CHECK GOOGLE SHEETS CONNECTION
# -----------------------------------------------------------------------------
try:
    has_gsheets = "connections" in st.secrets and "gsheets" in st.secrets["connections"]
except Exception:
    has_gsheets = False

# -----------------------------------------------------------------------------
# 2. LOCAL DEMO DATA (Fallback if no secrets are added yet)
# -----------------------------------------------------------------------------
if "local_tasks" not in st.session_state:
    st.session_state.local_tasks = pd.DataFrame([
        {"Task_ID": 1, "Task_Name": "Set up Streamlit project", "Priority": "High", "Due_Date": "2026-11-18", "Status": "Completed"},
        {"Task_ID": 2, "Task_Name": "Connect Google Sheet database", "Priority": "High", "Due_Date": "2026-11-19", "Status": "Pending"},
        {"Task_ID": 3, "Task_Name": "Deploy to Streamlit Cloud", "Priority": "Medium", "Due_Date": "2026-11-20", "Status": "Pending"}
    ])

def get_tasks_data():
    """Reads tasks from Google Sheets if configured, otherwise returns local demo data."""
    if has_gsheets:
        try:
            from streamlit_gsheets import GSheetsConnection
            conn = st.connection("gsheets", type=GSheetsConnection)
            df = conn.read(ttl="2s")
            if df.empty or "Task_ID" not in df.columns:
                df = pd.DataFrame(columns=["Task_ID", "Task_Name", "Priority", "Due_Date", "Status"])
            return conn, df
        except Exception as e:
            st.error(f"Error reading Google Sheet: {e}")
            return None, st.session_state.local_tasks
    else:
        return None, st.session_state.local_tasks

def save_tasks_data(conn, updated_df):
    """Saves updated dataframe back to Google Sheets or local memory."""
    if has_gsheets and conn is not None:
        try:
            conn.update(data=updated_df)
            return True, "Saved to Google Sheet successfully!"
        except Exception as e:
            return False, f"Failed to save to Google Sheet: {e}"
    else:
        st.session_state.local_tasks = updated_df
        return True, "Saved to local memory (Add Google Sheet secrets to save permanently)."

# -----------------------------------------------------------------------------
# 3. SIDEBAR: CONCEPT & STATUS
# -----------------------------------------------------------------------------
with st.sidebar:
    st.title("ℹ️ Project Architecture")
    
    if has_gsheets:
        st.success("🟢 **Database Status:** Connected to Google Sheet!")
    else:
        st.warning("🟡 **Database Status:** Localhost Demo Mode")
        st.caption("Tasks are currently saved in temporary local memory. Once you add your Google Sheet credentials, they save to the cloud permanently.")
    
    st.write("---")
    st.markdown("""
    ### 🪜 How this works:
    1. **Local Test (Now):** Run on your machine (`localhost:8501`).
    2. **Connect Sheet:** Link your Google Sheet via `.streamlit/secrets.toml`.
    3. **Push to GitHub:** Upload `app.py` & `requirements.txt`.
    4. **Host on Cloud:** Deploy on [share.streamlit.io](https://share.streamlit.io).
    """)

# -----------------------------------------------------------------------------
# 4. MAIN APP HEADER & METRICS
# -----------------------------------------------------------------------------
st.title("✅ Simple Task Tracker")
st.caption("A beginner-friendly project demonstrating Streamlit UI + Google Sheets as a database.")

conn, tasks_df = get_tasks_data()
tasks_df = tasks_df.dropna(how="all")

# Metrics
total_tasks = len(tasks_df)
pending_tasks = len(tasks_df[tasks_df["Status"] == "Pending"]) if "Status" in tasks_df.columns else 0
completed_tasks = len(tasks_df[tasks_df["Status"] == "Completed"]) if "Status" in tasks_df.columns else 0

col1, col2, col3 = st.columns(3)
col1.metric("📋 Total Tasks", total_tasks)
col2.metric("⏳ Pending", pending_tasks)
col3.metric("🎉 Completed", completed_tasks)

st.write("---")

# -----------------------------------------------------------------------------
# 5. TWO-COLUMN LAYOUT: ADD TASK & MANAGE TASKS
# -----------------------------------------------------------------------------
col_add, col_list = st.columns([1, 2], gap="large")

with col_add:
    st.subheader("➕ Add New Task")
    with st.form("add_task_form", clear_on_submit=True):
        task_name = st.text_input("Task Name", placeholder="e.g. Design homepage mockup")
        priority = st.selectbox("Priority", ["Low", "Medium", "High"], index=1)
        due_date = st.date_input("Due Date", value=date.today())
        
        submitted = st.form_submit_button("Add Task", use_container_width=True)
        if submitted:
            if not task_name.strip():
                st.warning("Please enter a task name.")
            else:
                next_id = int(tasks_df["Task_ID"].max() + 1) if not tasks_df.empty and "Task_ID" in tasks_df.columns and pd.notna(tasks_df["Task_ID"].max()) else 1
                new_row = pd.DataFrame([{
                    "Task_ID": next_id,
                    "Task_Name": task_name.strip(),
                    "Priority": priority,
                    "Due_Date": str(due_date),
                    "Status": "Pending"
                }])
                updated_df = pd.concat([tasks_df, new_row], ignore_index=True)
                success, msg = save_tasks_data(conn, updated_df)
                if success:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

with col_list:
    st.subheader("📋 Your Tasks")
    
    if not tasks_df.empty:
        # Filter
        filter_status = st.radio("Show:", ["All", "Pending", "Completed"], horizontal=True)
        filtered_df = tasks_df.copy()
        if filter_status != "All" and "Status" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["Status"] == filter_status]
        
        # Display Table
        st.dataframe(filtered_df, use_container_width=True, hide_index=True)
        
        # Action: Mark Task as Completed
        pending_rows = tasks_df[tasks_df["Status"] == "Pending"]
        if not pending_rows.empty:
            with st.expander("⚡ Quick Action: Mark Task as Completed"):
                task_options = pending_rows.apply(lambda r: f"#{r['Task_ID']}: {r['Task_Name']}", axis=1).tolist()
                selected_task_str = st.selectbox("Select Task to Complete", task_options)
                
                if st.button("Mark as Completed", type="primary"):
                    selected_id = int(selected_task_str.split(":")[0].replace("#", ""))
                    tasks_df.loc[tasks_df["Task_ID"] == selected_id, "Status"] = "Completed"
                    success, msg = save_tasks_data(conn, tasks_df)
                    if success:
                        st.success(f"Task #{selected_id} completed!")
                        st.rerun()
                    else:
                        st.error(msg)
    else:
        st.info("No tasks yet. Use the form on the left to add your first task!")
