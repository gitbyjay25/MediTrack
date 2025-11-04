from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory
import os
import bcrypt
from database.db_config import execute_query
from backend.ml.drug_interactions import check_drug_interaction

def generate_timing_advice(drug1, drug2, severity, description):
    """Generate dynamic timing advice based on interaction risk analysis"""
    
    # Risk analysis based on description keywords
    def analyze_interaction_risk(description):
        description_lower = description.lower()
        
        # High risk keywords
        high_risk_keywords = [
            'bleeding', 'hemorrhage', 'death', 'fatal', 'life-threatening', 
            'cardiac arrest', 'heart failure', 'severe', 'critical', 'emergency',
            'overdose', 'toxicity', 'kidney failure', 'liver damage', 'stroke'
        ]
        
        # Medium risk keywords  
        medium_risk_keywords = [
            'increase', 'decrease', 'reduce', 'enhance', 'potentiate', 'inhibit',
            'metabolism', 'absorption', 'excretion', 'side effects', 'adverse',
            'monitor', 'caution', 'warning', 'risk', 'interaction'
        ]
        
        # Count risk indicators
        high_risk_count = sum(1 for keyword in high_risk_keywords if keyword in description_lower)
        medium_risk_count = sum(1 for keyword in medium_risk_keywords if keyword in description_lower)
        
        return high_risk_count, medium_risk_count
    
    # Analyze the interaction risk
    high_risk_count, medium_risk_count = analyze_interaction_risk(description)
    
    # Determine timing based on severity + risk analysis
    severity_lower = severity.lower()
    
    # High severity or high risk keywords = longer spacing
    if severity_lower == 'high' or high_risk_count >= 2:
        if high_risk_count >= 3:  # Very dangerous
            return f" CRITICAL: Take {drug1} at least 2-3 hours before or after {drug2} (Very dangerous interaction!)"
        else:  # High severity
            return f"CRITICAL: Take {drug1} at least 1-2 hours before or after {drug2} (Dangerous interaction!)"
    
    # Medium severity or medium risk keywords = moderate spacing
    elif severity_lower == 'medium' or medium_risk_count >= 2:
        if medium_risk_count >= 3:  # High medium risk
            return f" Take {drug1} at least 60-90 minutes before or after {drug2} (Moderate-high risk)"
        else:  # Normal medium risk
            return f" Take {drug1} at least 40-60 minutes before or after {drug2} (Moderate risk)"
    
    # Low severity = minimal spacing
    else:
        if medium_risk_count >= 1:  # Some risk detected
            return f"Take {drug1} at least 30-45 minutes before or after {drug2} (Low-moderate risk)"
        else:  # Very low risk
            return f"Take {drug1} at least 15-20 minutes before or after {drug2} (Low risk)"
from datetime import datetime
import io
import re
from typing import Dict, Optional

try:
    from PIL import Image
    import pytesseract
    OCR_AVAILABLE = True
except Exception:
    OCR_AVAILABLE = False

# Import OCR service for prescription extraction
try:
    from ocr_service import extract_prescription_data, is_ocr_available
    OCR_SERVICE_AVAILABLE = True
except ImportError:
    OCR_SERVICE_AVAILABLE = False
    def is_ocr_available():
        return False
    def extract_prescription_data(image):
        return {'success': False, 'error': 'OCR service not available'}

# Optional: PaddleOCR (excellent for handwritten text, pretrained models)
PADDLEOCR_AVAILABLE = False
_paddleocr_reader = None
try:
    from paddleocr import PaddleOCR  # type: ignore
    PADDLEOCR_AVAILABLE = True
except Exception as e:
    print(f"PaddleOCR not available: {e}")
    PADDLEOCR_AVAILABLE = False

# Optional: TrOCR (Transformer-based OCR, best for handwritten text)
TROCR_AVAILABLE = False
_trocr_processor = None
_trocr_model = None
try:
    from transformers import TrOCRProcessor, VisionEncoderDecoderModel  # type: ignore
    TROCR_AVAILABLE = True
