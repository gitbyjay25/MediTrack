"""
OCR Service for Prescription Text Extraction
"""
import re
import os
import tempfile
from typing import Dict, Optional
from datetime import datetime

try:
    from PIL import Image, ImageOps, ImageFilter, ImageEnhance
    import numpy as np
except ImportError:
    raise ImportError("PIL and numpy required")

EASYOCR_AVAILABLE = False
_reader = None

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except Exception:
    pass


def _preprocess_image(img: Image.Image) -> Image.Image:
    """Optimize image for printed text OCR"""
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    img = img.convert('L')
    arr = np.array(img)
    
    # Light denoise
    try:
        from scipy import ndimage
        arr = ndimage.gaussian_filter(arr, sigma=0.5)
    except ImportError:
        img = img.filter(ImageFilter.MedianFilter(size=3))
        arr = np.array(img)
    
    img = Image.fromarray(arr)
    img = ImageEnhance.Contrast(img).enhance(1.3)
    img = img.filter(ImageFilter.SHARPEN)
    img = ImageOps.autocontrast(img, cutoff=2)
    
    if np.mean(arr) < 120:
        img = ImageEnhance.Brightness(img).enhance(1.2)
    
    return img


def _clean_text(text: str) -> str:
    """Normalize OCR output"""
    if not text:
        return text
    
    lines = []
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue
        
        line = re.sub(r'\s+', ' ', line)
        line = re.sub(r'\s*([,.:;!?])\s*', r'\1 ', line)
        line = re.sub(r'\b0D\b', 'OD', line)
        line = re.sub(r'\bBD\b', 'BD', line)
        line = re.sub(r'\bTDS\b', 'TDS', line)
        line = re.sub(r'\bQID\b', 'QID', line)
        line = re.sub(r'\b(\d+)\s*MG\b', r'\1 mg', line, flags=re.IGNORECASE)
        line = re.sub(r'\b(\d+)\s*ML\b', r'\1 ml', line, flags=re.IGNORECASE)
        line = re.sub(r'\b(\d+)\s*MCG\b', r'\1 mcg', line, flags=re.IGNORECASE)
        
        lines.append(line)
    
    return '\n'.join(lines)


def extract_text_from_image(image: Image.Image) -> str:
    """Extract text using EasyOCR"""
    global _reader
    
    if not EASYOCR_AVAILABLE:
        raise RuntimeError('EasyOCR not available')
    
    if _reader is None:
        _reader = easyocr.Reader(['en'], gpu=False, quantize=True)
    
    image = _preprocess_image(image)
    
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        image.save(tmp.name, format='PNG', quality=95, optimize=False)
        tmp_path = tmp.name
    
    try:
        results = _reader.readtext(
            tmp_path,
            detail=1,
            paragraph=False,
            width_ths=0.7,
            height_ths=0.7,
            text_threshold=0.7,
            link_threshold=0.4,
            adjust_contrast=0.5,
            canvas_size=2560,
            mag_ratio=1.0,
            slope_ths=0.1,
            ycenter_ths=0.5,
        )
        
        text = "\n".join([t for _, t, conf in results if conf >= 0.5])
        return _clean_text(text) or text
        
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass


