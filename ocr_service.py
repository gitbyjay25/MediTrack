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
    """Enhance image specifically for printed text OCR (ignore handwriting)."""
    if img.mode != 'RGB':
        img = img.convert('RGB')

    # Convert to grayscale
    img = img.convert('L')
    arr = np.array(img)

    # Light Gaussian denoising (remove paper noise)
    try:
        from scipy import ndimage
        arr = ndimage.gaussian_filter(arr, sigma=0.3)
    except ImportError:
        img = img.filter(ImageFilter.MedianFilter(size=3))
        arr = np.array(img)

    img = Image.fromarray(arr)

    # Boost clarity & contrast for printed fonts
    img = ImageEnhance.Contrast(img).enhance(1.8)
    img = ImageEnhance.Sharpness(img).enhance(2.2)
    img = ImageOps.autocontrast(img, cutoff=2)

    # Slight brightness boost if background is dark
    if np.mean(arr) < 125:
        img = ImageEnhance.Brightness(img).enhance(1.25)

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
    """Extract text using EasyOCR (optimized for printed text only)."""
    global _reader

    if not EASYOCR_AVAILABLE:
        raise RuntimeError("EasyOCR not available. Install using: pip install easyocr torch torchvision")

    if _reader is None:
        _reader = easyocr.Reader(['en'], gpu=False, quantize=True)

    image = _preprocess_image(image)

    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        image.save(tmp.name, format='PNG', quality=100, optimize=True)
        tmp_path = tmp.name

    try:
        results = _reader.readtext(
            tmp_path,
            detail=1,
            paragraph=False,
            width_ths=0.6,
            height_ths=0.6,
            text_threshold=0.7,
            contrast_ths=0.3,
            adjust_contrast=0.6,
            mag_ratio=1.0,
            slope_ths=0.1,
            ycenter_ths=0.5,
        )

        # Keep only printed/high-confidence text (ignore faint/handwritten)
        lines = [t for _, t, conf in results if conf >= 0.55]
        text = "\n".join(lines)

        if not text.strip():
            raise RuntimeError("No clear printed text detected. Please upload a well-lit printed prescription.")

        return _clean_text(text)

    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass

def parse_prescription_text(text: str) -> Dict[str, Optional[str]]:
    """Parse multiple medicines (name, dosage, frequency) and patient details from OCR text"""
    lines = re.split(r'[\n\r]+', text)
    lines = [ln.strip() for ln in lines if ln.strip()]

    # Merge broken "Rx" lines
    merged_lines = []
    skip_next = False
    for i, ln in enumerate(lines):
        if skip_next:
            skip_next = False
            continue
        if re.fullmatch(r'(R|Rx|RxI|Rx1|Rxi|Rxl)\.?\s*', ln.strip(), re.IGNORECASE):
            if i + 1 < len(lines):
                merged_lines.append(f"{ln.strip()} {lines[i + 1].strip()}")
                skip_next = True
            else:
                merged_lines.append(ln)
        else:
            merged_lines.append(ln)
    lines = merged_lines

    # Debug merged lines
    print("\nDebug: Merged Lines:")
    for i, ln in enumerate(lines):
        print(f"{i+1:02d}: {ln}")

    # Data structure
    data = {
        'medicines': [],
        'age': None,
        'age_group': None,
        'weight': None,
        'height': None,
        'gender': None,
        'purpose': None
    }

    freq_keywords = {
        'once daily': ['once daily', 'od', 'qd', 'daily', 'one daily'],
        'twice daily': ['twice daily', 'bd', 'bid', '2x daily', 'two daily'],
        'three times daily': ['three times daily', 'tds', 'tid', '3x daily', 'thrice daily'],
        'four times daily': ['four times daily', 'qid', '4x daily', 'every 6 hours'],
        'as needed': ['sos', 'prn', 'as needed']
    }

    # Extract medicines
    for ln in lines:
        if not ln:
            continue

        # Skip non-medicine lines
        if re.search(
            r'\b(phone|address|license|npi|health|avenue|business|city|clinic|hospital|street|road|block|internal|specialist|patient|date|dob|dr|doctor|allergies|gender|weight|height|purpose|penicillin)\b',
            ln, re.IGNORECASE):
            continue

        # Skip instructions
        if re.match(r'^(take|give|apply|use)\b', ln, re.IGNORECASE):
            continue

        # Must have dosage clue
        if not re.search(r'(mg|ml|tab|tablet|cap|capsule|syrup|drop|ointment|cream)', ln, re.IGNORECASE):
            continue

        # Clean line
        cand = re.sub(r"^[\-\d\.\)\s]+", "", ln)
        cand = re.sub(r"^r\s*x\s*\d*\s*[:\.]?\s*", "", cand, flags=re.IGNORECASE)
        cand = re.sub(r'^\b[IVX]+\.\s*', '', cand, flags=re.IGNORECASE)

        # Extract medicine name + dosage
        match = re.search(r"([A-Za-z][A-Za-z0-9\-]+)\s+(\d+(?:\.\d+)?)\s*(mg|ml|mcg|g|iu)?", cand, re.IGNORECASE)
        if not match:
            continue

        med_name = match.group(1).capitalize()
        dose = match.group(2) + " " + (match.group(3) or "")

        # Detect frequency
        freq = None
        lower_ln = ln.lower()
        for key, words in freq_keywords.items():
            if any(k in lower_ln for k in words):
                freq = key
                break

        # Store if unique
        if not any(m['name'].lower() == med_name.lower() for m in data['medicines']):
            data['medicines'].append({
                'name': med_name,
                'dosage': dose.strip(),
                'frequency': freq
            })

    print("\n✅ Extracted structured medicines:")
    for m in data['medicines']:
        print(m)

    # Extract patient details
    for ln in lines:
        # Age
        if not data['age']:
            m = re.search(r"\b(age|yrs?|years?)\b[\s:]*([0-9]{1,3})", ln, re.IGNORECASE)
            if m:
                data['age'] = m.group(2)
        # Weight
        if not data['weight']:
            m = re.search(r"\b(weight|wt)\b[\s:]*([0-9]{1,3}(?:\.[0-9]+)?)", ln, re.IGNORECASE)
            if m:
                data['weight'] = m.group(2)
        # Height
        if not data['height']:
            m = re.search(r"\b(height|ht)\b[\s:]*([0-9]{2,3})", ln, re.IGNORECASE)
            if m:
                data['height'] = m.group(2)
        # Gender
        # Gender
        if not data['gender']:
            # 🔍 Debug print to see OCR line
            print(f"🔍 Checking line for gender: {ln}")

            # Match all possible OCR variants like:
            # "Gender: Male", "Gender : Ma1e", "Sex- F", "GENDER Male", "Sex | Female"
            m = re.search(
                r"\b(gender|sex)\b[\s:;=\-\|]*([A-Za-z0-9]+)",
                ln, re.IGNORECASE
            )

            if m:
                g = m.group(2).lower()
                g = g.replace('1', 'l').replace('0', 'o').replace('|', 'l').replace('€', 'e')
                print(f"✅ Gender pattern matched: {g}")

                if g.startswith('m'):
                    data['gender'] = 'Male'
                elif g.startswith('f'):
                    data['gender'] = 'Female'
                elif g.startswith('o'):
                    data['gender'] = 'Other'

            else:
                # 🔁 Backup: search for standalone words if label missing
                if re.search(r'\bmale\b', ln, re.IGNORECASE):
                    print("✅ Found standalone 'male'")
                    data['gender'] = 'Male'
                elif re.search(r'\bfemale\b', ln, re.IGNORECASE):
                    print("✅ Found standalone 'female'")
                    data['gender'] = 'Female'
                elif re.search(r'\bother\b', ln, re.IGNORECASE):
                    print("✅ Found standalone 'other'")
                    data['gender'] = 'Other'

        # Purpose
        if not data['purpose']:
            m = re.search(r"(purpose|for)\s*[:\-]?\s*(.+)", ln, re.IGNORECASE)
            if m:
                data['purpose'] = m.group(2).strip()

    # Determine age group
    if data['age']:
        try:
            age_val = int(data['age'])
            if age_val < 18:
                data['age_group'] = "pediatric"
            elif 18 <= age_val < 65:
                data['age_group'] = "adult"
            else:
                data['age_group'] = "elderly"
        except ValueError:
            data['age_group'] = None

    # --- ✅ Backward compatibility for templates ---
    if data.get('medicines'):
        first_med = data['medicines'][0]
        data['med_name'] = first_med.get('name')
        data['dosage'] = first_med.get('dosage')
        data['frequency'] = first_med.get('frequency')
    # -------------------------------------------------
    print("\n🧩 RETURNING DATA TO FRONTEND:", data)

    return data








def extract_prescription_data(image: Image.Image) -> Dict:
    """Complete extraction pipeline"""
    try:
        text = extract_text_from_image(image)
        print("\n================ OCR RAW TEXT OUTPUT ================\n")
        print(text)
        print("\n=====================================================\n")
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