except Exception as e:
    print(f"TrOCR not available: {e}")
    TROCR_AVAILABLE = False

# ML Services 
try:
    from ml_recommendation_service import RecommendationEngine
    recommendation_engine = RecommendationEngine()
    ML_RECOMMENDATION_ENABLED = True
except ImportError:
    print("ML Recommendation Service not found. Falling back to database lookup.")
    ML_RECOMMENDATION_ENABLED = False
    recommendation_engine = None

# Gamification Engine
try:
    from gamification_engine import gamification_engine
    GAMIFICATION_ENABLED = True
except ImportError:
    print("Gamification Engine not found.")
    GAMIFICATION_ENABLED = False
    gamification_engine = None

# Analytics Engine
try:
    from analytics_engine import analytics_engine
    ANALYTICS_ENABLED = True
except ImportError:
    print("Analytics Engine not found.")
    ANALYTICS_ENABLED = False
    analytics_engine = None

try:
    from ml_interaction_service import InteractionEngine
    interaction_engine = InteractionEngine()
    ML_INTERACTION_ENABLED = True
except ImportError:
    print("ML Interaction Service not found. Falling back to database lookup.")
    ML_INTERACTION_ENABLED = False
    interaction_engine = None

try:
    from ml_dosage_service import DosageOptimizationEngine
    dosage_optimization_engine = DosageOptimizationEngine()
    ML_DOSAGE_ENABLED = True
except ImportError:
    print("ML Dosage Optimization Service not found. Falling back to database lookup.")
    ML_DOSAGE_ENABLED = False
    dosage_optimization_engine = None

app = Flask(__name__)
@app.route('/assets/<path:filename>')
def serve_asset(filename):
    base_dir = os.path.join(os.path.dirname(__file__), 'database', 'data')
    return send_from_directory(base_dir, filename)
app.secret_key = 'meditrek_secret_key_2024'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    
    # POST method (existing login logic)
    email = request.form['email']
    password = request.form['password']
    
    query = "SELECT id, email, password_hash FROM users WHERE email = %s"
    user = execute_query(query, (email,))
    
    if user and user[0]:
        user_data = user[0]
        try:
            if bcrypt.checkpw(password.encode('utf-8'), user_data['password_hash'].encode('utf-8')):
                session['user_id'] = user_data['id']
                session['user_email'] = user_data['email']
                return redirect(url_for('dashboard'))
        except Exception as e:
            print(f"Password check error: {e}")
    
    flash('Invalid email or password')
    return redirect(url_for('login'))

