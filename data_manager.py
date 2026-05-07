import pandas as pd
import os
from datetime import datetime
import streamlit as st
import hashlib
import json
import uuid

class DataManager:
    def __init__(self):
        self.data_dir = "data"
        self.ensure_data_directory()
    
    def ensure_data_directory(self):
        """Ensure data directory exists"""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
    
    def get_user_file_path(self, username, file_type="study"):
        """Get file path for various user data types"""
        file_map = {
            "study": f"{username}_study_data.csv",
            "quiz": f"{username}_quiz_data.csv",
            "expenses": f"{username}_expenses.csv",
            "tasks": f"{username}_tasks.csv",
            "auth": "user_auth.json"
        }
        filename = file_map.get(file_type, f"{username}_{file_type}_data.csv")
        return os.path.join(self.data_dir, filename)
    
    def _hash_password(self, password):
        """Hash password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def _load_auth_data(self):
        """Load authentication data from file"""
        auth_file = self.get_user_file_path("", "auth")
        if os.path.exists(auth_file):
            try:
                with open(auth_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def _save_auth_data(self, auth_data):
        """Save authentication data to file"""
        auth_file = self.get_user_file_path("", "auth")
        with open(auth_file, 'w') as f:
            json.dump(auth_data, f, indent=4)

    def create_user(self, username, password):
        """Create a new user profile and all associated data files."""
        auth_data = self._load_auth_data()
        if username in auth_data:
            return False, "Username already exists!"

        auth_data[username] = {
            'password_hash': self._hash_password(password),
            'created_date': datetime.now().isoformat()
        }
        self._save_auth_data(auth_data)

        # Create empty data files for the new user
        pd.DataFrame(columns=['date', 'subject', 'chapter', 'duration_minutes', 'confidence_rating', 'notes', 'timestamp']).to_csv(self.get_user_file_path(username, "study"), index=False)
        pd.DataFrame(columns=['id', 'amount', 'category', 'date', 'description']).to_csv(self.get_user_file_path(username, "expenses"), index=False)
        pd.DataFrame(columns=['id', 'title', 'deadline', 'status']).to_csv(self.get_user_file_path(username, "tasks"), index=False)

        return True, "User created successfully!"

    def authenticate_user(self, username, password):
        """Authenticate user with username and password"""
        auth_data = self._load_auth_data()
        if username not in auth_data:
            return False, "Username not found!"
        
        if auth_data[username]['password_hash'] == self._hash_password(password):
            return True, "Authentication successful!"
        else:
            return False, "Incorrect password!"
    
    def get_all_users(self):
        """Get list of all existing users from auth file"""
        return sorted(list(self._load_auth_data().keys()))

    def _get_generic_data(self, username, file_type):
        """Generic function to load any user CSV data."""
        file_path = self.get_user_file_path(username, file_type)
        if not os.path.exists(file_path):
            # If file doesn't exist, create it with the correct headers
            if file_type == 'study': pd.DataFrame(columns=['date', 'subject', 'chapter', 'duration_minutes', 'confidence_rating', 'notes', 'timestamp']).to_csv(file_path, index=False)
            elif file_type == 'expenses': pd.DataFrame(columns=['id', 'amount', 'category', 'date', 'description']).to_csv(file_path, index=False)
            elif file_type == 'tasks': pd.DataFrame(columns=['id', 'title', 'deadline', 'status']).to_csv(file_path, index=False)
            return pd.DataFrame()
        try:
            df = pd.read_csv(file_path)
            if 'date' in df.columns: df['date'] = pd.to_datetime(df['date']).dt.date
            if 'deadline' in df.columns: df['deadline'] = pd.to_datetime(df['deadline']).dt.date
            return df
        except Exception as e:
            st.error(f"Error loading {file_type} data: {e}")
            return pd.DataFrame()

    def _save_generic_data(self, username, df, file_type):
        """Generic function to save any user CSV data."""
        file_path = self.get_user_file_path(username, file_type)
        try:
            df.to_csv(file_path, index=False)
            return True
        except Exception as e:
            st.error(f"Error saving {file_type} data: {e}")
            return False

    # --- Study Session Methods ---
    def get_user_data(self, username): 
        return self._get_generic_data(username, "study")

    def log_study_session(self, username, subject, chapter, duration, confidence, date, notes=""):
        df = self.get_user_data(username)
        new_session = pd.DataFrame([{'date': date, 'subject': subject, 'chapter': chapter, 'duration_minutes': duration, 'confidence_rating': confidence, 'notes': notes, 'timestamp': datetime.now().isoformat()}])
        df = pd.concat([df, new_session], ignore_index=True)
        return self._save_generic_data(username, df, "study")

    # --- Expense Methods (CRUD) ---
    def get_user_expenses(self, username):
        """Reads all expenses for a user."""
        return self._get_generic_data(username, "expenses")

    def log_expense(self, username, amount, category, date, description):
        """Creates a new expense."""
        df = self.get_user_expenses(username)
        new_expense = pd.DataFrame([{'id': str(uuid.uuid4()), 'amount': amount, 'category': category, 'date': date, 'description': description}])
        df = pd.concat([df, new_expense], ignore_index=True)
        return self._save_generic_data(username, df, "expenses")

    def update_expense(self, username, expense_id, new_data):
        """Updates an existing expense."""
        df = self.get_user_expenses(username)
        if 'id' in df.columns and expense_id in df['id'].values:
            for key, value in new_data.items():
                df.loc[df['id'] == expense_id, key] = value
            return self._save_generic_data(username, df, "expenses")
        return False

    def delete_expense(self, username, expense_id):
        """Deletes an expense by its ID."""
        df = self.get_user_expenses(username)
        if 'id' in df.columns:
            df = df[df['id'] != expense_id]
            return self._save_generic_data(username, df, "expenses")
        return False

    # --- Task Methods (CRUD) ---
    def get_user_tasks(self, username):
        """Reads all tasks for a user."""
        return self._get_generic_data(username, "tasks")

    def add_task(self, username, title, deadline):
        """Creates a new task."""
        df = self.get_user_tasks(username)
        new_task = pd.DataFrame([{'id': str(uuid.uuid4()), 'title': title, 'deadline': deadline, 'status': 'Pending'}])
        df = pd.concat([df, new_task], ignore_index=True)
        return self._save_generic_data(username, df, "tasks")

    def update_task_status(self, username, task_id, status):
        """Updates the status of an existing task."""
        df = self.get_user_tasks(username)
        if 'id' in df.columns:
            df.loc[df['id'] == task_id, 'status'] = status
        return self._save_generic_data(username, df, "tasks")

    def delete_task(self, username, task_id):
        """Deletes a task by its ID."""
        df = self.get_user_tasks(username)
        if 'id' in df.columns:
            df = df[df['id'] != task_id]
        return self._save_generic_data(username, df, "tasks")

    # --- User Data Management ---
    def delete_user_data(self, username):
        """Delete all data files and auth entry for a user."""
        try:
            for file_type in ["study", "expenses", "tasks", "quiz"]:
                file_path = self.get_user_file_path(username, file_type)
                if os.path.exists(file_path): 
                    os.remove(file_path)
            
            auth_data = self._load_auth_data()
            if username in auth_data:
                del auth_data[username]
                self._save_auth_data(auth_data)
            return True
        except Exception as e:
            st.error(f"Error deleting user data: {e}")
            return False
            
    def backup_user_data(self, username):
        """Create a backup of all user data files."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = os.path.join(self.data_dir, "backups", username, timestamp)
            
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
            
            for file_type in ["study", "expenses", "tasks"]:
                source_file = self.get_user_file_path(username, file_type)
                if os.path.exists(source_file):
                    backup_file = os.path.join(backup_dir, f"{username}_{file_type}_backup.csv")
                    pd.read_csv(source_file).to_csv(backup_file, index=False)
            
            return True
        except Exception as e:
            st.error(f"Error creating backup: {str(e)}")
            return False

