from database.db_config import execute_query
from datetime import datetime, date

class GamificationEngine:
    def __init__(self):
        self.points_per_dose = 10
        self.streak_bonus = 5
        self.level_thresholds = [100, 300, 600, 1000, 1500, 2000, 3000, 5000]
        self.badges = {
            'first_dose': {'name': 'First Step', 'points': 50, 'description': 'Took your first medicine'},
            'week_streak': {'name': 'Week Warrior', 'points': 100, 'description': '7-day streak'},
            'month_streak': {'name': 'Monthly Master', 'points': 300, 'description': '30-day streak'},
            'perfect_week': {'name': 'Perfect Week', 'points': 150, 'description': '100% adherence for 7 days'},
            'early_bird': {'name': 'Early Bird', 'points': 75, 'description': 'Took medicine before 8 AM'},
            'night_owl': {'name': 'Night Owl', 'points': 75, 'description': 'Took medicine after 10 PM'},
            'level_5': {'name': 'Level 5 Master', 'points': 200, 'description': 'Reached Level 5'},
            'level_10': {'name': 'Level 10 Legend', 'points': 500, 'description': 'Reached Level 10'}
        }
    
    def calculate_points(self, user_id, medicine_id, dose_taken=True, on_time=True):
        """Calculate points for taking medicine"""
        points = 0
        
        if dose_taken:
            points += self.points_per_dose
            
            if on_time:
                points += self.streak_bonus
        
        return points
    
    def update_streak(self, user_id):
        """Update user's streak based on today's activity"""
        today = date.today()
        
        # Get user's current streak data
        user_query = "SELECT streak_days, last_streak_date, longest_streak FROM users WHERE id = %s"
        user_data = execute_query(user_query, (user_id,))
        
        if not user_data:
            return 0
        
        user = user_data[0]
        current_streak = user['streak_days'] or 0
        last_streak_date = user['last_streak_date']
        longest_streak = user['longest_streak'] or 0
        
        # Check if user took medicine today
        today_query = """
            SELECT COUNT(*) as doses_taken 
            FROM user_medicines 
            WHERE user_id = %s AND status = 'active' 
            AND DATE(last_taken) = %s
        """
        today_doses = execute_query(today_query, (user_id, today))
        doses_taken_today = today_doses[0]['doses_taken'] if today_doses else 0
        
        new_streak = current_streak
        
        if doses_taken_today > 0:
            # User took medicine today
            if last_streak_date == today:
                # Already counted today
                pass
            elif last_streak_date and (today - last_streak_date).days == 1:
                # Consecutive day
                new_streak = current_streak + 1
            else:
                # New streak starting
                new_streak = 1
        else:
            # No medicine taken today - streak broken
            new_streak = 0
        
        # Update longest streak
        if new_streak > longest_streak:
            longest_streak = new_streak
        
        # Update database
        update_query = """
            UPDATE users 
            SET streak_days = %s, last_streak_date = %s, longest_streak = %s
            WHERE id = %s
        """
        execute_query(update_query, (new_streak, today, longest_streak, user_id))
        
        return new_streak
    
    def add_points(self, user_id, points):
        """Add points to user's total"""
        query = "UPDATE users SET total_points = total_points + %s WHERE id = %s"
        execute_query(query, (points, user_id))
        
        # Check for level up
        self.check_level_up(user_id)
    
    def check_level_up(self, user_id):
        """Check if user should level up"""
        user_query = "SELECT total_points, level FROM users WHERE id = %s"
        user_data = execute_query(user_query, (user_id,))
        
        if not user_data:
            return
        
        user = user_data[0]
        total_points = user['total_points'] or 0
        current_level = user['level'] or 1
        
        # Calculate new level
        new_level = 1
        for i, threshold in enumerate(self.level_thresholds):
            if total_points >= threshold:
                new_level = i + 2
            else:
                break
        
        if new_level > current_level:
            # Level up!
            update_query = "UPDATE users SET level = %s WHERE id = %s"
            execute_query(update_query, (new_level, user_id))
            
            # Award level badge
            if new_level >= 5:
                self.award_badge(user_id, 'level_5')
            if new_level >= 10:
                self.award_badge(user_id, 'level_10')
            
            return new_level
        
        return current_level
    
    def award_badge(self, user_id, badge_key):
        """Award a badge to user"""
        if badge_key not in self.badges:
            return
        
        badge = self.badges[badge_key]
        
        # Check if user already has this badge
        user_query = "SELECT badges FROM users WHERE id = %s"
        user_data = execute_query(user_query, (user_id,))
        
        if not user_data:
            return
        
        current_badges = user_data[0]['badges'] or ''
        badges_list = current_badges.split(',') if current_badges else []
        
        if badge_key not in badges_list:
            badges_list.append(badge_key)
            new_badges = ','.join(badges_list)
            
            # Update badges and add points
            update_query = "UPDATE users SET badges = %s, total_points = total_points + %s WHERE id = %s"
            execute_query(update_query, (new_badges, badge['points'], user_id))
            
            return badge
        
        return None
    
    def get_user_stats(self, user_id):
        """Get user's gamification stats"""
        query = """
            SELECT streak_days, total_points, level, badges, longest_streak, last_streak_date
            FROM users WHERE id = %s
        """
        user_data = execute_query(query, (user_id,))
        
        if not user_data:
            return None
        
        user = user_data[0]
        badges_list = user['badges'].split(',') if user['badges'] else []
        
        # Get earned badges details
        earned_badges = []
        for badge_key in badges_list:
            if badge_key in self.badges:
                earned_badges.append({
                    'key': badge_key,
                    'name': self.badges[badge_key]['name'],
                    'description': self.badges[badge_key]['description']
                })
        
        return {
            'streak_days': user['streak_days'] or 0,
            'total_points': user['total_points'] or 0,
            'level': user['level'] or 1,
            'longest_streak': user['longest_streak'] or 0,
            'last_streak_date': user['last_streak_date'],
            'earned_badges': earned_badges,
            'next_level_points': self.level_thresholds[user['level'] - 1] if user['level'] <= len(self.level_thresholds) else None
        }

# Create global instance
gamification_engine = GamificationEngine()
