import pandas as pd
from datetime import datetime, timedelta
import numpy as np

def format_time(minutes):
    """Convert minutes to a human-readable format"""
    if minutes < 60:
        return f"{int(minutes)} min"
    
    hours = int(minutes // 60)
    remaining_minutes = int(minutes % 60)
    
    if hours == 1:
        if remaining_minutes == 0:
            return "1 hour"
        else:
            return f"1 hour {remaining_minutes} min"
    else:
        if remaining_minutes == 0:
            return f"{hours} hours"
        else:
            return f"{hours} hours {remaining_minutes} min"

def calculate_streak(user_data):
    """Calculate the current study streak in days"""
    if user_data.empty:
        return 0
    
    # Convert dates to datetime and sort
    dates = pd.to_datetime(user_data['date']).dt.date.unique()
    dates = sorted(dates, reverse=True)  # Most recent first
    
    if not dates:
        return 0
    
    # Check if user studied today or yesterday (to account for different time zones)
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    
    # Start counting from today if studied today, otherwise from yesterday if studied yesterday
    if dates[0] == today:
        current_date = today
    elif dates[0] == yesterday:
        current_date = yesterday
    else:
        return 0  # No recent study activity
    
    # Count consecutive days
    streak = 0
    for date in dates:
        if date == current_date:
            streak += 1
            current_date -= timedelta(days=1)
        else:
            break
    
    return streak

def get_date_range_data(user_data, days_back):
    """Get user data for the last N days"""
    if user_data.empty:
        return pd.DataFrame()
    
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days_back)
    
    # Convert date column to datetime if it's not already
    user_data_copy = user_data.copy()
    user_data_copy['date'] = pd.to_datetime(user_data_copy['date']).dt.date
    
    # Filter data
    filtered_data = user_data_copy[
        (user_data_copy['date'] >= start_date) & 
        (user_data_copy['date'] <= end_date)
    ]
    
    return filtered_data

def calculate_consistency_score(user_data, days_back=30):
    """Calculate consistency score for the last N days (0-100)"""
    if user_data.empty:
        return 0
    
    recent_data = get_date_range_data(user_data, days_back)
    if recent_data.empty:
        return 0
    
    # Count unique study days
    unique_study_days = recent_data['date'].nunique()
    
    # Calculate possible study days (excluding today if no study yet)
    possible_days = min(days_back, (datetime.now().date() - recent_data['date'].min()).days + 1)
    
    if possible_days == 0:
        return 0
    
    # Consistency score
    consistency = (unique_study_days / possible_days) * 100
    return min(100, consistency)

def get_study_habits_analysis(user_data):
    """Analyze study habits and return insights"""
    if user_data.empty:
        return {}
    
    analysis = {}
    
    # Study time patterns
    analysis['total_time'] = user_data['duration_minutes'].sum()
    analysis['avg_session_length'] = user_data['duration_minutes'].mean()
    analysis['total_sessions'] = len(user_data)
    
    # Confidence patterns
    analysis['avg_confidence'] = user_data['confidence_rating'].mean()
    analysis['confidence_improvement'] = calculate_confidence_trend(user_data)
    
    # Subject diversity
    analysis['subjects_studied'] = user_data['subject'].nunique()
    analysis['most_studied_subject'] = user_data.groupby('subject')['duration_minutes'].sum().idxmax()
    
    # Consistency
    analysis['current_streak'] = calculate_streak(user_data)
    analysis['consistency_30d'] = calculate_consistency_score(user_data, 30)
    
    # Recent activity (last 7 days)
    recent_data = get_date_range_data(user_data, 7)
    analysis['recent_study_time'] = recent_data['duration_minutes'].sum() if not recent_data.empty else 0
    analysis['recent_sessions'] = len(recent_data)
    
    return analysis

def calculate_confidence_trend(user_data, window_size=5):
    """Calculate trend in confidence ratings (positive = improving, negative = declining)"""
    if len(user_data) < window_size * 2:
        return 0
    
    # Sort by date
    sorted_data = user_data.sort_values('date')
    
    # Compare first and last portions
    first_portion = sorted_data.head(window_size)['confidence_rating'].mean()
    last_portion = sorted_data.tail(window_size)['confidence_rating'].mean()
    
    return last_portion - first_portion

def get_weak_topics(user_data, confidence_threshold=3.0, min_sessions=2):
    """Identify topics that need more attention"""
    if user_data.empty:
        return []
    
    # Group by subject and chapter
    topic_stats = user_data.groupby(['subject', 'chapter']).agg({
        'confidence_rating': ['mean', 'count'],
        'duration_minutes': 'sum'
    }).round(2)
    
    # Flatten column names
    topic_stats.columns = ['avg_confidence', 'session_count', 'total_time']
    topic_stats = topic_stats.reset_index()
    
    # Filter weak topics
    weak_topics = topic_stats[
        (topic_stats['avg_confidence'] < confidence_threshold) &
        (topic_stats['session_count'] >= min_sessions)
    ].sort_values('avg_confidence')
    
    return weak_topics.to_dict('records')

