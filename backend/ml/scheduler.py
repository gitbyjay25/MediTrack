# Simple reminder scheduler
from datetime import datetime, timedelta
from database.db_config import execute_query

def setup_reminders(user_id, med_id, reminder_times):
    """Setup reminders for a medicine"""
    
    for time_str in reminder_times:
        # Parse time string to get hour and minute
        time_parts = time_str.split(':')
        hour = int(time_parts[0])
        minute = int(time_parts[1])
        
        # Create job ID
        job_id = f"med_{med_id}_{hour}_{minute}"
        
        # Calculate next run time (today if time hasn't passed, tomorrow if it has)
        now = datetime.now()
        next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        if next_run <= now:
            next_run += timedelta(days=1)
        
        # Store schedule in database
        query = """
            INSERT INTO schedules (user_id, med_id, job_id, next_run_time)
            VALUES (%s, %s, %s, %s)
        """
        execute_query(query, (user_id, med_id, job_id, next_run))

def get_user_reminders(user_id):
    """Get upcoming reminders for user"""
    
    query = """
        SELECT s.*, m.med_name, m.med_id
        FROM schedules s
        JOIN medicines m ON s.med_id = m.id
        WHERE s.user_id = %s AND s.next_run_time <= NOW() + INTERVAL 1 HOUR
        ORDER BY s.next_run_time
    """
    
    reminders = execute_query(query, (user_id,))
    return reminders or []

def mark_job_completed(job_id):
    """Mark a scheduled job as completed"""
    
    # Update next run time to tomorrow
    query = """
        UPDATE schedules 
        SET next_run_time = next_run_time + INTERVAL 1 DAY
        WHERE job_id = %s
    """
    execute_query(query, (job_id,))
