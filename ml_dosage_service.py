import pickle
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestRegressor
import numpy as np
from database.db_config import execute_query
import re

class DosageOptimizationEngine:
    def __init__(self):
        self.model = None
        self.tfidf = None
        self.load_model()
    
    def load_model(self):
        try:
            # Try to load trained model files
            with open('ml/Models/dosage_model.pkl', 'rb') as f:
                self.model = pickle.load(f)
            with open('ml/Models/dosage_tfidf.pkl', 'rb') as f:
                self.tfidf = pickle.load(f)
            print("✅ Dosage Optimization ML Model loaded successfully!")
        except FileNotFoundError:
            print("⚠️ Dosage Optimization ML Model files not found, using database lookup")
            self.model = None
    
    def extract_dosage_value(self, dosage_text):
        """Extract numerical dosage value from text"""
        if not dosage_text:
            return 0
        
        # Extract numbers from dosage text
        numbers = re.findall(r'\d+\.?\d*', str(dosage_text))
        if numbers:
            return float(numbers[0])
        return 0
    
    def predict_optimal_dosage(self, medicine_name, age_group='adult', weight=None):
        """Predict optimal dosage using ML model"""
        if not self.model:
            return self.get_database_dosage(medicine_name, age_group)
        
        try:
            # Prepare input features
            features = f"{medicine_name} {age_group}"
            if weight:
                features += f" {weight}kg"
            
            # Transform using TF-IDF
            X = self.tfidf.transform([features])
            
            # Get prediction
            predicted_dosage = self.model.predict(X)[0]
            
            return {
                'predicted_dosage': predicted_dosage,
                'confidence': 0.8,  # ML confidence
                'source': 'ML Model',
                'recommendation': f"ML suggests {predicted_dosage:.1f}mg for {age_group}"
            }
            
        except Exception as e:
            print(f"ML prediction error: {e}")
            return self.get_database_dosage(medicine_name, age_group)
    
    def get_database_dosage(self, medicine_name, age_group='adult'):
        """Get dosage from database"""
        query = """
            SELECT * FROM dosage_optimization 
            WHERE medicine_name LIKE %s
            LIMIT 1
        """
        result = execute_query(query, (f'%{medicine_name}%',))
        
        if result and result[0]:
            dosage_data = result[0]
            
            # Get appropriate dosage based on age group
            if age_group == 'pediatric' and dosage_data['pediatric_dosage']:
                dosage_text = dosage_data['pediatric_dosage']
            elif age_group == 'elderly' and dosage_data['elderly_dosage']:
                dosage_text = dosage_data['elderly_dosage']
            else:
                dosage_text = dosage_data['adult_dosage']
            
            dosage_value = self.extract_dosage_value(dosage_text)
            
            return {
                'predicted_dosage': dosage_value,
                'confidence': 0.9,  # High confidence for database results
                'source': 'Database',
                'recommendation': f"Database suggests {dosage_text} for {age_group}",
                'full_dosage_info': dosage_data
            }
        
        return None
    
    def get_dosage_recommendations(self, user_id):
        """Get dosage recommendations for user's medicines"""
        # Get user's medicines with age group and weight
        query = """
            SELECT medicine_name, dosage, age_group, weight FROM user_medicines 
            WHERE user_id = %s AND status = 'active'
        """
        user_medicines = execute_query(query, (user_id,)) or []
        
        recommendations = []
        
        for med in user_medicines:
            medicine_name = med['medicine_name']
            current_dosage = self.extract_dosage_value(med['dosage'])
            age_group = med['age_group'] or 'adult'
            weight = med['weight']
            
            # Get optimal dosage
            optimal = self.predict_optimal_dosage(medicine_name, age_group, weight)
            
            if optimal:
                recommendations.append({
                    'medicine_name': medicine_name,
                    'current_dosage': current_dosage,
                    'optimal_dosage': optimal['predicted_dosage'],
                    'age_group': age_group,
                    'weight': weight,
                    'recommendation': optimal['recommendation'],
                    'source': optimal['source'],
                    'confidence': optimal['confidence']
                })
        
        return recommendations

# Global instance
dosage_engine = DosageOptimizationEngine()