def get_study_recommendations(user_data):
    """Generate study recommendations based on user data"""
    recommendations = []
    
    if user_data.empty:
        return ["Start logging your study sessions to get personalized recommendations!"]
    
    habits = get_study_habits_analysis(user_data)
    
    # Session length recommendations
    if habits['avg_session_length'] < 15:
        recommendations.append("Try longer study sessions (20-45 minutes) for better focus and retention.")
    elif habits['avg_session_length'] > 90:
        recommendations.append("Consider breaking long sessions into smaller chunks with breaks.")
    
    # Consistency recommendations
    if habits['current_streak'] == 0:
        recommendations.append("Start building a study streak! Consistent daily practice is key to success.")
    elif habits['consistency_30d'] < 50:
        recommendations.append("Try to study more regularly. Aim for at least 4-5 sessions per week.")
    
    # Confidence recommendations
    if habits['avg_confidence'] < 3.0:
        recommendations.append("Focus on building confidence. Review fundamentals and practice more problems.")
    elif habits['confidence_improvement'] < -0.3:
        recommendations.append("Your confidence seems to be declining. Consider reviewing recent topics or seeking help.")
    
    # Subject diversity
    if habits['subjects_studied'] == 1:
        recommendations.append("Consider studying multiple subjects to maintain engagement and prevent burnout.")
    elif habits['subjects_studied'] > 5:
        recommendations.append("You're studying many subjects. Ensure you're giving adequate time to each.")
    
    # Recent activity
    if habits['recent_sessions'] == 0:
        recommendations.append("You haven't studied recently. Get back on track with a short session today!")
    elif habits['recent_study_time'] < 60:  # Less than 1 hour in last week
        recommendations.append("Increase your weekly study time for better progress.")
    
    # Weak topics
    weak_topics = get_weak_topics(user_data)
    if weak_topics:
        top_weak = weak_topics[:2]
        subjects = [f"{topic['subject']} - {topic['chapter']}" for topic in top_weak]
        recommendations.append(f"Give extra attention to: {', '.join(subjects)}")
    
    if not recommendations:
        recommendations.append("Excellent study habits! Keep up the great work!")
    
    return recommendations[:5]  # Limit to 5 recommendations

def format_confidence_rating(rating):
    """Format confidence rating with stars"""
    stars = "⭐" * int(rating)
    return f"{rating}/5 {stars}"

def get_performance_grade(avg_confidence):
    """Convert average confidence to letter grade"""
    if avg_confidence >= 4.5:
        return "A+"
    elif avg_confidence >= 4.0:
        return "A"
    elif avg_confidence >= 3.5:
        return "B+"
    elif avg_confidence >= 3.0:
        return "B"
    elif avg_confidence >= 2.5:
        return "C+"
    elif avg_confidence >= 2.0:
        return "C"
    elif avg_confidence >= 1.5:
        return "D"
    else:
        return "F"

def calculate_xp_for_period(user_data, days_back=30):
    """Calculate total XP earned in the last N days"""
    from gamification import GamificationSystem
    
    recent_data = get_date_range_data(user_data, days_back)
    if recent_data.empty:
        return 0
    
    gamification = GamificationSystem()
    total_xp = 0
    
    for _, session in recent_data.iterrows():
        streak = calculate_streak(user_data)  # This could be optimized
        session_xp = gamification.calculate_session_xp(
            session['duration_minutes'],
            session['confidence_rating'],
            streak
        )
        total_xp += session_xp
    
    return total_xp

def validate_study_session(subject, chapter, duration, confidence):
    """Validate study session input"""
    errors = []
    
    if not subject or not subject.strip():
        errors.append("Subject is required")
    
    if not chapter or not chapter.strip():
        errors.append("Chapter/Topic is required")
    
    if duration <= 0:
        errors.append("Duration must be greater than 0")
    elif duration > 1440:  # 24 hours
        errors.append("Duration cannot exceed 24 hours")
    
    if confidence not in [1, 2, 3, 4, 5]:
        errors.append("Confidence rating must be between 1 and 5")
    
    return errors

def get_monthly_summary(user_data, target_month=None, target_year=None):
    """Get summary statistics for a specific month"""
    if user_data.empty:
        return {}
    
    # Default to current month if not specified
    if target_month is None:
        target_month = datetime.now().month
    if target_year is None:
        target_year = datetime.now().year
    
    # Filter data for the target month
    user_data_copy = user_data.copy()
    user_data_copy['date'] = pd.to_datetime(user_data_copy['date'])
    
    monthly_data = user_data_copy[
        (user_data_copy['date'].dt.month == target_month) &
        (user_data_copy['date'].dt.year == target_year)
    ]
    
    if monthly_data.empty:
        return {}
    
    summary = {
        'total_time': monthly_data['duration_minutes'].sum(),
        'total_sessions': len(monthly_data),
        'avg_confidence': monthly_data['confidence_rating'].mean(),
        'subjects_studied': monthly_data['subject'].nunique(),
        'study_days': monthly_data['date'].dt.date.nunique(),
        'best_subject': monthly_data.groupby('subject')['confidence_rating'].mean().idxmax(),
        'most_studied_subject': monthly_data.groupby('subject')['duration_minutes'].sum().idxmax()
    }
    
    return summary

def export_data_to_csv(user_data, filename=None):
    """Export user data to CSV format"""
    if filename is None:
        filename = f"study_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    # Add calculated fields
    export_data = user_data.copy()
    export_data['formatted_time'] = export_data['duration_minutes'].apply(format_time)
    export_data['confidence_stars'] = export_data['confidence_rating'].apply(format_confidence_rating)
    
    return export_data.to_csv(index=False)

def get_subject_performance_comparison(user_data):
    """Compare performance across different subjects"""
    if user_data.empty:
        return {}
    
    subject_stats = user_data.groupby('subject').agg({
        'confidence_rating': ['mean', 'std', 'count'],
        'duration_minutes': ['sum', 'mean']
    }).round(2)
    
    # Flatten columns
    subject_stats.columns = ['avg_confidence', 'confidence_std', 'sessions', 'total_time', 'avg_session_time']
    subject_stats = subject_stats.reset_index()
    
    # Add performance grades
    subject_stats['grade'] = subject_stats['avg_confidence'].apply(get_performance_grade)
    
    # Sort by average confidence (descending)
    subject_stats = subject_stats.sort_values('avg_confidence', ascending=False)
    
    return subject_stats.to_dict('records')