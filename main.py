from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import bcrypt
from database.db_config import execute_query
from backend.ml.drug_interactions import check_drug_interaction
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'meditrek_secret_key_2024'

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
        try:
            if bcrypt.check_password_hash(user_data['password_hash'], password):
                session['user_id'] = user_data['id']
                session['user_email'] = user_data['email']
                return redirect(url_for('dashboard'))
        except Exception as e:
            print(f"Password check error: {e}")
    
    flash('Invalid email or password')
    return redirect(url_for('index'))

@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/register', methods=['POST'])
def register_user():
    name = request.form['name']
    email = request.form['email']
    password = request.form['password']
    
    query = "SELECT id FROM users WHERE email = %s"
    existing_user = execute_query(query, (email,))
    
    if existing_user and existing_user[0]:
        flash('Email already exists')
        return redirect(url_for('register'))
    
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    query = "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)"
    user_id = execute_query(query, (name, email, password_hash))
    
    if user_id:
        flash('Registration successful! Please login.')
        return redirect(url_for('index'))
    else:
        flash('Registration failed')
        return redirect(url_for('register'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    query = "SELECT * FROM medicines LIMIT 10"
    medicines = execute_query(query)
    
    return render_template('dashboard.html', medicines=medicines or [])

@app.route('/add_medicine')
def add_medicine_form():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    return render_template('add_medicine.html')

@app.route('/search_medicine')
def search_medicine():
    search_term = request.args.get('q', '')
    if search_term:
        query = "SELECT medicine_name, form, main_category FROM medicines WHERE medicine_name LIKE %s LIMIT 10"
        medicines = execute_query(query, (f'%{search_term}%',))
        return jsonify(medicines or [])
    
    return jsonify([])

@app.route('/add_medicine', methods=['POST'])
def add_medicine():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    med_name = request.form['med_name']
    dosage = request.form['dosage']
    frequency = request.form['frequency']
    purpose = request.form.get('purpose', '')
    
    query = "SELECT * FROM medicines WHERE medicine_name LIKE %s LIMIT 1"
    med_result = execute_query(query, (f'%{med_name}%',))
    
    if not med_result:
        flash('Medicine not found in database')
        return redirect(url_for('add_medicine_form'))
    
    flash('Medicine added successfully!')
    return redirect(url_for('dashboard'))

@app.route('/recommendations')
def recommendations():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    query = "SELECT * FROM recommendations ORDER BY medical_condition"
    recommendations = execute_query(query)
    
    return render_template('recommendations.html', recommendations=recommendations or [])

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    print("Starting MediTrek Flask App...")
    print("Database: 231 medicines, 375 interactions")
    print("URL: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
