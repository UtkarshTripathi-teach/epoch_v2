import pandas as pd
from datetime import datetime, timedelta
import math

class GamificationSystem:
    def __init__(self):
        # XP calculation constants
        self.base_xp_per_minute = 2
        self.confidence_multiplier = {1: 0.5, 2: 0.7, 3: 1.0, 4: 1.3, 5: 1.5}
        self.streak_bonus_multiplier = 0.1  # 10% bonus per streak day
        
        
        # Level thresholds (XP required for each level)
        self.level_thresholds = [
            0, 100, 250, 450, 700, 1000, 1400, 1850, 2350, 2900, 3500,
            4200, 5000, 5900, 6900, 8000, 9200, 10500, 12000, 13600, 15300
        ]
        
        # Achievement definitions
        self.achievements = {
            "first_session": {"name": "Getting Started", "description": "Complete your first study session", "xp": 25},
            "week_streak": {"name": "Consistent Learner", "description": "Study for 7 consecutive days", "xp": 100},
            "month_streak": {"name": "Dedicated Scholar", "description": "Study for 30 consecutive days", "xp": 500},
            "100_hours": {"name": "Century Mark", "description": "Complete 100 hours of study", "xp": 200},
            "perfect_week": {"name": "Perfect Week", "description": "Average 4+ confidence for a week", "xp": 150},
            "quiz_master": {"name": "Quiz Master", "description": "Score 90%+ on 5 quizzes", "xp": 300},
            "subject_expert": {"name": "Subject Expert", "description": "Reach average confidence 4+ in any subject", "xp": 250}
        }
    
    def calculate_session_xp(self, duration_minutes, confidence_rating, streak_days=0):
        """Calculate XP earned from a study session"""
        # Base XP from time spent
        base_xp = duration_minutes * self.base_xp_per_minute
        
        # Confidence multiplier
        confidence_bonus = self.confidence_multiplier.get(confidence_rating, 1.0)
        
        # Streak bonus (capped at 50% bonus)
        streak_bonus = min(0.5, streak_days * self.streak_bonus_multiplier)
        
        # Calculate final XP
        total_xp = int(base_xp * confidence_bonus * (1 + streak_bonus))
        
        return max(5, total_xp)  # Minimum 5 XP per session
    
    def calculate_total_xp(self, user_data):
        """Calculate total XP from all user activities"""
        if user_data.empty:
            return 0
        
        total_xp = 0
        
        # XP from study sessions
        for _, session in user_data.iterrows():
            # Calculate streak for this session date
            streak = self._calculate_streak_for_date(user_data, session['date'])
            session_xp = self.calculate_session_xp(
                session['duration_minutes'],
                session['confidence_rating'],
                streak
            )
            total_xp += session_xp
        
        return total_xp
    
    def _calculate_streak_for_date(self, user_data, target_date):
        """Calculate streak days up to a specific date"""
        # Convert target_date to datetime if it's not already
        if isinstance(target_date, str):
            target_date = pd.to_datetime(target_date).date()
        elif isinstance(target_date, pd.Timestamp):
            target_date = target_date.date()
        
        # Get all unique study dates up to target date
        study_dates = user_data[user_data['date'] <= target_date]['date'].unique()
        study_dates = pd.to_datetime(study_dates).date if len(study_dates) > 0 else []
        study_dates = sorted(study_dates, reverse=True)
        
        if not study_dates or study_dates[0] != target_date:
            return 0
        
        # Calculate consecutive days
        streak = 1
        current_date = study_dates[0]
        
        for date in study_dates[1:]:
            expected_date = current_date - timedelta(days=1)
            if date == expected_date:
                streak += 1
                current_date = date
            else:
                break
        
        return streak
    
    def get_level(self, total_xp):
        """Get current level based on total XP"""
        for level, threshold in enumerate(self.level_thresholds):
            if total_xp < threshold:
                return max(1, level)
        return len(self.level_thresholds)  # Max level
    
    def get_level_progress(self, total_xp):
        """Get progress towards next level"""
        current_level = self.get_level(total_xp)
        
        if current_level >= len(self.level_thresholds):
            return {"current_level": current_level, "progress": 100, "xp_to_next": 0}
        
        current_threshold = self.level_thresholds[current_level - 1] if current_level > 1 else 0
        next_threshold = self.level_thresholds[current_level]
        
        progress_xp = total_xp - current_threshold
        required_xp = next_threshold - current_threshold
        progress_percentage = (progress_xp / required_xp) * 100
        
        return {
            "current_level": current_level,
            "progress": round(progress_percentage, 1),
            "xp_to_next": next_threshold - total_xp,
            "current_xp": progress_xp,
            "required_xp": required_xp
        }
    
    def check_achievements(self, user_data, quiz_data=None):
        """Check which achievements the user has earned"""
        earned_achievements = []
        
        if user_data.empty:
            return earned_achievements
        
        # First session achievement
        if len(user_data) >= 1:
            earned_achievements.append("first_session")
        
        # Streak achievements
        from utils import calculate_streak
        current_streak = calculate_streak(user_data)
        
        if current_streak >= 7:
            earned_achievements.append("week_streak")
        if current_streak >= 30:
            earned_achievements.append("month_streak")
        
        # Study time achievements
        total_minutes = user_data['duration_minutes'].sum()
        total_hours = total_minutes / 60
        
        if total_hours >= 100:
            earned_achievements.append("100_hours")
        
        # Perfect week achievement
        if len(user_data) >= 7:
            # Check last 7 days
            recent_data = user_data.tail(7)
            if recent_data['confidence_rating'].mean() >= 4.0:
                earned_achievements.append("perfect_week")
        
        # Subject expert achievement
        subject_confidence = user_data.groupby('subject')['confidence_rating'].mean()
        if any(conf >= 4.0 for conf in subject_confidence.values):
            earned_achievements.append("subject_expert")
        
        return earned_achievements
    
    def get_achievement_info(self, achievement_key):
        """Get information about a specific achievement"""
        return self.achievements.get(achievement_key, {})
    
    def calculate_bonus_xp(self, user_data):
        """Calculate bonus XP from achievements and special events"""
        achievements = self.check_achievements(user_data)
        bonus_xp = 0
        
        for achievement in achievements:
            if achievement in self.achievements:
                bonus_xp += self.achievements[achievement]["xp"]
        
        return bonus_xp
    
    def get_motivational_message(self, level, streak, recent_performance):
        """Generate motivational messages based on user performance"""
        messages = []
        
        # Level-based messages
        if level >= 10:
            messages.append("You're a study champion! Keep pushing boundaries!")
        elif level >= 5:
            messages.append("Great progress! You're becoming a study expert!")
        else:
            messages.append("Every expert was once a beginner. Keep growing!")
        
        # Streak-based messages
        if streak >= 30:
            messages.append("Incredible 30+ day streak! You're unstoppable!")
        elif streak >= 7:
            messages.append("Amazing weekly streak! Consistency is key!")
        elif streak >= 3:
            messages.append("Building momentum! Keep the streak alive!")
        
        # Performance-based messages
        if recent_performance >= 4.0:
            messages.append("Excellent confidence levels! You're mastering your subjects!")
        elif recent_performance >= 3.0:
            messages.append("Good progress! Keep building that confidence!")
        else:
            messages.append("Focus and persistence will lead to improvement!")
        
        return messages
    
    def get_next_milestone(self, total_xp, current_streak):
        """Get the next milestone the user should aim for"""
        milestones = []
        
        # Level milestone
        level_info = self.get_level_progress(total_xp)
        if level_info["xp_to_next"] > 0:
            milestones.append({
                "type": "level",
                "description": f"Reach Level {level_info['current_level'] + 1}",
                "progress": level_info["progress"],
                "target": f"{level_info['xp_to_next']} XP needed"
            })
        
        # Streak milestones
        if current_streak < 7:
            milestones.append({
                "type": "streak",
                "description": "7-day study streak",
                "progress": (current_streak / 7) * 100,
                "target": f"{7 - current_streak} more days"
            })
        elif current_streak < 30:
            milestones.append({
                "type": "streak",
                "description": "30-day study streak",
                "progress": (current_streak / 30) * 100,
                "target": f"{30 - current_streak} more days"
            })
        
        return milestones[:2]  # Return top 2 milestones