@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/register_user', methods=['POST'])
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
    
    user_id = session['user_id']
    
    # Get user's personal medicines with dose tracking
    query = """
        SELECT um.*, m.form, m.main_category,
               CASE 
                   WHEN um.daily_doses_taken >= um.total_doses_required THEN 'Complete'
                   WHEN um.daily_doses_taken > 0 THEN CONCAT(um.daily_doses_taken, '/', um.total_doses_required)
                   ELSE 'Not Taken'
               END as dose_status
        FROM user_medicines um
        LEFT JOIN medicines m ON um.medicine_name = m.medicine_name
        WHERE um.user_id = %s AND um.status = 'active'
        ORDER BY um.created_at DESC
    """
    medicines = execute_query(query, (user_id,))
    
    # Check for drug interactions
    interactions = []
    if medicines:
        medicine_names = [med['medicine_name'] for med in medicines]
        for i, med1 in enumerate(medicine_names):
            for med2 in medicine_names[i+1:]:
                interaction = check_drug_interaction(med1, med2)
                if interaction:
                    # Generate timing advice based on severity and interaction type
                    timing_advice = generate_timing_advice(med1, med2, interaction['severity'], interaction['description'])
                    interactions.append({
                        'drug1': med1,
                        'drug2': med2,
                        'severity': interaction['severity'],
                        'description': interaction['description'],
                        'recommendation': interaction.get('recommendation', ''),
                        'timing_advice': timing_advice
                    })
    
    # Get user stats
    stats_query = """
        SELECT 
            COUNT(*) as total_medicines,
            COALESCE(AVG(adherence_score), 0) as avg_adherence,
            COUNT(CASE WHEN last_taken >= CURDATE() THEN 1 END) as taken_today
        FROM user_medicines 
        WHERE user_id = %s AND status = 'active'
    """
    stats = execute_query(stats_query, (user_id,))
    
    # Get ML model status
    ml_status = {
        'recommendation': ML_RECOMMENDATION_ENABLED,
        'interaction': ML_INTERACTION_ENABLED,
        'dosage': ML_DOSAGE_ENABLED
    }
    
    return render_template('dashboard.html', 
                         medicines=medicines or [], 
                         stats=stats[0] if stats else {'total_medicines': 0, 'avg_adherence': 100, 'taken_today': 0},
                         interactions=interactions,
                         ml_status=ml_status)

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
    
    user_id = session['user_id']
    med_name = request.form.get('med_name')
    dosage = request.form.get('dosage')
    frequency = request.form.get('frequency')
    age_group = request.form.get('age_group')
    weight = request.form.get('weight')
    height = request.form.get('height')
    gender = request.form.get('gender')
    purpose = request.form.get('purpose', '')
    medical_conditions = request.form.get('medical_conditions', '')
    allergies = request.form.get('allergies', '')
    
    # Get reminder times
    reminder_times = []
    for key, value in request.form.items():
        if key.startswith('reminder_time_') and value:
            reminder_times.append(value)
    
    # Convert reminder times to JSON string
    reminder_times_json = ','.join(reminder_times) if reminder_times else ''
    
    # Basic validation for required fields
    if not med_name or not dosage or not frequency or not age_group:
        flash('Please fill in all required fields: Medicine Name, Dosage, Frequency, and Age Group.', 'error')
        return redirect(url_for('add_medicine_form'))
    
    # Check if medicine exists in reference database
    query = "SELECT * FROM medicines WHERE medicine_name LIKE %s LIMIT 1"
    med_result = execute_query(query, (f'%{med_name}%',))
    
    if not med_result:
        flash('Medicine not found in database')
        return redirect(url_for('add_medicine_form'))
    
    # Check if user already has this medicine
    check_query = "SELECT id FROM user_medicines WHERE user_id = %s AND medicine_name = %s AND status = 'active'"
    existing = execute_query(check_query, (user_id, med_name))
    
    if existing:
        flash('Medicine already added to your list')
        return redirect(url_for('add_medicine_form'))
    
    # Check for drug interactions with existing medicines
    existing_meds_query = "SELECT medicine_name FROM user_medicines WHERE user_id = %s AND status = 'active'"
    existing_meds = execute_query(existing_meds_query, (user_id,))
    
    interactions = []
    if existing_meds:
        try:
            from ml_interaction_service import interaction_engine
            # Use ML-powered interaction checking
            for existing_med in existing_meds:
                interaction = interaction_engine.predict_interaction_severity(med_name, existing_med['medicine_name'])
                if interaction:
                    interactions.append(interaction)
        except ImportError:
            # Fallback to database lookup
            existing_med_names = [med['medicine_name'] for med in existing_meds]
            for existing_med in existing_med_names:
                interaction_check = check_drug_interaction(med_name, existing_med)
                if interaction_check:
                    interactions.append(interaction_check)
    
    # Add to user's medicine list
    insert_query = """
        INSERT INTO user_medicines (user_id, medicine_name, dosage, frequency, age_group, weight, height, gender, purpose, medical_conditions, allergies, adherence_score, reminder_times, reminder_enabled)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 100, %s, TRUE)
    """
    med_id = execute_query(insert_query, (user_id, med_name, dosage, frequency, age_group, weight, height, gender, purpose, medical_conditions, allergies, reminder_times_json))
    
    if med_id:
        flash('Medicine added successfully!')
        
        # Show interactions if any
        if interactions:
            for interaction in interactions:
                flash(f'⚠️ Drug Interaction Alert: {interaction["description"]}', 'warning')
        
        return redirect(url_for('dashboard'))
    else:
        flash('Failed to add medicine')
        return redirect(url_for('add_medicine_form'))

