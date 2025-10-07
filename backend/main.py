from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import bcrypt
import random
from database.db_config import execute_query, get_db_connection
from ml.drug_interactions import check_drug_interaction
from ml.scheduler import setup_reminders
import pymysql
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'meditrek_secret_key_2024'

# Simple user login
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']
    
    query = "SELECT id, email, password_hash FROM users WHERE email = %s"
    user = execute_query(query, (email,))
    
    if user and user[0]:
        user_data = user[0]
        if bcrypt.check_password_hash(user_data['password_hash'], password):
            session['user_id'] = user_data['id']
            session['user_email'] = user_data['email']
            return redirect(url_for('dashboard'))
    
    flash('Invalid email or password')
    return redirect(url_for('index'))

# User registration
@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/register', methods=['POST'])
def register_user():
    name = request.form['name']
    email = request.form['email']
    password = request.form['password']
    
    # Check if email exists
    query = "SELECT id FROM users WHERE email = %s"
    existing_user = execute_query(query, (email,))
    
    if existing_user and existing_user[0]:
        flash('Email already exists')
        return redirect(url_for('register'))
    
    # Hash password
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    # Insert new user
    query = "INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s)"
    user_id = execute_query(query, (name, email, password_hash.decode('utf-8')))
    
    if user_id:
        flash('Registration successful! Please login.')
        return redirect(url_for('index'))
    else:
        flash('Registration failed')
        return redirect(url_for('register'))

# Dashboard
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    user_id = session['user_id']
    
    # Get user medicines
    query = """
        SELECT m.*, 
               COUNT(CASE WHEN dl.status = 'taken' THEN 1 END) as taken_count,
               COUNT(CASE WHEN dl.status IN ('taken', 'missed') THEN 1 END) as total_count
        FROM medicines m 
        LEFT JOIN dose_logs dl ON m.id = dl.med_id AND dl.dose_time >= CURDATE() - INTERVAL 7 DAY
        WHERE m.user_id = %s AND m.active = 'active'
        GROUP BY m.id
    """
    medicines = execute_query(query, (user_id,))
    
    # Calculate adherence
    medicines_with_adherence = []
    for med in medicines:
        adherence = 0
        if med['total_count'] > 0:
            adherence = round((med['taken_count'] / med['total_count']) * 100, 1)
        med['adherence'] = adherence
        medicines_with_adherence.append(med)
    
    return render_template('dashboard.html', medicines=medicines_with_adherence)

# Add medicine
@app.route('/add_medicine')
def add_medicine_form():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    return render_template('add_medicine.html')

@app.route('/add_medicine', methods=['POST'])
def add_medicine():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    user_id = session['user_id']
    med_name = request.form['med_name']
    dosage = request.form['dosage']
    frequency = request.form['frequency']
    purpose = request.form.get('purpose', '')
    start_date = datetime.now()
    
    # Check drug interactions
    existing_meds_query = "SELECT med_name FROM medicines WHERE user_id = %s AND active = 'active'"
    existing_meds = execute_query(existing_meds_query, (user_id,))
    
    interactions = []
    if existing_meds:
        existing_med_names = [med['med_name'] for med in existing_meds]
        for existing_med in existing_med_names:
            interaction_check = check_drug_interaction(med_name, existing_med)
            if interaction_check:
                interactions.append(interaction_check)
    
    # Generate reminder times based on frequency
    reminder_times = get_reminder_times(frequency)
    
    # Insert medicine
    query = """
        INSERT INTO medicines (user_id, med_name, dosage, frequency, purpose, start_date, reminder_times)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    med_id = execute_query(query, (user_id, med_name, dosage, frequency, purpose, start_date, str(reminder_times)))
    
    if med_id:
        # Setup reminders
        setup_reminders(user_id, med_id, reminder_times)
        flash('Medicine added successfully!')
        
        # Show interactions if any
        if interactions:
            flash(f'Drug interaction alert: {interactions[0]["description"]}')
        
        return redirect(url_for('dashboard'))
    else:
        flash('Failed to add medicine')
        return redirect(url_for('add_medicine_form'))

# Take dose
@app.route('/take_dose/<int:med_id>')
def take_dose(med_id):
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    user_id = session['user_id']
    current_time = datetime.now()
    
    # Insert dose log
    query = """
        INSERT INTO dose_logs (user_id, med_id, dose_time, status, actual_time)
        VALUES (%s, %s, %s, 'taken', %s)
    """
    result = execute_query(query, (user_id, med_id, current_time, current_time))
    
    if result:
        flash('Dose recorded successfully!')
    else:
        flash('Failed to record dose')
    
    return redirect(url_for('dashboard'))

# Miss dose
@app.route('/miss_dose/<int:med_id>')
def miss_dose(med_id):
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    user_id = session['user_id']
    current_time = datetime.now()
    
    # Insert dose log
    query = """
        INSERT INTO dose_logs (user_id, med_id, dose_time, status)
        VALUES (%s, %s, %s, 'missed')
    """
    result = execute_query(query, (user_id, med_id, current_time))
    
    if result:
        flash('Missed dose recorded')
    else:
        flash('Failed to record missed dose')
    
    return redirect(url_for('dashboard'))

# Medicine recommendations
@app.route('/recommendations')
def recommendations():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    query = "SELECT * FROM recommendations ORDER BY illness"
    recommendations = execute_query(query)
    
    return render_template('recommendations.html', recommendations=recommendations)

# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# Helper functions
def get_reminder_times(frequency):
    """Get reminder times based on frequency"""
    frequency_lower = frequency.lower()
    
    if 'once' in frequency_lower:
        return ['09:00']
    elif 'twice' in frequency_lower:
        return ['09:00', '21:00']
    elif 'three' in frequency_lower:
        return ['08:00', '14:00', '20:00']
    elif 'every 8 hours' in frequency_lower:
        return ['08:00', '16:00', '00:00']
    else:
        return ['09:00', '19:00']

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
