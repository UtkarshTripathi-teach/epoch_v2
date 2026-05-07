import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
import warnings
warnings.filterwarnings('ignore')

class MLAnalyzer:
    def __init__(self):
        self.weakness_threshold = 3.0  # Confidence rating below this is considered weak
        self.min_sessions_for_analysis = 3  # Minimum sessions per topic for reliable analysis
    
    def analyze_weaknesses(self, user_data):
        """
        Analyze user's study data to identify weak topics and provide recommendations
        """
        if user_data.empty or len(user_data) < 5:
            return [], ["Need more study sessions for accurate analysis."]
        
        try:
            # prepare data for analysis
            topic_analysis = self._prepare_topic_analysis(user_data)
            
            # identify weak topics
            weak_topics = self._identify_weak_topics(topic_analysis)
            
            # generate ML-powered insight
            insights = self._generate_ml_insights(user_data, topic_analysis)
            
            # generate recommendations
            recommendations = self._generate_recommendations(weak_topics, insights, user_data)
            
            return weak_topics, recommendations
            
        except Exception as e:
            return [], [f"Analysis error: {str(e)}. Please try again with more data."]

    def forecast_spending(self, expense_data, forecast_days=30):
        """
        Forecast future spending using Linear Regression on spending trends.
        """
        if len(expense_data) < 5:
            return None, "Need at least 5 expenses for an accurate forecast."

        # Aggregate spending by date
        expense_data['date'] = pd.to_datetime(expense_data['date'])
        daily_spending = expense_data.groupby('date')['amount'].sum().reset_index()
        daily_spending = daily_spending.sort_values('date')

        # Feature engineering: days since the first expense
        daily_spending['days'] = (daily_spending['date'] - daily_spending['date'].min()).dt.days

        if len(daily_spending) < 2:
            return None, "Need expenses on at least 2 different days for a forecast."

        # Prepare data for Linear Regression
        X = daily_spending[['days']]
        y = daily_spending['amount'].cumsum()  # Forecast cumulative spending

        model = LinearRegression()
        model.fit(X, y)

        # Create future dates for prediction
        last_day = X['days'].max()
        future_days = np.arange(last_day + 1, last_day + 1 + forecast_days).reshape(-1, 1)

        # Predict future cumulative spending
        future_predictions = model.predict(future_days)
        
        # Combine historical and predicted data for plotting
        forecast_df = pd.DataFrame({
            'days': np.concatenate([X['days'].values, future_days.flatten()]),
            'amount': np.concatenate([y.values, future_predictions]),
            'type': ['Historical'] * len(y) + ['Forecast'] * forecast_days
        })
        
        return forecast_df, f"Predicted total spending in the next {forecast_days} days could reach around ₹{future_predictions[-1]:.2f}."

    def _prepare_topic_analysis(self, user_data):
        """Prepare topic-level analysis"""
        topic_stats = user_data.groupby(['subject', 'chapter']).agg({
            'confidence_rating': ['mean', 'std', 'count'],
            'duration_minutes': ['sum', 'mean'],
            'date': ['min', 'max']
        }).round(2)
        
        # flatten column names
        topic_stats.columns = ['_'.join(col).strip() for col in topic_stats.columns.values]
        topic_stats = topic_stats.reset_index()
        
        # Calculate additional metrics
        topic_stats['days_studied'] = (
            pd.to_datetime(topic_stats['date_max']) - pd.to_datetime(topic_stats['date_min'])
        ).dt.days + 1
        
        topic_stats['consistency_score'] = (
            topic_stats['confidence_rating_count'] / topic_stats['days_studied']
        ).fillna(0)
        
        # Calculate improvement trend
        topic_stats['improvement_trend'] = topic_stats.apply(
            lambda row: self._calculate_improvement_trend(
                user_data, row['subject'], row['chapter']
            ), axis=1
        )
        
        return topic_stats
    
    def _calculate_improvement_trend(self, user_data, subject, chapter):
        """Calculate if confidence is improving for a topic"""
        topic_data = user_data[
            (user_data['subject'] == subject) & 
            (user_data['chapter'] == chapter)
        ].sort_values('date')
        
        if len(topic_data) < 2:
            return 0
        
        # Simple trend calculation using first and last half of sessions
        mid_point = len(topic_data) // 2
        first_half_avg = topic_data.iloc[:mid_point]['confidence_rating'].mean()
        second_half_avg = topic_data.iloc[mid_point:]['confidence_rating'].mean()
        
        return second_half_avg - first_half_avg
    
    def _identify_weak_topics(self, topic_analysis):
        """Identify topics that need attention"""
        weak_topics = []
        
        for _, topic in topic_analysis.iterrows():
            # Criteria for weak topic
            is_weak = (
                topic['confidence_rating_mean'] < self.weakness_threshold or
                (topic['improvement_trend'] < -0.5 and topic['confidence_rating_count'] >= 3) or
                (topic['consistency_score'] < 0.3 and topic['confidence_rating_count'] >= 2)
            )
            
            if is_weak and topic['confidence_rating_count'] >= self.min_sessions_for_analysis:
                weak_topics.append({
                    'subject': topic['subject'],
                    'chapter': topic['chapter'],
                    'avg_confidence': topic['confidence_rating_mean'],
                    'total_time': topic['duration_minutes_sum'],
                    'sessions': topic['confidence_rating_count'],
                    'improvement_trend': topic['improvement_trend'],
                    'weakness_score': self._calculate_weakness_score(topic)
                })
        
        # Sort by weakness score (higher = more attention needed)
        weak_topics.sort(key=lambda x: x['weakness_score'], reverse=True)
        
        return weak_topics
    
    def _calculate_weakness_score(self, topic):
        """Calculate a composite weakness score"""
        confidence_factor = (5 - topic['confidence_rating_mean']) / 4  # Normalize to 0-1
        trend_factor = max(0, -topic['improvement_trend'] / 2)  # Penalty for negative trends
        consistency_factor = 1 - min(1, topic['consistency_score'])  # Penalty for inconsistency
        
        return (confidence_factor * 0.5 + trend_factor * 0.3 + consistency_factor * 0.2)
    
    def _generate_ml_insights(self, user_data, topic_analysis):
        """Generate ML-powered insights using clustering and classification"""
        insights = {}
        
        try:
            # prepare features for ML analysis
            features = self._prepare_ml_features(topic_analysis)
            
            if len(features) < 3:
                return {"status": "insufficient_data"}
            
            # clustering analysis to group similar topics
            clusters = self._perform_clustering(features)
            insights['clusters'] = clusters
            
            # performance prediction
            performance_prediction = self._predict_performance_trends(user_data)
            insights['performance_prediction'] = performance_prediction
            
            # study pattern analysis
            study_patterns = self._analyze_study_patterns(user_data)
            insights['study_patterns'] = study_patterns
            
        except Exception as e:
            insights['error'] = str(e)
        
        return insights
    
    def _prepare_ml_features(self, topic_analysis):
        """Prepare features for ML analysis"""
        features = topic_analysis[[
            'confidence_rating_mean',
            'duration_minutes_sum',
            'confidence_rating_count',
            'improvement_trend',
            'consistency_score'
        ]].fillna(0)
        
        # normalize features
        scaler = StandardScaler()
        normalized_features = scaler.fit_transform(features)
        
        return normalized_features
    
    def _perform_clustering(self, features):
        """Cluster topics by similarity"""
        try:
            # determine optimal number of clusters (2-4)
            n_clusters = min(4, max(2, len(features) // 2))
            
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init='auto')
            cluster_labels = kmeans.fit_predict(features)
            
            return {
                'labels': cluster_labels.tolist(),
                'n_clusters': n_clusters,
                'cluster_centers': kmeans.cluster_centers_.tolist()
            }
        except:
            return {"status": "clustering_failed"}
    
    def _predict_performance_trends(self, user_data):
        """Predict performance trends using time series analysis"""
        try:
            # aggregate daily performance
            daily_performance = user_data.groupby('date').agg({
                'confidence_rating': 'mean',
                'duration_minutes': 'sum'
            }).reset_index()
            
            if len(daily_performance) < 7:
                return {"status": "insufficient_history"}
            
            # simple trend analysis
            daily_performance['date'] = pd.to_datetime(daily_performance['date'])
            daily_performance = daily_performance.sort_values('date')
            
            # calculate rolling averages
            daily_performance['confidence_trend'] = daily_performance['confidence_rating'].rolling(3).mean()
            daily_performance['time_trend'] = daily_performance['duration_minutes'].rolling(3).mean()
            
            # calculate overall trends
            recent_confidence = daily_performance['confidence_rating'].tail(7).mean()
            older_confidence = daily_performance['confidence_rating'].head(7).mean()
            confidence_trend = recent_confidence - older_confidence
            
            recent_time = daily_performance['duration_minutes'].tail(7).mean()
            older_time = daily_performance['duration_minutes'].head(7).mean()
            time_trend = recent_time - older_time
            
            return {
                'confidence_trend': confidence_trend,
                'time_trend': time_trend,
                'recent_performance': recent_confidence,
                'status': 'success'
            }
            
        except Exception as e:
            return {"status": "prediction_failed", "error": str(e)}
    
    def _analyze_study_patterns(self, user_data):
        """Analyze study patterns and habits"""
        try:
            patterns = {}
            
            # time of day analysis (if timestamp available)
            if 'timestamp' in user_data.columns:
                user_data['hour'] = pd.to_datetime(user_data['timestamp']).dt.hour
                patterns['peak_hours'] = user_data.groupby('hour')['duration_minutes'].sum().idxmax()
            
            # day of week patterns
            user_data['day_of_week'] = pd.to_datetime(user_data['date']).dt.day_name()
            patterns['most_productive_day'] = user_data.groupby('day_of_week')['confidence_rating'].mean().idxmax()
            
            # session length patterns
            patterns['avg_session_length'] = user_data['duration_minutes'].mean()
            patterns['preferred_session_length'] = user_data['duration_minutes'].mode().iloc[0] if not user_data['duration_minutes'].mode().empty else patterns['avg_session_length']
            
            # subject switching patterns
            patterns['subject_diversity'] = user_data['subject'].nunique()
            patterns['most_studied_subject'] = user_data.groupby('subject')['duration_minutes'].sum().idxmax()
            
            return patterns
            
        except Exception as e:
            return {"status": "pattern_analysis_failed", "error": str(e)}
    
    def _generate_recommendations(self, weak_topics, insights, user_data):
        """Generate personalized recommendations based on analysis"""
        recommendations = []
        
        # weakness-based recommendations
        if weak_topics:
            top_weak = weak_topics[:3]
            topic_list = ', '.join([f"{t['subject']} - {t['chapter']}" for t in top_weak])
            recommendations.append(f"Focus on these weak areas: {topic_list}")
            
            for topic in top_weak:
                if topic['improvement_trend'] < 0:
                    recommendations.append(f" {topic['subject']} - {topic['chapter']}: Try different study methods, confidence is declining")
                elif topic['sessions'] < 5:
                    recommendations.append(f" {topic['subject']} - {topic['chapter']}: Needs more practice sessions")
        
        # pattern-based recommendations
        if 'study_patterns' in insights and insights['study_patterns'].get('status') != 'pattern_analysis_failed':
            patterns = insights['study_patterns']
            
            if 'most_productive_day' in patterns:
                recommendations.append(f"You perform best on {patterns['most_productive_day']}s - consider scheduling important topics then")
            
            if 'avg_session_length' in patterns:
                avg_length = patterns['avg_session_length']
                if avg_length < 20:
                    recommendations.append("Consider longer study sessions (20-45 minutes) for better retention")
                elif avg_length > 90:
                    recommendations.append("Break down long sessions into smaller chunks with breaks")
        
        # performance trend recommendations
        if 'performance_prediction' in insights and insights['performance_prediction'].get('status') == 'success':
            pred = insights['performance_prediction']
            
            if pred['confidence_trend'] < -0.2:
                recommendations.append("Your confidence has been declining recently - consider reviewing fundamentals")
            elif pred['confidence_trend'] > 0.2:
                recommendations.append("Great progress! Your confidence is improving - keep up the momentum")
            
            if pred['time_trend'] < -10:
                recommendations.append("You've been studying less lately - try to maintain consistency")
        
        # General Recommendations
        if len(user_data) >= 10:
            user_data['date'] = pd.to_datetime(user_data['date'])
            recent_consistency = len(user_data[user_data['date'] >= (user_data['date'].max() - pd.Timedelta(days=7))])
            if recent_consistency < 3:
                recommendations.append("Try to study more consistently - aim for at least 3 sessions per week")
        
        # subject diversity recommendations
        subject_count = user_data['subject'].nunique()
        if subject_count == 1:
            recommendations.append("Consider diversifying your subjects to maintain engagement")
        elif subject_count > 5:
            recommendations.append("You're studying many subjects - ensure you're giving enough attention to each")
        
        if not recommendations:
            recommendations.append("Great job! No major issues detected. Keep maintaining your study routine!")
        
        return recommendations[:6]  # Limit to 6 recommendations

