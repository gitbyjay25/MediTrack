from database.db_config import execute_query
from datetime import datetime, date, timedelta
import json

class AnalyticsEngine:
    def __init__(self):
        pass
    
    def calculate_user_analytics(self, user_id):
        """Calculate comprehensive analytics for a user"""
        analytics = {}
        
        # Get user's medicine data
        medicines_query = """
            SELECT um.*, m.form, m.main_category
            FROM user_medicines um
            LEFT JOIN medicines m ON um.medicine_name = m.medicine_name
            WHERE um.user_id = %s AND um.status = 'active'
        """
        medicines = execute_query(medicines_query, (user_id,))
        
        if not medicines:
            return self.get_empty_analytics()
        
        # Calculate basic stats
        total_medicines = len(medicines)
        total_doses_taken = sum(med.get('taken_count', 0) for med in medicines)
        total_doses_missed = sum(med.get('missed_count', 0) for med in medicines)
        
        # Calculate adherence rates
        adherence_scores = [med.get('adherence_score', 0) for med in medicines]
        avg_adherence = sum(adherence_scores) / len(adherence_scores) if adherence_scores else 0
        
        # Weekly analytics
        week_analytics = self.calculate_weekly_analytics(user_id)
        
        # Monthly analytics
        month_analytics = self.calculate_monthly_analytics(user_id)
        
        # Medicine category breakdown
        category_analytics = self.calculate_category_analytics(medicines)
        
        # Time-based analytics
        time_analytics = self.calculate_time_analytics(user_id)
        
        analytics = {
            'overview': {
                'total_medicines': total_medicines,
                'total_doses_taken': total_doses_taken,
                'total_doses_missed': total_doses_missed,
                'avg_adherence_rate': round(avg_adherence, 2),
                'compliance_score': self.calculate_compliance_score(total_doses_taken, total_doses_missed)
            },
            'weekly': week_analytics,
            'monthly': month_analytics,
            'categories': category_analytics,
            'timing': time_analytics,
            'trends': self.calculate_trends(user_id),
            'insights': self.generate_insights(analytics)
        }
        
        # Update user analytics in database
        self.update_user_analytics(user_id, analytics)
        
        return analytics
    
    def calculate_weekly_analytics(self, user_id):
        """Calculate weekly adherence and patterns"""
        week_ago = date.today() - timedelta(days=7)
        
        # Get weekly medicine data
        weekly_query = """
            SELECT 
                DATE(last_taken) as date,
                COUNT(*) as doses_taken,
                SUM(CASE WHEN daily_doses_taken >= total_doses_required THEN 1 ELSE 0 END) as complete_days
            FROM user_medicines 
            WHERE user_id = %s AND status = 'active' 
            AND DATE(last_taken) >= %s
            GROUP BY DATE(last_taken)
            ORDER BY date
        """
        weekly_data = execute_query(weekly_query, (user_id, week_ago))
        
        # Calculate weekly adherence
        total_days = 7
        days_with_medicines = len(weekly_data)
        weekly_adherence = (days_with_medicines / total_days) * 100 if total_days > 0 else 0
        
        return {
            'adherence_rate': round(weekly_adherence, 2),
            'days_with_medicines': days_with_medicines,
            'total_days': total_days,
            'daily_data': weekly_data
        }
    
    def calculate_monthly_analytics(self, user_id):
        """Calculate monthly adherence and patterns"""
        month_ago = date.today() - timedelta(days=30)
        
        # Get monthly medicine data
        monthly_query = """
            SELECT 
                WEEK(last_taken) as week_number,
                COUNT(*) as doses_taken,
                AVG(adherence_score) as avg_adherence
            FROM user_medicines 
            WHERE user_id = %s AND status = 'active' 
            AND DATE(last_taken) >= %s
            GROUP BY WEEK(last_taken)
            ORDER BY week_number
        """
        monthly_data = execute_query(monthly_query, (user_id, month_ago))
        
        # Calculate monthly adherence
        total_weeks = 4
        weeks_with_data = len(monthly_data)
        monthly_adherence = (weeks_with_data / total_weeks) * 100 if total_weeks > 0 else 0
        
        return {
            'adherence_rate': round(monthly_adherence, 2),
            'weeks_with_data': weeks_with_data,
            'total_weeks': total_weeks,
            'weekly_data': monthly_data
        }
    
    def calculate_category_analytics(self, medicines):
        """Calculate analytics by medicine category"""
        categories = {}
        
        for med in medicines:
            category = med.get('main_category', 'Unknown')
            if category not in categories:
                categories[category] = {
                    'count': 0,
                    'total_adherence': 0,
                    'medicines': []
                }
            
            categories[category]['count'] += 1
            categories[category]['total_adherence'] += med.get('adherence_score', 0)
            categories[category]['medicines'].append(med['medicine_name'])
        
        # Calculate average adherence per category
        for category in categories:
            count = categories[category]['count']
            total_adherence = categories[category]['total_adherence']
            categories[category]['avg_adherence'] = round(total_adherence / count, 2) if count > 0 else 0
        
        return categories
    
    def calculate_time_analytics(self, user_id):
        """Calculate medicine timing patterns"""
        # Get medicine timing data
        timing_query = """
            SELECT 
                HOUR(last_taken) as hour,
                COUNT(*) as doses_taken
            FROM user_medicines 
            WHERE user_id = %s AND status = 'active' 
            AND DATE(last_taken) >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
            GROUP BY HOUR(last_taken)
            ORDER BY hour
        """
        timing_data = execute_query(timing_query, (user_id,))
        
        # Analyze timing patterns
        morning_doses = sum(1 for item in timing_data if 6 <= item['hour'] < 12)
        afternoon_doses = sum(1 for item in timing_data if 12 <= item['hour'] < 18)
        evening_doses = sum(1 for item in timing_data if 18 <= item['hour'] < 24)
        night_doses = sum(1 for item in timing_data if 0 <= item['hour'] < 6)
        
        return {
            'morning': morning_doses,
            'afternoon': afternoon_doses,
            'evening': evening_doses,
            'night': night_doses,
            'hourly_data': timing_data,
            'best_time': self.find_best_time(timing_data)
        }
    
    def calculate_trends(self, user_id):
        """Calculate adherence trends over time"""
        # Get trend data for last 30 days
        trend_query = """
            SELECT 
                DATE(last_taken) as date,
                AVG(adherence_score) as daily_adherence
            FROM user_medicines 
            WHERE user_id = %s AND status = 'active' 
            AND DATE(last_taken) >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            GROUP BY DATE(last_taken)
            ORDER BY date
        """
        trend_data = execute_query(trend_query, (user_id,))
        
        # Calculate trend direction
        if len(trend_data) >= 2:
            recent_avg = sum(item['daily_adherence'] for item in trend_data[-7:]) / 7
            older_avg = sum(item['daily_adherence'] for item in trend_data[:7]) / 7
            trend_direction = 'improving' if recent_avg > older_avg else 'declining'
        else:
            trend_direction = 'stable'
        
        return {
            'direction': trend_direction,
            'daily_data': trend_data,
            'trend_percentage': self.calculate_trend_percentage(trend_data)
        }
    
    def generate_insights(self, analytics):
        """Generate personalized insights based on analytics"""
        insights = []
        
        overview = analytics.get('overview', {})
        weekly = analytics.get('weekly', {})
        monthly = analytics.get('monthly', {})
        
        # Adherence insights
        if overview.get('avg_adherence_rate', 0) >= 90:
            insights.append("🎉 Excellent! You're maintaining great adherence!")
        elif overview.get('avg_adherence_rate', 0) >= 70:
            insights.append("👍 Good job! You're doing well with your medicines.")
        else:
            insights.append("💪 Keep going! Try to take medicines more consistently.")
        
        # Weekly insights
        if weekly.get('adherence_rate', 0) >= 85:
            insights.append("🔥 Great week! You've been very consistent.")
        elif weekly.get('adherence_rate', 0) < 50:
            insights.append("📅 This week was challenging. Tomorrow is a fresh start!")
        
        # Category insights
        categories = analytics.get('categories', {})
        if len(categories) > 3:
            insights.append("💊 You're managing multiple medicine categories well!")
        
        # Timing insights
        timing = analytics.get('timing', {})
        if timing.get('morning', 0) > timing.get('evening', 0):
            insights.append("🌅 You're better at taking morning medicines!")
        elif timing.get('evening', 0) > timing.get('morning', 0):
            insights.append("🌙 You're better at taking evening medicines!")
        
        return insights
    
    def calculate_compliance_score(self, taken, missed):
        """Calculate overall compliance score"""
        total = taken + missed
        if total == 0:
            return 0
        return round((taken / total) * 100, 2)
    
    def find_best_time(self, timing_data):
        """Find the best time for taking medicines"""
        if not timing_data:
            return "No data available"
        
        best_hour = max(timing_data, key=lambda x: x['doses_taken'])
        hour = best_hour['hour']
        
        if 6 <= hour < 12:
            return f"Morning ({hour}:00)"
        elif 12 <= hour < 18:
            return f"Afternoon ({hour}:00)"
        elif 18 <= hour < 24:
            return f"Evening ({hour}:00)"
        else:
            return f"Night ({hour}:00)"
    
    def calculate_trend_percentage(self, trend_data):
        """Calculate trend percentage change"""
        if len(trend_data) < 2:
            return 0
        
        recent = trend_data[-1]['daily_adherence']
        older = trend_data[0]['daily_adherence']
        
        if older == 0:
            return 0
        
        return round(((recent - older) / older) * 100, 2)
    
    def update_user_analytics(self, user_id, analytics):
        """Update user analytics in database"""
        overview = analytics.get('overview', {})
        
        update_query = """
            UPDATE users 
            SET total_medicines_taken = %s,
                total_doses_missed = %s,
                avg_adherence_rate = %s,
                last_analytics_update = NOW()
            WHERE id = %s
        """
        
        execute_query(update_query, (
            overview.get('total_doses_taken', 0),
            overview.get('total_doses_missed', 0),
            overview.get('avg_adherence_rate', 0),
            user_id
        ))
    
    def get_empty_analytics(self):
        """Return empty analytics structure"""
        return {
            'overview': {
                'total_medicines': 0,
                'total_doses_taken': 0,
                'total_doses_missed': 0,
                'avg_adherence_rate': 0,
                'compliance_score': 0
            },
            'weekly': {'adherence_rate': 0, 'days_with_medicines': 0, 'total_days': 7},
            'monthly': {'adherence_rate': 0, 'weeks_with_data': 0, 'total_weeks': 4},
            'categories': {},
            'timing': {'morning': 0, 'afternoon': 0, 'evening': 0, 'night': 0},
            'trends': {'direction': 'stable', 'daily_data': [], 'trend_percentage': 0},
            'insights': ['Start taking medicines to see your analytics!']
        }

# Create global instance
analytics_engine = AnalyticsEngine()
