import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
import random
import time
import io
from utils import format_time, calculate_streak, validate_study_session

# Import your custom modules
from data_manager import DataManager
from ml_analyzer import MLAnalyzer
from gamification import GamificationSystem
from pdf_exporter import PDFExporter

# --- Page Configuration ---
st.set_page_config(
    page_title="⏏︎ Epoch",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Initialize Session State & Classes ---
if 'data_manager' not in st.session_state: st.session_state.data_manager = DataManager()
if 'gamification' not in st.session_state: st.session_state.gamification = GamificationSystem()
if 'ml_analyzer' not in st.session_state: st.session_state.ml_analyzer = MLAnalyzer()
if 'pdf_exporter' not in st.session_state: st.session_state.pdf_exporter = PDFExporter()
if 'current_user' not in st.session_state: st.session_state.current_user = None

# Session state for the live timer
if 'timer_running' not in st.session_state: st.session_state.timer_running = False
if 'session_just_completed' not in st.session_state: st.session_state.session_just_completed = False
if 'timer_end_time' not in st.session_state: st.session_state.timer_end_time = None
if 'timer_duration' not in st.session_state: st.session_state.timer_duration = 0
if 'timer_subject' not in st.session_state: st.session_state.timer_subject = ""

# Session state for PDF download
if 'pdf_buffer' not in st.session_state: st.session_state.pdf_buffer = None
if 'pdf_ready' not in st.session_state: st.session_state.pdf_ready = False


# --- Main App Logic ---
def main():
    if st.session_state.current_user is None:
        show_user_selection()
    else:
        show_main_app()

def show_user_selection():
    st.title("⏏︎ Epoch - it's simple")
    st.header("Welcome to Your Personal Growth Platform!")
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    with tab1:
        st.subheader("Login to Your Account")
        users = st.session_state.data_manager.get_all_users()
        if not users:
            st.info("No users found. Please Sign Up.")
            return
        with st.form("login_form"):
            selected_user = st.selectbox("Choose your username:", users)
            password = st.text_input("Password:", type="password")
            if st.form_submit_button("Login"):
                success, message = st.session_state.data_manager.authenticate_user(selected_user, password)
                if success:
                    st.session_state.current_user = selected_user
                    st.rerun()
                else:
                    st.error(message)
    with tab2:
        st.subheader("Create New Account")
        with st.form("signup_form"):
            new_username = st.text_input("Username:")
            new_password = st.text_input("Password:", type="password")
            confirm_password = st.text_input("Confirm Password:", type="password")
            if st.form_submit_button("Create Account"):
                if new_password == confirm_password and new_username and new_password:
                    if len(new_password) >= 6:
                        success, message = st.session_state.data_manager.create_user(new_username.strip(), new_password)
                        if success:
                            st.session_state.current_user = new_username.strip()
                            st.success(message)
                            st.balloons()
                            st.rerun()
                        else:
                            st.error(message)
                    else:
                        st.error("Password must be at least 6 characters long.")
                else:
                    st.error("Please fill all fields and ensure passwords match.")

def show_main_app():
    with st.sidebar:
        st.markdown('<h1 style="font-size:48px;">⏏︎ Epoch</h1>', unsafe_allow_html=True)
        # st.markdown('<h2 style="font-size:38px;">it is simple</h2>', unsafe_allow_html=True)
        st.markdown(f'<h1 style="font-size:24px;">Welcome, {st.session_state.current_user}!', unsafe_allow_html=True)
        st.markdown(f'*Your next level in productivity*')

        user_data = st.session_state.data_manager.get_user_data(st.session_state.current_user)
        total_xp = st.session_state.gamification.calculate_total_xp(user_data)
        st.metric("🏆 Level", st.session_state.gamification.get_level(total_xp))
        st.metric("⭐ Total XP", total_xp)
        st.metric("🔥 Current Streak", f"{calculate_streak(user_data)} days")

        st.markdown("---")
        
        # REMOVED: "Placement Prediction" from navigation
        page_options = ["Dashboard", "Study Tracker", "Expense Tracker", "Task Tracker", "Your Report", "Settings"]
        page = st.radio("Navigation", page_options)

        st.markdown("---")
        if st.button("Logout"):
            st.session_state.current_user = None
            st.session_state.timer_running = False
            st.session_state.session_just_completed = False
            st.rerun()

    # REMOVED: "Placement Prediction" from routing
    page_functions = {
        "Dashboard": show_dashboard, 
        "Study Tracker": show_study_logging,
        "Expense Tracker": show_expense_tracker, 
        "Task Tracker": show_task_tracker,
        "Your Report": show_your_report,
        "Settings": show_settings,
    }
    page_functions[page]()


def show_dashboard():
    st.header("Master Dashboard")
    user = st.session_state.current_user
    study_data = st.session_state.data_manager.get_user_data(user)
    expense_data = st.session_state.data_manager.get_user_expenses(user)
    task_data = st.session_state.data_manager.get_user_tasks(user)

    st.subheader("Today's Snapshot")
    kpi1, kpi2, kpi3 = st.columns(3)
    today_study_time = study_data[study_data['date'] == datetime.now().date()]['duration_minutes'].sum()
    kpi1.metric("Time Studied Today", format_time(today_study_time))
    this_month = datetime.now().month
    monthly_expenses = expense_data[pd.to_datetime(expense_data['date']).dt.month == this_month]['amount'].sum()
    kpi2.metric("Expenses This Month", f"₹{monthly_expenses:,.2f}")
    pending_tasks = task_data[task_data['status'] == 'Pending'].shape[0]
    kpi3.metric("Pending Tasks", pending_tasks)
    
    st.markdown("---")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Weekly Study Consistency")
        if not study_data.empty:
            today = datetime.now().date()
            start_date = today - timedelta(days=84)
            date_range = pd.to_datetime(pd.date_range(start=start_date, end=today))
            study_counts = pd.to_datetime(study_data['date']).value_counts().reindex(date_range, fill_value=0)
            heatmap_data = pd.DataFrame({'date': study_counts.index, 'sessions': study_counts.values})
            heatmap_data['weekday'] = heatmap_data['date'].dt.day_name()
            heatmap_data['week'] = heatmap_data['date'].dt.isocalendar().week
            heatmap_pivot = heatmap_data.pivot_table(index='weekday', columns='week', values='sessions', aggfunc='sum').fillna(0)
            weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            heatmap_pivot = heatmap_pivot.reindex(weekday_order)
            fig = go.Figure(data=go.Heatmap(z=heatmap_pivot.values, x=heatmap_pivot.columns, y=heatmap_pivot.index, hoverongaps=False, colorscale='Greens'))
            fig.update_layout(title='Study Sessions per Day', height=350)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Log study sessions to see your consistency heatmap.")

    with col2:
        st.subheader("Monthly Budget Overview")
        if not expense_data.empty:
            monthly_budget = 20000 
            
            # 1. Prepare Data: Group by category
            # Filter for current month first
            this_month = datetime.now().month
            current_month_data = expense_data[pd.to_datetime(expense_data['date']).dt.month == this_month]
            
            if current_month_data.empty:
                 st.info("No expenses logged this month.")
            else:
                cat_group = current_month_data.groupby('category')['amount'].sum().sort_values(ascending=False)
                
                # 2. Define Colors for Categories
                # You can add more categories/colors here
                category_colors = {
                    'Food': '#ff9900',          # Orange
                    'Transport': '#3366cc',     # Blue
                    'Utilities': '#109618',     # Green
                    'Entertainment': '#dc3912', # Red
                    'Shopping': '#990099',      # Purple
                    'Health': '#0099c6',        # Teal
                    'Other': '#dd4477'          # Pink
                }

                # 3. Build the Gauge Steps (The stacked segments)
                gauge_steps = []
                current_value = 0
                
                for category, amount in cat_group.items():
                    # Get color (default to gray if category not in dict)
                    color = category_colors.get(category, '#666666')
                    
                    # Create a step for this category
                    step = {
                        'range': [current_value, current_value + amount],
                        'color': color
                    }
                    gauge_steps.append(step)
                    current_value += amount

                # 4. Create the Figure
                # We set the axis max to the Budget OR the Total Expenses (whichever is higher)
                max_range = max(monthly_budget, current_value)

                fig = go.Figure(go.Indicator(
                    mode = "gauge+number", 
                    value = current_value,
                    domain = {'x': [0, 1], 'y': [0, 1]}, 
                    title = {'text': "Spending Breakdown"},
                    
                    number = {'prefix': "₹", 'font': {'size': 24}},
                    
                    gauge = {
                        'axis': {
                            'range': [None, max_range], 
                            'tickwidth': 1, 
                            'tickcolor': "darkblue",
                            # Show ticks so user can see the amounts
                            'tickmode': 'linear',
                            'tick0': 0,
                            'dtick': 5000, 
                        },
                        
                        # Make the main bar transparent so we see the colored steps behind it
                        # OR make it a thin black line to show the "Total" mark
                        'bar': {'color': "rgba(0,0,0,0.3)", 'thickness': 0.1}, 
                        
                        # Apply our category steps
                        'steps': gauge_steps,
                        
                        # Make the threshold (Budget line) visible
                        'threshold': {
                            'line': {'color': "red", 'width': 4},
                            'thickness': 0.75,
                            'value': monthly_budget
                        }
                    }))
                
                fig.update_layout(height=350, margin=dict(t=50, b=20, l=20, r=20))
                st.plotly_chart(fig, use_container_width=True)

                # 5. Create a Custom Legend (Since Gauge steps don't have legends)
                st.markdown("**Category Legend:**")
                legend_cols = st.columns(len(cat_group))
                for i, (cat, amt) in enumerate(cat_group.items()):
                    color = category_colors.get(cat, '#666666')
                    # Use HTML to display a colored dot
                    st.markdown(f"<span style='color:{color};'>●</span> {cat} (₹{amt:,.0f})", unsafe_allow_html=True)

        else:
            st.info("Log expenses to see your budget overview.")

    with col3:
        st.subheader("Task Status")
        if not task_data.empty:
            status_counts = task_data['status'].value_counts().reset_index()
            status_counts.columns = ['status', 'count']
            fig = px.pie(status_counts, names='status', values='count', title='Task Breakdown', hole=.4,
                         color='status', color_discrete_map={'Completed':'#28a745', 'Pending':'#ffc107'})
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Add tasks to see your status breakdown.")


def show_study_logging():
    st.header("Study Tracker")
    tab1, tab2, tab3 = st.tabs(["Start Live Session", "Log a Past Session", "AI Weakness Analysis"])
    with tab1:
        show_live_session_tracker()
    with tab2:
        show_manual_log_form()
    with tab3:
        st.subheader("AI-Powered Weakness Analysis")
        user_data = st.session_state.data_manager.get_user_data(st.session_state.current_user)
        if len(user_data) < 5:
            st.warning("Need at least 5 study sessions for accurate analysis.")
            return
        
        weak_topics, recommendations = st.session_state.ml_analyzer.analyze_weaknesses(user_data)
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Areas Needing Attention")
            if weak_topics:
                df_weak = pd.DataFrame(weak_topics)
                st.dataframe(df_weak[['subject', 'chapter', 'avg_confidence', 'sessions']], use_container_width=True)
            else:
                st.success("No specific weak areas detected. Keep up the great work!")
        with col2:
            st.subheader("Personalized Recommendations")
            for rec in recommendations:
                st.info(rec)

def show_live_session_tracker():
    st.subheader("Live Study Session")
    
    if st.session_state.session_just_completed:
        st.success(f"Session for **{st.session_state.timer_subject}** complete!")
        st.info("Please rate your confidence to automatically log the session.")
        
        confidence = st.select_slider("Confidence Rating:", options=[1, 2, 3, 4, 5], value=3, format_func=lambda x: f"{x} {'⭐' * x}")
        
        if st.button("Log Session & Get XP"):
            _log_and_reward_session(
                user=st.session_state.current_user,
                subject=st.session_state.timer_subject,
                chapter="Live Session", 
                duration=st.session_state.timer_duration,
                confidence=confidence,
                date=datetime.now().date(),
                notes="Completed via live timer."
            )
            st.session_state.session_just_completed = False
            st.session_state.timer_subject = ""
            st.session_state.timer_duration = 0
            st.rerun()

    elif st.session_state.timer_running:
        time_left = st.session_state.timer_end_time - datetime.now()
        if time_left.total_seconds() > 0:
            st.info(f"Session for **{st.session_state.timer_subject}** is in progress!")
            progress = 1.0 - (time_left.total_seconds() / (st.session_state.timer_duration * 60))
            st.progress(progress, text=f"Time remaining: {str(time_left).split('.')[0]}")
            
            if st.button("Give Up", type="secondary"):
                st.session_state.timer_running = False
                st.session_state.timer_end_time = None
                st.warning("Live session cancelled.")
                time.sleep(2)
                st.rerun()
            
            time.sleep(1)
            st.rerun()
        else:
            st.session_state.timer_running = False
            st.session_state.session_just_completed = True
            st.rerun()

    else:
        user_data = st.session_state.data_manager.get_user_data(st.session_state.current_user)
        existing_subjects = sorted(user_data['subject'].unique()) if not user_data.empty else []
        
        subject_option = st.selectbox("Subject:", ["Add a new subject..."] + existing_subjects)
        if subject_option == "Add a new subject...":
            subject = st.text_input("New Subject Name:", placeholder="e.g., Cloud Computing")
        else:
            subject = subject_option

        duration_options = {"30 mins": 30, "45 mins": 45, "60 mins": 60, "Custom": 0}
        duration_choice = st.selectbox("Select Duration:", list(duration_options.keys()))
        duration = st.number_input("Custom (mins):", 1, 240, 25) if duration_choice == "Custom" else duration_options[duration_choice]

        if st.button("Start Session", disabled=(not subject.strip())):
            st.session_state.timer_running = True
            st.session_state.timer_duration = duration
            st.session_state.timer_subject = subject
            st.session_state.timer_end_time = datetime.now() + timedelta(minutes=duration)
            st.rerun()

def show_manual_log_form():
    st.subheader("Log a Past Study Session")
    user = st.session_state.current_user
    user_data = st.session_state.data_manager.get_user_data(user)
    existing_subjects = sorted(user_data['subject'].unique()) if not user_data.empty else []

    with st.form("manual_session_form"):
        col1, col2 = st.columns(2)
        with col1:
            subject_option = st.selectbox("Subject:", ["Add a new subject..."] + existing_subjects)
            subject = st.text_input("New Subject:", placeholder="e.g., Data Structures") if subject_option == "Add a new subject..." else subject_option
            chapter = st.text_input("Chapter/Topic:", placeholder="e.g., Linked Lists")
            duration = st.number_input("Duration (minutes):", 1, value=30)
        with col2:
            confidence = st.select_slider("Confidence:", [1, 2, 3, 4, 5], 3, format_func=lambda x: f"{x} {'⭐'*x}")
            study_date = st.date_input("Date:", value=datetime.now().date())
            notes = st.text_area("Notes (optional):")
        
        if st.form_submit_button("Log Session"):
            errors = validate_study_session(subject, chapter, duration, confidence)
            if errors:
                for error in errors: st.error(error)
            else:
                _log_and_reward_session(user, subject, chapter, duration, confidence, study_date, notes)

def _log_and_reward_session(user, subject, chapter, duration, confidence, date, notes):
    user_data = st.session_state.data_manager.get_user_data(user)
    current_streak = calculate_streak(user_data)
    xp_gained = st.session_state.gamification.calculate_session_xp(duration, confidence, current_streak)
    
    success = st.session_state.data_manager.log_study_session(user, subject, chapter, duration, confidence, date, notes)
    if success:
        st.success(f"Session logged! You gained {xp_gained} XP! ✨")
        updated_data = st.session_state.data_manager.get_user_data(user)
        total_xp = st.session_state.gamification.calculate_total_xp(updated_data)
        if st.session_state.gamification.get_level(total_xp) > st.session_state.gamification.get_level(total_xp - xp_gained):
            st.balloons()
            st.success(f"LEVEL UP! You've reached Level {st.session_state.gamification.get_level(total_xp)}! 🚀")
        if calculate_streak(updated_data) > current_streak and calculate_streak(updated_data) > 1:
            st.info(f"Amazing! You're now on a {calculate_streak(updated_data)}-day study streak! 🔥")
    else:
        st.error("Failed to log session.")

def show_expense_tracker():
    st.header("Expense Tracker")
    user = st.session_state.current_user
    tab1, tab2, tab3 = st.tabs(["Log Expense", "View & Analyze", "Budget Forecast"])
    with tab1:
        st.subheader("Log a New Expense")
        with st.form("expense_form", clear_on_submit=True):
            amount = st.number_input("Amount (₹)", min_value=1.00, step=1.00, format="%.2f")
            category = st.selectbox("Category", ["Food", "Transport", "Utilities", "Entertainment", "Shopping", "Health", "Other"])
            date = st.date_input("Date", datetime.now())
            description = st.text_input("Description (optional)")
            if st.form_submit_button("Add Expense"):
                st.session_state.data_manager.log_expense(user, amount, category, date, description)
                st.success("Expense logged!")
    with tab2:
        st.subheader("Your Expenses")
        expense_data = st.session_state.data_manager.get_user_expenses(user)
        if expense_data.empty:
            st.info("No expenses logged yet.")
        else:
            st.dataframe(expense_data.sort_values('date', ascending=False), use_container_width=True)
            c1, c2 = st.columns(2)
            expense_data['month'] = pd.to_datetime(expense_data['date']).dt.to_period('M').astype(str)
            monthly_summary = expense_data.groupby('month')['amount'].sum().reset_index()
            fig_monthly = px.bar(monthly_summary, x='month', y='amount', title="Spending Per Month", labels={'amount': 'Total Amount (₹)'})
            c1.plotly_chart(fig_monthly, use_container_width=True)
            category_summary = expense_data.groupby('category')['amount'].sum().reset_index()
            fig_category = px.pie(category_summary, names='category', values='amount', title="Spending by Category")
            c2.plotly_chart(fig_category, use_container_width=True)
    with tab3:
        st.subheader("ML-Based Budget Forecast")
        expense_data = st.session_state.data_manager.get_user_expenses(user)
        forecast_df, message = st.session_state.ml_analyzer.forecast_spending(expense_data)
        if forecast_df is not None:
            st.info(message)
            fig = px.line(forecast_df, x='days', y='amount', color='type', title="Cumulative Spending Forecast", labels={'amount': 'Cumulative Amount (₹)'})
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning(message)

def show_task_tracker():
    st.header("Task Tracker")
    user = st.session_state.current_user
    st.subheader("Add a New Task")
    with st.form("task_form", clear_on_submit=True):
        title = st.text_input("Task Title")
        deadline = st.date_input("Deadline", min_value=datetime.now().date())
        if st.form_submit_button("Add Task"):
            if title:
                st.session_state.data_manager.add_task(user, title, deadline)
                st.success("Task added!")
            else:
                st.error("Task title cannot be empty.")
    st.markdown("---")
    st.subheader("Your Tasks")
    tasks = st.session_state.data_manager.get_user_tasks(user)
    if tasks.empty:
        st.info("You have no tasks.")
        return
    completion_rate = (tasks[tasks['status'] == 'Completed'].shape[0] / len(tasks)) * 100 if len(tasks) > 0 else 0
    st.progress(completion_rate / 100, text=f"{completion_rate:.1f}% Complete")
    pending_tasks = tasks[tasks['status'] == 'Pending'].sort_values('deadline')
    if pending_tasks.empty: st.success("All tasks completed! 🎉")
    else:
        for _, row in pending_tasks.iterrows():
            col1, col2, col3 = st.columns([0.1, 0.7, 0.2])
            if col1.checkbox("", key=f"check_{row['id']}"):
                st.session_state.data_manager.update_task_status(user, row['id'], 'Completed')
                st.rerun()
            col2.markdown(f"**{row['title']}** | *Deadline: {row['deadline'].strftime('%Y-%m-%d')}*")
            if col3.button("🗑️", key=f"del_{row['id']}"):
                st.session_state.data_manager.delete_task(user, row['id'])
                st.rerun()
    with st.expander("Show Completed Tasks"):
        st.dataframe(tasks[tasks['status'] == 'Completed'], use_container_width=True)

def show_your_report():
    st.header("Your Consolidated Report")
    user = st.session_state.current_user
    
    period = st.selectbox("Select Time Period:", ["Last 7 days", "Last 30 days", "Last 90 days", "All time"])
    end_date = datetime.now().date()
    if period == "Last 7 days": start_date = end_date - timedelta(days=7)
    elif period == "Last 30 days": start_date = end_date - timedelta(days=30)
    elif period == "Last 90 days": start_date = end_date - timedelta(days=90)
    else: start_date = None

    def filter_data(df, date_col='date'):
        if df.empty or start_date is None: return df
        df[date_col] = pd.to_datetime(df[date_col]).dt.date
        return df[(df[date_col] >= start_date) & (df[date_col] <= end_date)]

    study_data = filter_data(st.session_state.data_manager.get_user_data(user).copy())
    expense_data = filter_data(st.session_state.data_manager.get_user_expenses(user).copy())
    task_data = filter_data(st.session_state.data_manager.get_user_tasks(user).copy(), date_col='deadline')

    tab1, tab2, tab3 = st.tabs(["Study Report", "Expense Report", "Task Report"])
    with tab1:
        st.subheader("Study Performance")
        if not study_data.empty:
            s_c1, s_c2 = st.columns(2)
            s_c1.metric("Total Study Time", format_time(study_data['duration_minutes'].sum()))
            s_c2.metric("Average Confidence", f"{study_data['confidence_rating'].mean():.1f}/5")
            
            st.markdown("---")
            st.subheader("Visualizations")
            v_c1, v_c2 = st.columns(2)
            
            fig_study_bar = px.bar(study_data.groupby('subject')['duration_minutes'].sum().reset_index(), 
                                 x='subject', y='duration_minutes', title="Study Time by Subject")
            v_c1.plotly_chart(fig_study_bar, use_container_width=True)

            daily_confidence = study_data.groupby('date')['confidence_rating'].mean().reset_index()
            fig_study_line = px.line(daily_confidence, x='date', y='confidence_rating', markers=True,
                                    title="Confidence Trend Over Time")
            v_c2.plotly_chart(fig_study_line, use_container_width=True)
        else:
            st.info("No study data for this period.")
            
    with tab2:
        st.subheader("Expense Summary")
        if not expense_data.empty:
            e_c1, e_c2 = st.columns(2)
            e_c1.metric("Total Spent", f"₹{expense_data['amount'].sum():,.2f}")
            e_c2.metric("Total Transactions", len(expense_data))

            st.markdown("---")
            st.subheader("Visualizations")
            v_c1, v_c2 = st.columns(2)

            fig_expense_pie = px.pie(expense_data.groupby('category')['amount'].sum().reset_index(), 
                                   names='category', values='amount', title="Spending by Category")
            v_c1.plotly_chart(fig_expense_pie, use_container_width=True)

            daily_expense = expense_data.groupby('date')['amount'].sum().reset_index()
            fig_expense_bar = px.bar(daily_expense, x='date', y='amount', title="Daily Spending")
            v_c2.plotly_chart(fig_expense_bar, use_container_width=True)
        else:
            st.info("No expense data for this period.")

    with tab3:
        st.subheader("Task Overview")
        if not task_data.empty:
            t_c1, t_c2 = st.columns(2)
            completed = task_data[task_data['status'] == 'Completed'].shape[0]
            total = len(task_data)
            t_c1.metric("Completion Rate", f"{completed/total:.1%}" if total > 0 else "N/A")
            t_c2.metric("Pending Tasks", total - completed)
            
            st.markdown("---")
            st.subheader("Visualizations")

            status_counts = task_data['status'].value_counts().reset_index()
            status_counts.columns = ['status', 'count']
            fig_task_pie = px.pie(status_counts, names='status', values='count', 
                                title="Task Status Breakdown", color='status',
                                color_discrete_map={'Completed':'green', 'Pending':'orange'})
            st.plotly_chart(fig_task_pie, use_container_width=True)
        else:
            st.info("No task data for this period.")

    st.markdown("---")
    st.subheader("Export Your Report")
    
    csv_buffer = io.StringIO()
    csv_buffer.write(f"--- STUDY DATA ({period}) ---\n")
    study_data.to_csv(csv_buffer, index=False)
    csv_buffer.write(f"\n\n--- EXPENSE DATA ({period}) ---\n")
    expense_data.to_csv(csv_buffer, index=False)
    csv_buffer.write(f"\n\n--- TASK DATA ({period}) ---\n")
    task_data.to_csv(csv_buffer, index=False)
    
    st.download_button(
        label="📥 Download as CSV",
        data=csv_buffer.getvalue(),
        file_name=f"Elevate_Report_{user}_{period.replace(' ', '_')}.csv",
        mime="text/csv"
    )

    if st.button("📥 Generate PDF Report"):
        with st.spinner("Generating PDF..."):
            pdf_data = st.session_state.pdf_exporter.generate_report(
                user, period, study_data, expense_data, task_data
            )
            st.session_state.pdf_buffer = pdf_data
            st.session_state.pdf_ready = True

    if st.session_state.get('pdf_ready', False):
        st.download_button(
            label="Click here to Download PDF",
            data=st.session_state.pdf_buffer,
            file_name=f"Elevate_Report_{user}_{period.replace(' ', '_')}.pdf",
            mime="application/pdf"
        )
        st.session_state.pdf_ready = False
        st.session_state.pdf_buffer = None

def show_settings():
    st.header("⚙️ Settings")
    user = st.session_state.current_user
    tab1, tab2 = st.tabs(["Profile", "Data Management"])

    with tab1:
        st.subheader("Your Profile")
        user_data = st.session_state.data_manager.get_user_data(user)
        st.info(f"**Username:** {user}")
        if not user_data.empty:
            st.info(f"**Member since:** {pd.to_datetime(user_data['date']).min().strftime('%B %d, %Y')}")
            st.info(f"**Total study sessions logged:** {len(user_data)}")
        else:
            st.info("No study sessions logged yet.")

    with tab2:
        st.subheader("Data Management")
        
        st.markdown("Export all your data from every module into a single CSV file.")
        all_study_data = st.session_state.data_manager.get_user_data(user)
        all_expense_data = st.session_state.data_manager.get_user_expenses(user)
        all_task_data = st.session_state.data_manager.get_user_tasks(user)
        
        csv_buffer = io.StringIO()
        csv_buffer.write("--- STUDY DATA ---\n")
        all_study_data.to_csv(csv_buffer, index=False)
        csv_buffer.write("\n\n--- EXPENSE DATA ---\n")
        all_expense_data.to_csv(csv_buffer, index=False)
        csv_buffer.write("\n\n--- TASK DATA ---\n")
        all_task_data.to_csv(csv_buffer, index=False)

        st.download_button(
            label="📥 Export All My Data",
            data=csv_buffer.getvalue(),
            file_name=f"Elevate_ALL_DATA_{user}.csv",
            mime="text/csv"
        )
        
        st.markdown("---")
        
        st.subheader("Danger Zone")
        st.warning("WARNING: Deleting your account is permanent and cannot be undone.")
        if st.checkbox("I understand the consequences and want to delete my account."):
            if st.button("DELETE MY ACCOUNT AND ALL DATA", type="primary"):
                success = st.session_state.data_manager.delete_user_data(user)
                if success:
                    st.success("Your account and all associated data have been permanently deleted.")
                    st.session_state.current_user = None
                    time.sleep(3)
                    st.rerun()
                else:
                    st.error("Failed to delete data. Please try again.")

if __name__ == "__main__":
    main()