def parse_prescription_text(text: str) -> Dict[str, Optional[str]]:
    """Parse prescription fields from OCR text"""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    
    # Patterns
    dosage_rx = re.compile(
        r"\b((\d+(?:\.\d+)?)\s*(mg|mcg|g|ml|iu|units))|"
        r"((\d+(?:\.\d+)?)\s*(tablet|tab|capsule|cap|pill|pills))|"
        r"((\d+(?:\.\d+)?)\s*(teaspoon|tsp|tablespoon|tbsp|tb\s+spoon|drop|drops|ml))|"
        r"((\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)\s*(mg|ml))|"
        r"((\d+(?:\.\d+)?)\s*%\s*(w/w|w/v|cream|ointment))|"
        r"((\d+(?:\.\d+)?)\s*(caps|capsules))",
        re.IGNORECASE
    )
    
    freq_map = {
        'once daily': ['od', 'once daily', 'qd', 'daily', 'q.d.', 'q24h', 'q 24h', 'once a day', '1x daily', 
                       'by mouth daily', 'by mouth-daily', 'mouth daily', 'mouth-daily', 'orally daily'],
        'twice daily': ['bd', 'twice daily', 'bid', 'b.i.d', 'b.i.d.', 'q12h', 'q 12h', '2x daily', 
                        'twice a day', 'by mouth twice', 'mouth twice'],
        'three times daily': ['tid', 't.d.s', 'tds', 't.i.d', 't.i.d.', 'three times', '3x daily', 
                              'thrice daily', 'by mouth three times', 'mouth three times'],
        'four times daily': ['qid', 'q.i.d', 'q.i.d.', 'q6h', 'q 6h', '4x daily', 'four times'],
        'every 8 hours': ['q8h', 'q 8h', 'every 8 hours', 'every 8 hrs', 'every eight hours'],
        'every 12 hours': ['q12h', 'q 12h', 'every 12 hours', 'every 12 hrs', 'every twelve hours'],
        'at bedtime': ['hs', 'qhs', 'at bedtime', 'bedtime', 'night', 'nightly'],
        'as needed': ['sos', 'prn', 'p.r.n', 'as needed', 'when required', 'as directed'],
        'every 6 hours': ['q6h', 'q 6h', 'every 6 hours', 'every 6 hrs'],
    }
    
    header_rx = re.compile(
        r"(dr\.?|doctor|physician|specialist|patient|dob|age|sex|gender|date|address|phone|"
        r"license|allergies|weight|height|diagnosis|prescription|rx\s*no|reg\s*no|"
        r"internal\s*medicine|md|npi|health\s*ave|business\s*city)\b",
        re.IGNORECASE
    )
    
    med_patterns = [
        re.compile(r"^\s*rx\s*\d*\s*[:\.]?\s*([A-Za-z][A-Za-z0-9\-\s]{2,})\s+(\d+(?:\.\d+)?)\s*(mg|mcg|g|ml|iu)\s*(tablet|tab|capsule|cap|syrup|drops)?", re.IGNORECASE),
        re.compile(r"^\s*rx\s*[:\.]?\s*([A-Za-z][A-Za-z0-9\-\s]{2,})\s+(\d+(?:\.\d+)?)\s*(mg|mcg|g|ml|iu)", re.IGNORECASE),
        re.compile(r"^\s*\d+\.?\s+([A-Za-z][A-Za-z0-9\-\s]{2,})\s+(\d+(?:\.\d+)?)\s*(mg|mcg|g|ml|iu)", re.IGNORECASE),
        re.compile(r"^([A-Za-z][A-Za-z0-9\-\s]{2,})\s+(\d+(?:\.\d+)?)\s*(mg|mcg|g|ml|iu)\s*(tablet|tab|capsule|cap|syrup|drops|cream|ointment)?", re.IGNORECASE),
        re.compile(r"^([A-Z][a-z]+\s+[A-Z][a-z]+)\s+(\d+(?:\.\d+)?)\s*(mg|mcg|g|ml)", re.IGNORECASE),
        re.compile(r"^\s*([A-Za-z][A-Za-z0-9\-\s]{3,})\s*[,:]?\s*(\d+(?:\.\d+)?)\s*(mg|mcg|g|ml)\b", re.IGNORECASE),
        re.compile(r"^([A-Za-z][A-Za-z0-9\-\s]{2,})\s*[\(\[].*?(\d+(?:\.\d+)?)\s*(mg|mcg|g|ml)", re.IGNORECASE),
        re.compile(r"^([A-Za-z][A-Za-z0-9\-\s]{2,})\s+(\d+(?:\.\d+)?)\s*(mg|mcg|g|ml)", re.IGNORECASE),
    ]
    
    name_patterns = [
        re.compile(r"^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*(?:\d+\s*(?:mg|mcg|g|ml))?", re.IGNORECASE),
        re.compile(r"^([A-Z][a-z]{3,})\b", re.IGNORECASE),
    ]
    
    # Extra patterns for purpose and gender
    purpose_pattern = re.compile(r"\b(purpose|indication|reason|dx\.?|diagnosis)\b\s*[:\-]?\s*(.+)$", re.IGNORECASE)
    gender_pattern_labeled = re.compile(r"\b(gender|sex)\b\s*[:\-]?\s*(male|female|other|m|f|o)\b", re.IGNORECASE)
    gender_pattern_standalone = re.compile(r"\b(male|female)\b", re.IGNORECASE)

    data = {
        'med_name': None, 'dosage': None, 'frequency': None, 'time': None,
        'purpose': None, 'age': None, 'age_group': None, 
        'weight': None, 'height': None, 'allergies': None, 'gender': None
    }
    
    # Extract medicine name and dosage
    for ln in lines:
        if data['med_name'] is None or data['dosage'] is None:
            for pattern in med_patterns:
                m = pattern.search(ln)
                if m:
                    name = m.group(1).strip(' -,:')
                    name = re.sub(r'\b(sig|take|tablet|capsule|tab|cap|syrup|drops|cream|ointment)\b', '', name, flags=re.IGNORECASE).strip()
                    
                    dose_val, dose_unit = None, None
                    if len(m.groups()) >= 3 and m.group(2) and m.group(3):
                        dose_val, dose_unit = m.group(2), m.group(3)
                    elif len(m.groups()) >= 5 and m.group(4) and m.group(5):
                        dose_val, dose_unit = m.group(4), m.group(5)
                    
                    if dose_val and dose_unit:
                        dose = f"{dose_val} {dose_unit}".strip()
                        if data['med_name'] is None and len(name) >= 3:
                            invalid = ['dr', 'doctor', 'patient', 'date', 'weight', 'height', 'internal', 'medicine', 'specialist']
                            if not any(w.lower() in invalid for w in name.split()[:2]):
                                data['med_name'] = name
                        if data['dosage'] is None:
                            data['dosage'] = dose
                        break
    
    # Fallback: extract name without dosage
    if data['med_name'] is None:
        for ln in lines:
            if header_rx.search(ln):
                continue
            if re.search(r'\b(phone|address|license|npi|health\s+ave|business\s+city|specialist|internal\s+medicine)\b', ln, re.IGNORECASE):
                continue
            
            for pattern in name_patterns:
                m = pattern.search(ln)
                if m:
                    name = m.group(1).strip(' -,:')
                    name = re.sub(r'\b(sig|take|tablet|capsule|tab|cap|syrup|drops|cream|ointment|instructions?)\b', '', name, flags=re.IGNORECASE).strip()
                    
                    if len(name) >= 3:
                        words = name.split()
                        invalid = ['dr', 'doctor', 'patient', 'date', 'weight', 'height', 'internal', 'medicine', 'specialist', 'name', 'dob', 'phone', 'address']
                        if not any(w.lower() in invalid for w in words[:2]):
                            data['med_name'] = " ".join(words[:2]) if len(words) > 1 else words[0]
                            break
            if data['med_name']:
                break
    
    # Extract other fields
    for ln in lines:
        # Dosage
        if data['dosage'] is None:
            is_instr = re.search(r'\b(take|sig|instructions?|by\s+mouth|one\s+tablet|twice|thrice)\b', ln, re.IGNORECASE)
            m = dosage_rx.search(ln)
            if m:
                dose = None
                for g in m.groups():
                    if g and g.strip() and not re.match(r'^\d+\s*(tablet|tab|cap|capsule)$', g.strip(), re.IGNORECASE):
                        dose = g.strip()
                        break
                
                if dose:
                    data['dosage'] = dose
                elif m.group(0):
                    dose_text = m.group(0).strip()
                    if not (is_instr and re.match(r'^(tablet|tab|cap|capsule)$', dose_text, re.IGNORECASE)):
                        data['dosage'] = dose_text
        
        # Frequency
        if data['frequency'] is None:
            low = ln.lower()
            for freq, keys in freq_map.items():
                if any(k in low for k in keys):
                    data['frequency'] = freq
                    break
            # Heuristics for simple instruction wording like "take 1/one", etc.
            if data['frequency'] is None:
                if re.search(r"\btake\b\s*(?:1|one)\b", low):
                    data['frequency'] = 'once daily'
                elif re.search(r"\btake\b\s*(?:2|two)\b", low):
                    data['frequency'] = 'twice daily'
                elif re.search(r"\btake\b\s*(?:3|three|thrice)\b", low):
                    data['frequency'] = 'three times daily'
        
        # Time
        if data['time'] is None:
            m = re.search(r"(\d{1,2})\s*:\s*(\d{2})\s*(am|pm)", ln, re.IGNORECASE)
            if m:
                hr, mn, period = m.group(1), m.group(2), m.group(3).upper()
                data['time'] = f"{hr}:{mn} {period}"
            else:
                m = re.search(r"(\d{1,2})\s*:\s*(\d{2})", ln)
                if m:
                    hr, mn = int(m.group(1)), m.group(2)
                    if 0 <= hr <= 23:
                        period = 'AM' if hr < 12 else 'PM'
                        display_hr = hr if hr <= 12 else hr - 12
                        display_hr = 12 if display_hr == 0 else display_hr
                        data['time'] = f"{display_hr}:{mn} {period}"
        
        # Age
        if data['age'] is None:
            m = re.search(r"\b(age|yrs?|years?)\b[\s:]*([0-9]{1,3})", ln, re.IGNORECASE)
            if m:
                age_val = int(m.group(2))
                if 1 <= age_val <= 120:
                    data['age'] = str(age_val)
                    data['age_group'] = 'pediatric' if age_val < 18 else ('elderly' if age_val >= 65 else 'adult')
            
            if data['age'] is None:
                m = re.search(r"\b(?:dob|date\s+of\s+birth|birth\s+date)\b[\s:]*(\d{1,2})\s*(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|june|july|august|september|october|november|december)\s*(\d{4})", ln, re.IGNORECASE)
                if m:
                    try:
                        day, month_str, year = int(m.group(1)), m.group(2).lower(), int(m.group(3))
                        if 1900 <= year <= 2100:
                            months = {'jan':1,'feb':2,'mar':3,'apr':4,'may':5,'jun':6,'jul':7,'aug':8,'sep':9,'oct':10,'nov':11,'dec':12}
                            month = months.get(month_str[:3], 1)
                            age_years = (datetime.now() - datetime(year, month, min(day, 28))).days // 365
                            if 0 <= age_years <= 120:
                                data['age'] = str(age_years)
                                data['age_group'] = 'pediatric' if age_years < 18 else ('elderly' if age_years >= 65 else 'adult')
                    except Exception:
                        pass
        
        # Weight
        if data['weight'] is None:
            m = re.search(r"\b(weight|wt)\b[\s:]*([0-9]{1,3}(?:\.[0-9]+)?)\.?\s*(kg|kgs|kilograms?)?\b", ln, re.IGNORECASE)
            if m:
                data['weight'] = m.group(2)
            else:
                m = re.search(r"\b([0-9]{1,3}(?:\.[0-9]+)?)\.?\s*(kg|kgs|kilograms?)\b", ln, re.IGNORECASE)
                if m and 'tablet' not in ln.lower() and 'capsule' not in ln.lower():
                    data['weight'] = m.group(1)
        
        # Height
        if data['height'] is None:
            m = re.search(r"\b(height|ht)\b[\s:]*j?\s*([0-9]{2,3}(?:\.[0-9]+)?)", ln, re.IGNORECASE)
            if m:
                h_val = float(m.group(2))
                if 50 <= h_val <= 250:
                    data['height'] = m.group(2)
            else:
                m = re.search(r"\b([0-9]{2,3}(?:\.[0-9]+)?)\s*(?:cm|cms|centimeters?)\b", ln, re.IGNORECASE)
                if m:
                    h_val = float(m.group(1))
                    if 50 <= h_val <= 250:
                        data['height'] = m.group(1)
                else:
                    # 5'6" or 5’6” or 5 ft 6 in or 5ft6in
                    m_ft = re.search(r"\b(\d)\s*(?:feet|foot|ft|['’])\s*(\d{1,2})\s*(?:inches|inch|in|[\"”])?\b", ln, re.IGNORECASE)
                    if m_ft:
                        try:
                            ft = int(m_ft.group(1))
                            inch = int(m_ft.group(2))
                            cm = round(ft * 30.48 + inch * 2.54)
                            if 100 <= cm <= 250:
                                data['height'] = str(cm)
                        except Exception:
                            pass
                    else:
                        # 5.6 ft or 5.6ft
                        m_ft_dec = re.search(r"\b(\d+(?:\.\d+)?)\s*ft\b", ln, re.IGNORECASE)
                        if m_ft_dec:
                            try:
                                feet = float(m_ft_dec.group(1))
                                cm = round(feet * 30.48)
                                if 100 <= cm <= 250:
                                    data['height'] = str(cm)
                            except Exception:
                                pass
                        else:
                            # 1.75 m format
                            m_m = re.search(r"\b(\d\.\d{1,2})\s*m\b", ln, re.IGNORECASE)
                            if m_m:
                                try:
                                    meters = float(m_m.group(1))
                                    cm = round(meters * 100)
                                    if 100 <= cm <= 250:
                                        data['height'] = str(cm)
                                except Exception:
                                    pass
        
        # Purpose
        if data['purpose'] is None:
            m = purpose_pattern.search(ln)
            if m:
                data['purpose'] = m.group(2).strip()
            else:
                pf = re.search(r"\bfor\b\s*[:\-]?\s*(.+)$", ln, re.IGNORECASE)
                if pf:
                    data['purpose'] = pf.group(1).strip()
        
        # Allergies
        if data['allergies'] is None:
            m = re.search(r"\ballerg(?:y|ies)\b\s*[:\-]\s*(.+)$", ln, re.IGNORECASE)
            if m:
                data['allergies'] = m.group(1).strip()

        # Gender
        if data['gender'] is None:
            gm = gender_pattern_labeled.search(ln)
            if gm:
                g = gm.group(2).lower()
                data['gender'] = 'male' if g in ('m','male') else ('female' if g in ('f','female') else 'other')
            else:
                gs = gender_pattern_standalone.search(ln)
                if gs:
                    g = gs.group(1).lower()
                    data['gender'] = 'male' if g == 'male' else 'female'
    
    # Last resort: extract medicine name from any valid line
    if data['med_name'] is None:
        for ln in lines:
            if header_rx.search(ln) or re.search(r'\b(phone|address|license|npi|health\s+ave|business\s+city|specialist|internal\s+medicine|patient\s+name|date:|dob:)\b', ln, re.IGNORECASE):
                continue
            
            if re.search(r"^[A-Z][a-z]{2,}", ln) and not re.search(r'^(dr\.?|patient|date|dob|weight|height|allergies|sig|take|instructions)', ln, re.IGNORECASE):
                cand = re.sub(r"^[\-\d\.\)\s]+", "", ln)
                cand = re.sub(r"^r\s*x\s*\d*\s*[:\.]?\s*", "", cand, flags=re.IGNORECASE)
                cand = re.sub(r"\b(tab|tablet|caps|capsule|cap|syrup|drop|drops|inj|injection|ointment|cream|sig|take|instructions?)\b\.?,?\s*", "", cand, flags=re.IGNORECASE)
                
                words = cand.split()
                if words:
                    invalid = ['internal', 'medicine', 'specialist', 'patient', 'doctor', 'dr', 'name', 'date', 'weight', 'height', 'dob']
                    filtered = [w for w in words[:3] if w.lower() not in invalid]
                    if filtered:
                        data['med_name'] = filtered[0]
                        if len(filtered) > 1 and filtered[1][0].isupper():
                            data['med_name'] = " ".join(filtered[:2])
                        break
    
    return data


def extract_prescription_data(image: Image.Image) -> Dict:
    """Complete extraction pipeline"""
    try:
        text = extract_text_from_image(image)
        data = parse_prescription_text(text)
        
        return {
            'success': True,
            'data': data,
            'raw_text': text,
            'engine': 'easyocr'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'data': None,
            'raw_text': None,
            'engine': 'easyocr'
        }


def is_ocr_available() -> bool:
    """Check if EasyOCR is available"""
    return EASYOCR_AVAILABLE