import csv
import os
from typing import List, Dict, Any


from ml.rec_model import medicine_model

class MedicineRecommendationEngine:
    def __init__(self):
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_path = os.path.join(base_dir, 'database', 'data', 'medicines.csv')
            
            self.medicines = self._load_csv_data(data_path)
            
            
            medicine_model.load_and_train()
            self.ml_model = medicine_model
            
            print(" Recommendation engine ready!")
                
        except Exception as e:
            print(f"Engine init error: {e}")
            self.ml_model = None
            self.medicines = []
    
    def _load_csv_data(self, filepath: str) -> List[Dict[str, str]]:
        medicines = []
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file, delimiter=';')
                for row in reader:
                    cleaned_row = {}
                    for key, value in row.items():
                        cleaned_row[key.strip()] = value.strip() if value else ''
                    medicines.append(cleaned_row)
            return medicines
        except Exception:
            return []
    
    def predict_medicine_category(self, medicine_name: str) -> Dict[str, str]:
        if not self.ml_model:
            return {}
        
        try:
            category, confidence = self.ml_model.predict(medicine_name)
            
            print(f" ML Prediction: '{medicine_name}' → {category} (confidence: {confidence:.2f})")
            
            return {
                'main_category': category,
                'confidence': confidence,
                'source': 'ml_model'
            }
            
        except Exception as e:
            print(f"ML prediction failed: {e}")
            return {}
    
    def find_alternatives(self, medicine_name: str, max_results: int = 5) -> List[Dict[str, Any]]:
        if not self.medicines:
            return []
        
        medicine_lower = medicine_name.lower().strip()
        print(f"🔍 Finding alternatives for: {medicine_name}")
        
        # Try ML prediction first
        ml_categories = self.predict_medicine_category(medicine_name)
        
        # Try to find exact match in database
        medicine_match = None
        for med in self.medicines:
            med_name = med.get('medicine_name', '').lower().strip()
            if medicine_lower == med_name:
                medicine_match = med
                print(f" founded in db")
                break
        
       # use ml pred 
        if not medicine_match and ml_categories and ml_categories.get('confidence', 0) > 0.5:
            ml_category = ml_categories.get('main_category')
            
            if ml_category and ml_category != 'UNKNOWN':
                matches = []
                for med in self.medicines:
                    if (med.get('main_category') == ml_category and 
                        med.get('medicine_name', '').lower() != medicine_lower):
                        matches.append(med)
                        if len(matches) >= max_results:
                            break
                
                if matches:
                    recommendations = []
                    for med in matches:
                        
                        score = 0.85
                        recommendations.append(self._format_recommendation(med, 'ml_predicted', score))
                    
                    print(f"Using ML-predicted category: {ml_category} - Found {len(recommendations)} alternatives")
                    return recommendations
        
        # If no ML prediction or no match, use database logic
        if not medicine_match:
            print(f" no db mtch , keywrd srch")
            return self._get_recommendations_by_keywords(medicine_name, max_results)
        
        # Database-based recommendations
        main_category = medicine_match.get('main_category', '')
        sub_category_1 = medicine_match.get('sub_category_1', '')
        sub_category_2 = medicine_match.get('sub_category_2', '')
        
        print(f" Database categories: {main_category} > {sub_category_1} > {sub_category_2}")
        
        recommendations = []
        
        # Level 1: Same sub_category_2
        if sub_category_2:
            matches = self._find_medicines_by_category(
                main_category=main_category,
                sub_category_1=sub_category_1,
                sub_category_2=sub_category_2,
                exclude_medicine=medicine_match.get('medicine_name'),
                max_results=max_results
            )
            for med in matches:
                recommendations.append(self._format_recommendation(med, 'subcat2', 1.0))
            print(f" Level 1 (subcat2): Found {len(matches)}")
        
        # Level 2: Same sub_category_1
        if sub_category_1 and len(recommendations) < max_results:
            matches = self._find_medicines_by_category(
                main_category=main_category,
                sub_category_1=sub_category_1,
                sub_category_2='',
                exclude_medicine=medicine_match.get('medicine_name'),
                exclude_medicines=[r['medicine_name'] for r in recommendations],
                max_results=max_results - len(recommendations)
            )
            for med in matches:
                recommendations.append(self._format_recommendation(med, 'subcat1', 0.8))
            print(f" Level 2 (subcat1): Found {len(matches)}")
        
        # Level 3: Same main_category
        if len(recommendations) < max_results:
            matches = self._find_medicines_by_category(
                main_category=main_category,
                sub_category_1='',
                sub_category_2='',
                exclude_medicine=medicine_match.get('medicine_name'),
                exclude_medicines=[r['medicine_name'] for r in recommendations],
                max_results=max_results - len(recommendations)
            )
            for med in matches:
                recommendations.append(self._format_recommendation(med, 'category', 0.6))
            print(f" Level 3 (category): Found {len(matches)}")
        
        if not recommendations:
            print(" No category matches, using related medicines")
            return self._get_related_medicines(medicine_match, max_results)
        
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        print(f" Returning {len(recommendations)} recommendations")
        return recommendations[:max_results]
    
    def _find_medicines_by_category(self, main_category: str, sub_category_1: str, sub_category_2: str, 
                                  exclude_medicine: str, exclude_medicines: List[str] = None, 
                                  max_results: int = 5) -> List[Dict]:
        if exclude_medicines is None:
            exclude_medicines = []
        
        matches = []
        exclude_lower = exclude_medicine.lower()
        exclude_list_lower = [med.lower() for med in exclude_medicines]
        
        for med in self.medicines:
            med_name = med.get('medicine_name', '').lower()
            
            if med_name == exclude_lower or med_name in exclude_list_lower:
                continue
            
            matches_main = not main_category or med.get('main_category') == main_category
            matches_sub1 = not sub_category_1 or med.get('sub_category_1') == sub_category_1
            matches_sub2 = not sub_category_2 or med.get('sub_category_2') == sub_category_2
            
            if matches_main and matches_sub1 and matches_sub2:
                matches.append(med)
                if len(matches) >= max_results:
                    break
        
        return matches
    
    def _get_related_medicines(self, original_med: Dict, max_results: int) -> List[Dict[str, Any]]:
        original_name = original_med.get('medicine_name', '').lower()
        main_category = original_med.get('main_category', '')
        
        matches = []
        for med in self.medicines:
            if (med.get('main_category') == main_category and 
                med.get('medicine_name', '').lower() != original_name):
                matches.append(med)
                if len(matches) >= max_results:
                    break
        
        recommendations = []
        for med in matches:
            recommendations.append(self._format_recommendation(med, 'related', 0.5))
        
        return recommendations
    
    def _get_recommendations_by_keywords(self, medicine_name: str, max_results: int) -> List[Dict[str, Any]]:
        medicine_lower = medicine_name.lower()
        
        medicine_keywords = {
            'calcium': 'VITAMINS AND MINERALS',
            'warfarin': 'CARDIOVASCULAR MEDICINES', 
            'vitamin': 'VITAMINS AND MINERALS',
            'metformin': 'MEDICINES FOR ENDOCRINE DISORDERS',
            'amoxicillin': 'ANTI-INFECTIVE MEDICINES',
            'aspirin': 'ANALGESICS',
            'ibuprofen': 'ANALGESICS',
            'paracetamol': 'ANALGESICS'
        }
        
        category = None
        for keyword, cat in medicine_keywords.items():
            if keyword in medicine_lower:
                category = cat
                break
        
        if category and self.medicines:
            matches = []
            for med in self.medicines:
                if med.get('main_category') == category:
                    matches.append(med)
                    if len(matches) >= max_results:
                        break
            
            recommendations = []
            for med in matches:
                recommendations.append(self._format_recommendation(med, 'keyword', 0.7))
            return recommendations
        
        return self._get_fallback_recommendations(max_results)
    
    def _format_recommendation(self, medicine_data: Dict, source: str, score: float) -> Dict[str, Any]:
        return {
            'medicine_name': medicine_data.get('medicine_name', ''),
            'generic_name': medicine_data.get('generic_name', ''),
            'main_category': medicine_data.get('main_category', ''),
            'sub_category_1': medicine_data.get('sub_category_1', ''),
            'sub_category_2': medicine_data.get('sub_category_2', ''),
            'specific_indication': medicine_data.get('specific_indication', ''),
            'source': source,
            'score': score
        }
    
    def _get_fallback_recommendations(self, max_results: int) -> List[Dict[str, Any]]:
        common_medicine_names = ['Paracetamol', 'Amoxicillin', 'Metformin', 'Aspirin', 'Ibuprofen']
        recommendations = []
        
        for med in self.medicines:
            if med.get('medicine_name') in common_medicine_names and len(recommendations) < max_results:
                recommendations.append(self._format_recommendation(med, 'fallback', 0.3))
        
        return recommendations