# Moved to ocr_service.py - keeping for backward compatibility if needed
def _parse_prescription_text(text: str) -> Dict[str, Optional[str]]:
    """Extract medicine name, dosage and frequency heuristically from OCR text."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    
    # Enhanced dosage patterns - handle more formats
    dosage_pattern = re.compile(
        r"\b((\d+(?:\.\d+)?)\s*(mg|mcg|g|ml|iu|units|tablet|tab|capsule|cap|drop|drops|tsp|teaspoon))|"
        r"((\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)\s*(mg|ml))|"
        r"((\d+(?:\.\d+)?)\s*%\s*(w/w|w/v|cream|ointment))\b",
        re.IGNORECASE
    )
    
    # Enhanced frequency map with more variations
    freq_map = {
        'once daily': ['od', 'once daily', 'qd', 'daily', 'q.d.', 'q24h', 'q 24h', 'once a day', '1x daily'],
        'twice daily': ['bd', 'twice daily', 'bid', 'b.i.d', 'b.i.d.', 'q12h', 'q 12h', '2x daily', 'twice a day'],
        'three times daily': ['tid', 't.d.s', 'tds', 't.i.d', 't.i.d.', 'three times', '3x daily', 'thrice daily'],
        'four times daily': ['qid', 'q.i.d', 'q.i.d.', 'q6h', 'q 6h', '4x daily', 'four times'],
        'every 8 hours': ['q8h', 'q 8h', 'every 8 hours', 'every 8 hrs', 'every eight hours'],
        'every 12 hours': ['q12h', 'q 12h', 'every 12 hours', 'every 12 hrs', 'every twelve hours'],
        'at bedtime': ['hs', 'qhs', 'at bedtime', 'bedtime', 'night', 'nightly'],
        'as needed': ['sos', 'prn', 'p.r.n', 'as needed', 'when required', 'as directed'],
        'every 6 hours': ['q6h', 'q 6h', 'every 6 hours', 'every 6 hrs'],
    }

    time_pattern = re.compile(r"\b(\d{1,2}):(\d{2})\s*(am|pm|AM|PM)\b\.?", re.IGNORECASE)
    header_blockers = re.compile(
        r"(dr\.?|doctor|physician|patient|dob|age|sex|gender|date|address|phone|license|allergies|weight|height|diagnosis|prescription|rx\s*no|reg\s*no)\b",
        re.IGNORECASE
    )
    dosage_split_tokens = re.compile(r"\b(mg|mcg|g|ml|iu|units|tablet|tab|capsule|cap|drop|drops|cream|ointment)\b", re.IGNORECASE)
    
    # Multiple medicine line patterns for different prescription formats
    med_line_patterns = [
        re.compile(r"^\s*\d+\.?\s*([A-Za-z][A-Za-z0-9\-\s]{2,})\s+(\d+(?:\.\d+)?)\s*(mg|mcg|g|ml|iu)\b", re.IGNORECASE),  # "1. Medicine 500mg"
        re.compile(r"^([A-Za-z][A-Za-z0-9\-\s]{2,})\s+(\d+(?:\.\d+)?)\s*(mg|mcg|g|ml|iu)\s*(tablet|tab|capsule|cap)?", re.IGNORECASE),  # "Medicine 500mg tablet"
        re.compile(r"^\s*rx\s*[:\.]?\s*([A-Za-z][A-Za-z0-9\-\s]{2,})\s+(\d+(?:\.\d+)?)\s*(mg|mcg|g|ml)", re.IGNORECASE),  # "Rx: Medicine 500mg"
        re.compile(r"^([A-Z][a-z]+\s+[A-Z][a-z]+)\s+(\d+(?:\.\d+)?)\s*(mg|mcg|g|ml)", re.IGNORECASE),  # "Medicine Name 500mg"
        re.compile(r"^\s*([A-Za-z][A-Za-z0-9\-\s]{3,})\s*[,:]?\s*(\d+(?:\.\d+)?)\s*(mg|mcg|g|ml)\b", re.IGNORECASE),  # "Medicine: 500mg"
    ]
    
    age_pattern = re.compile(r"\b(age|dob|yrs|years?)\b[\s:]*([0-9]{1,3})", re.IGNORECASE)
    weight_pattern = re.compile(r"\b(weight|wt)\b[\s:]*([0-9]{1,3}(?:\.[0-9]+)?)\s*(kg|kgs|kilograms?)?\b", re.IGNORECASE)
    height_pattern = re.compile(r"\b(height|ht)\b[\s:]*([0-9]{2,3}(?:\.[0-9]+)?)\s*(cm|cms|centimeters?)?\b", re.IGNORECASE)
    purpose_pattern = re.compile(r"\b(purpose|indication|reason|for|diagnosis)\b\s*[:\-]\s*(.+)$", re.IGNORECASE)
    allergies_pattern = re.compile(r"\ballerg(?:y|ies)\b\s*[:\-]\s*(.+)$", re.IGNORECASE)

    extracted: Dict[str, Optional[str]] = { 'med_name': None, 'dosage': None, 'frequency': None, 'time': None }
    extra: Dict[str, Optional[str]] = { 'purpose': None, 'age': None, 'age_group': None, 'weight': None, 'height': None, 'allergies': None }

    for ln in lines:
        # Try multiple medicine line patterns
        if extracted['med_name'] is None or extracted['dosage'] is None:
            for pattern in med_line_patterns:
                ml = pattern.search(ln)
                if ml:
                    name = ml.group(1).strip(' -,:')
                    # Handle different group structures
                    if len(ml.groups()) >= 3:
                        dose_value = ml.group(2) if ml.group(2) else ml.group(4)
                        dose_unit = ml.group(3) if ml.group(3) else ml.group(5)
                        if dose_value and dose_unit:
                            dose = (dose_value + ' ' + dose_unit).strip()
                            if extracted['med_name'] is None and len(name) >= 3:
                                extracted['med_name'] = name
                            if extracted['dosage'] is None:
                                extracted['dosage'] = dose
                            break  # Found a match, stop trying other patterns

        # dosage - enhanced pattern matching
        if extracted['dosage'] is None:
            d = dosage_pattern.search(ln)
            if d:
                # Extract the full match, prioritizing grouped patterns
                for group in d.groups():
                    if group and group.strip():
                        extracted['dosage'] = group.strip()
                        break

        # frequency
        if extracted['frequency'] is None:
            low = ln.lower()
            for freq, keys in freq_map.items():
                if any(k in low for k in keys):
                    extracted['frequency'] = freq
                    break

        # explicit time (e.g., 9:00 AM)
        if extracted['time'] is None:
            t = time_pattern.search(ln)
            if t:
                extracted['time'] = t.group(1) + ' ' + t.group(2).upper()

        # demographics and purpose/allergies
        if extra['age'] is None:
            am = age_pattern.search(ln)
            if am:
                try:
                    age_val = int(am.group(2))
                    extra['age'] = str(age_val)
                    if age_val < 18:
                        extra['age_group'] = 'pediatric'
                    elif age_val >= 65:
                        extra['age_group'] = 'elderly'
                    else:
                        extra['age_group'] = 'adult'
                except Exception:
                    pass
        if extra['weight'] is None:
            wm = weight_pattern.search(ln)
            if wm:
                extra['weight'] = wm.group(2)
        if extra['height'] is None:
            hm = height_pattern.search(ln)
            if hm:
                extra['height'] = hm.group(2)
        if extra['purpose'] is None:
            pm = purpose_pattern.search(ln)
            if pm:
                extra['purpose'] = pm.group(2).strip()
        if extra['allergies'] is None:
            alm = allergies_pattern.search(ln)
            if alm:
                extra['allergies'] = alm.group(1).strip()

        # medicine name heuristic: first line that looks like a wordy token and not Doctor/Patient headers
        if extracted['med_name'] is None:
            if re.search(r"[A-Za-z]{3,}", ln) and not header_blockers.search(ln):
                # remove leading bullets or numbering
                cand = re.sub(r"^[\-\d\.\)\s]+", "", ln)
                # remove leading rx markers like 'Rx', 'Rx1.', 'Rxi'
                cand = re.sub(r"^r\s*x\s*i?\s*[:\.]?\s*\d*\)?\s*", "", cand, flags=re.IGNORECASE)
                # strip common instructions
                cand = re.sub(r"\b(tab|tablet|caps|capsule|cap|syrup|drop|drops|inj|injection|ointment|cream)\b\.?,?\s*", "", cand, flags=re.IGNORECASE)
                # If dosage unit exists in same line, split name before it
                split_match = dosage_split_tokens.search(cand)
                name_part = cand
                if split_match:
                    name_part = cand[:split_match.start()].strip(' -,:')
                # keep first 3 words max as name
                words = name_part.split()
                if words:
                    extracted['med_name'] = " ".join(words[:3])

        if all(extracted.values()):
            break

    # merge extra fields into response
    for k, v in extra.items():
        extracted[k] = v
    return extracted

def _preprocess_for_handwriting(image: Image.Image) -> Image.Image:
    """Enhanced preprocessing specifically for handwritten text recognition"""
    from PIL import ImageOps, ImageFilter, ImageEnhance
    import numpy as np
    
    # Convert to grayscale if not already
    if image.mode != 'L':
        image = image.convert('L')
    
    # Convert to numpy for advanced processing
    img_array = np.array(image)
    
    # 1. Denoise (median filter for handwritten text)
    try:
        from scipy import ndimage
        img_array = ndimage.median_filter(img_array, size=3)
    except ImportError:
        # Fallback: PIL median filter
        image = image.filter(ImageFilter.MedianFilter(size=3))
        img_array = np.array(image)
    
    # 2. Enhance contrast aggressively for handwriting
    image = Image.fromarray(img_array)
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(2.0)  # Increase contrast
    
    # 3. Auto-contrast
    image = ImageOps.autocontrast(image, cutoff=5)
    
    # 4. Sharpen
    image = image.filter(ImageFilter.SHARPEN)
    
    # 5. Binarization (OTSU-like thresholding for handwritten text)
    try:
        from scipy.ndimage import gaussian_filter
        blurred = gaussian_filter(img_array, sigma=1.0)
        threshold = np.mean(blurred)
        binary = np.where(img_array > threshold * 0.9, 255, 0).astype(np.uint8)
        image = Image.fromarray(binary, mode='L')
    except ImportError:
        # Fallback: simple threshold
        image = ImageOps.autocontrast(image)
    
    return image

# OCR functions moved to ocr_service.py

def _paddleocr_text_from_image(image: Image.Image) -> str:
    """PaddleOCR - Excellent for handwritten text with pretrained models"""
    global _paddleocr_reader
    if not PADDLEOCR_AVAILABLE:
        raise RuntimeError('PaddleOCR not available')
    if _paddleocr_reader is None:
        # Initialize with English model, optimized for handwritten text
        _paddleocr_reader = PaddleOCR(use_angle_cls=True, lang='en', use_gpu=False)
    
    import tempfile, os as _os
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        image.save(tmp.name, format='PNG')
        tmp_path = tmp.name
    try:
        results = _paddleocr_reader.ocr(tmp_path, cls=True)
        # Extract text from results
        text_lines = []
        if results and results[0]:
            for line in results[0]:
                if line and len(line) >= 2:
                    text_lines.append(line[1][0])  # text is at [1][0]
        return "\n".join(text_lines)
    finally:
        try:
            _os.remove(tmp_path)
        except Exception:
            pass

def _trocr_text_from_image(image: Image.Image) -> str:
    """TrOCR - Transformer-based OCR, best for handwritten text (pretrained model)"""
    global _trocr_processor, _trocr_model
    if not TROCR_AVAILABLE:
        raise RuntimeError('TrOCR not available')
    
    # Lazy load model (first time only)
    if _trocr_processor is None or _trocr_model is None:
        # Use pretrained handwritten model
        _trocr_processor = TrOCRProcessor.from_pretrained('microsoft/trocr-base-handwritten')
        _trocr_model = VisionEncoderDecoderModel.from_pretrained('microsoft/trocr-base-handwritten')
    
    # Preprocess image
    pixel_values = _trocr_processor(image, return_tensors="pt").pixel_values
    
    # Generate text
    generated_ids = _trocr_model.generate(pixel_values)
    generated_text = _trocr_processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
    
    return generated_text

def _pytesseract_text_from_image(image: Image.Image, optimize_handwriting: bool = True) -> str:
    if not OCR_AVAILABLE:
        raise RuntimeError('Tesseract OCR not available')
    
    # Preprocess for handwritten text
    if optimize_handwriting:
        image = _preprocess_for_handwriting(image)
    
    # Use handwriting-optimized Tesseract config
    custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,:/()%mgml- '
    # PSM 6 = Assume a single uniform block of text (better for prescriptions)
    # OEM 3 = Default OCR engine mode
    
    try:
        text = pytesseract.image_to_string(image, config=custom_config)
        # Fallback if custom config fails
        if not text or len(text.strip()) < 5:
            text = pytesseract.image_to_string(image, config='--psm 6')
    except Exception:
        # Final fallback without custom config
        text = pytesseract.image_to_string(image)
    
    return text

@app.route('/extract_prescription', methods=['POST'])
def extract_prescription():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401

    # Check if OCR service is available
    if not OCR_SERVICE_AVAILABLE or not is_ocr_available():
        return jsonify({'success': False, 'error': 'EasyOCR not available. Install: pip install easyocr'}), 500

    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file uploaded'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'Empty filename'}), 400

    try:
        img_bytes = file.read()
        image = Image.open(io.BytesIO(img_bytes)).convert('RGB')
        
        # Use OCR service to extract prescription data
        result = extract_prescription_data(image)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify({'success': False, 'error': result.get('error', 'OCR extraction failed')}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/recommendations')
def recommendations():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    user_id = session['user_id']
    
    # Import ML recommendation engine
    try:
        from ml_recommendation_service import recommendation_engine
        recommendations = recommendation_engine.get_smart_recommendations(user_id)
    except ImportError:
        # Fallback to database lookup
        query = "SELECT * FROM medicine_recommendations ORDER BY medicine_name LIMIT 10"
        recommendations = execute_query(query)
    
    return render_template('recommendations.html', recommendations=recommendations or [])

@app.route('/ml_models')
def ml_models():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    return render_template('ml_models.html')

@app.route('/dosage_optimization')
def dosage_optimization():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    user_id = session['user_id']
    
    # Import ML dosage engine
    try:
        from ml_dosage_service import dosage_engine
        recommendations = dosage_engine.get_dosage_recommendations(user_id)
    except ImportError:
        # Fallback to database lookup
        recommendations = []
    
    return render_template('dosage_optimization.html', recommendations=recommendations)

@app.route('/take_medicine', methods=['POST'])
def take_medicine():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'})
    
    try:
        user_id = session['user_id']
        medicine_id = request.json.get('medicine_id')
        
        # Get current medicine data
        med_query = "SELECT * FROM user_medicines WHERE id = %s AND user_id = %s"
        medicine = execute_query(med_query, (medicine_id, user_id))
        
        if not medicine:
            return jsonify({'success': False, 'error': 'Medicine not found'})
        
        medicine = medicine[0]
        current_doses = medicine.get('daily_doses_taken', 0)
        total_required = medicine.get('total_doses_required', 1)
        
        # Incrementipon dose k;a daily
        new_doses = min(current_doses + 1, total_required)
        
        # Update database medipcipne vla
        query = """
            UPDATE user_medicines 
            SET daily_doses_taken = %s,
                last_taken_date = CURDATE(),
                adherence_score = LEAST(adherence_score + 5, 100),
                last_taken = NOW()
            WHERE id = %s AND user_id = %s
        """
        execute_query(query, (new_doses, medicine_id, user_id))
        
        # Gameipfiped : bdge vgera k; liye
        points = 0
        if GAMIFICATION_ENABLED and gamification_engine:
            points = gamification_engine.calculate_points(user_id, medicine_id, dose_taken=True, on_time=True)
            gamification_engine.add_points(user_id, points)
            new_streak = gamification_engine.update_streak(user_id)
            
            # bdge chk;r
            if new_streak == 1:
                gamification_engine.award_badge(user_id, 'first_dose')
            elif new_streak == 7:
                gamification_engine.award_badge(user_id, 'week_streak')
            elif new_streak == 30:
                gamification_engine.award_badge(user_id, 'month_streak')
        
        # Check if all doses taken for today
        is_complete = new_doses >= total_required
        
        return jsonify({
            'success': True, 
            'doses_taken': new_doses,
            'total_required': total_required,
            'is_complete': is_complete,
            'points_earned': points
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/miss_medicine', methods=['POST'])
def miss_medicine():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'})
    
    try:
        user_id = session['user_id']
        medicine_id = request.json.get('medicine_id')
        
        # Update k;rega adherence score missed k; liye
        query = """
            UPDATE user_medicines 
            SET adherence_score = GREATEST(adherence_score - 10, 0)
            WHERE id = %s AND user_id = %s
        """
        execute_query(query, (medicine_id, user_id))
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/remove_medicine', methods=['POST'])
def remove_medicine():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'})
    
    try:
        user_id = session['user_id']
        medicine_id = request.json.get('medicine_id')
        
        if not medicine_id:
            return jsonify({'success': False, 'error': 'Medicine ID required'})
        
        # Update medicine status to '0'
        query = """
            UPDATE user_medicines 
            SET status = '0'
            WHERE id = %s AND user_id = %s
        """
        execute_query(query, (medicine_id, user_id))
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/clear_medicines', methods=['POST'])
def clear_medicines():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'})
    
    try:
        user_id = session['user_id']
        query = "UPDATE user_medicines SET status = '0' WHERE user_id = %s"
        execute_query(query, (user_id,))
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/gamification')
def gamification():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    user_id = session['user_id']
    
    if GAMIFICATION_ENABLED and gamification_engine:
        stats = gamification_engine.get_user_stats(user_id)
        return render_template('gamification.html', stats=stats)
    else:
        return render_template('gamification.html', stats=None)

@app.route('/analytics')
def analytics():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    user_id = session['user_id']
    
    if ANALYTICS_ENABLED and analytics_engine:
        analytics_data = analytics_engine.calculate_user_analytics(user_id)
        return render_template('analytics.html', analytics=analytics_data)
    else:
        return render_template('analytics.html', analytics=None)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    print("Starting MediTrek Flask App...")
    print("Database: 231 medicines, 375 interactions")
    print("URL: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