def get_recommendations_for_user(user_id, db_connection, max_recommendations=10):
    try:
        engine = MedicineRecommendationEngine()
        
        query = "SELECT medicine_name FROM user_medicines WHERE user_id = %s AND status = 'active'"
        cursor = db_connection.cursor()
        cursor.execute(query, (user_id,))
        user_medicines_rows = cursor.fetchall()
        cursor.close()
        
        user_medicines = []
        for row in user_medicines_rows:
            if isinstance(row, dict):
                if row.get('medicine_name'):
                    user_medicines.append({'medicine_name': row['medicine_name']})
            else:
                if row and row[0]:
                    user_medicines.append({'medicine_name': row[0]})
        
        print(f"👤 User has {len(user_medicines)} active medicines")
        
        if not user_medicines:
            return []
        
        all_recommendations = []
        for medicine_row in user_medicines:
            medicine_name = medicine_row['medicine_name']
            alternatives = engine.find_alternatives(medicine_name, max_results=5)
            
            for alt in alternatives:
                alt['original_medicine'] = medicine_name
                all_recommendations.append(alt)
        
        # Remove duplicates
        unique_recommendations = {}
        for rec in all_recommendations:
            key = rec['medicine_name']
            if key not in unique_recommendations or rec['score'] > unique_recommendations[key]['score']:
                unique_recommendations[key] = rec
        
        final_recommendations = sorted(unique_recommendations.values(), 
                                     key=lambda x: x['score'], reverse=True)
        
        print(f" FINAL: Returning {len(final_recommendations)} unique recommendations")
        
        # Check if ML was used
        ml_used = any(rec.get('source') == 'ml_predicted' for rec in final_recommendations)
        if ml_used:
            print(" ML MODEL WAS USED IN RECOMMENDATIONS!")
        
        return final_recommendations[:max_recommendations]
        
    except Exception as e:
        print(f"User recommendation error: {e}")
        return []

recommendation_engine = MedicineRecommendationEngine()