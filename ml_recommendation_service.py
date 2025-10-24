import pickle
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
import numpy as np
from database.db_config import execute_query

class MedicineRecommendationEngine:
    def __init__(self):
        self.model = None
        self.tfidf = None
        self.label_encoder = None
        self.load_model()
    
    def load_model(self):
        try:
            # Try to load trained model files
            with open('ml/Models/recommendation_model.pkl', 'rb') as f:
                self.model = pickle.load(f)
            with open('ml/Models/recommendation_tfidf.pkl', 'rb') as f:
                self.tfidf = pickle.load(f)
            with open('ml/Models/recommendation_label_encoder.pkl', 'rb') as f:
                self.label_encoder = pickle.load(f)
            print("✅ ML Recommendation Model loaded successfully!")
        except FileNotFoundError:
            print("⚠️ ML Recommendation Model files not found, using database lookup")
            self.model = None
    
    def get_recommendations_by_condition(self, condition):
        """Get recommendations from database based on condition"""
        query = """
            SELECT medicine_name, primary_conditions, secondary_conditions, 
                   contraindications, medical_condition
            FROM medicine_recommendations 
            WHERE primary_conditions LIKE %s OR secondary_conditions LIKE %s
            ORDER BY medicine_name
        """
        results = execute_query(query, (f'%{condition}%', f'%{condition}%'))
        return results or []
    
    def get_recommendations_by_ml(self, user_medicines):
        """Get ML-powered recommendations based on user's current medicines"""
        if not self.model:
            return self.get_fallback_recommendations(user_medicines)
        
        try:
            # Combine user medicines into text
            medicine_text = ' '.join([med['medicine_name'] for med in user_medicines])
            
            # Transform using TF-IDF
            X = self.tfidf.transform([medicine_text])
            
            # Get prediction probabilities
            probabilities = self.model.predict_proba(X)[0]
            classes = self.label_encoder.classes_
            
            # Get top 5 recommendations
            top_indices = np.argsort(probabilities)[-5:][::-1]
            recommendations = []
            
            for idx in top_indices:
                if probabilities[idx] > 0.1:  # Only if confidence > 10%
                    category = classes[idx]
                    # Get medicines in this category
                    meds = self.get_medicines_by_category(category)
                    recommendations.extend(meds[:2])  # Top 2 from each category
            
            return recommendations[:10]  # Return top 10
            
        except Exception as e:
            print(f"ML prediction error: {e}")
            return self.get_fallback_recommendations(user_medicines)
    
    def get_medicines_by_category(self, category):
        """Get medicines from database by category"""
        query = """
            SELECT medicine_name, primary_conditions, secondary_conditions
            FROM medicine_recommendations 
            WHERE primary_conditions LIKE %s
            LIMIT 5
        """
        return execute_query(query, (f'%{category}%',)) or []
    
    def get_fallback_recommendations(self, user_medicines):
        """Fallback recommendations based on user's current medicines"""
        recommendations = []
        
        for med in user_medicines:
            # Get related medicines from database
            query = """
                SELECT medicine_name, primary_conditions, secondary_conditions
                FROM medicine_recommendations 
                WHERE medicine_name != %s 
                AND (primary_conditions LIKE %s OR secondary_conditions LIKE %s)
                LIMIT 3
            """
            med_name = med['medicine_name']
            related = execute_query(query, (med_name, f'%{med_name}%', f'%{med_name}%'))
            if related:
                recommendations.extend(related)
        
        return recommendations[:10]
    
    def get_smart_recommendations(self, user_id):
        """Get smart recommendations combining ML and database"""
        # Get user's current medicines
        user_meds_query = """
            SELECT medicine_name FROM user_medicines 
            WHERE user_id = %s AND status = 'active'
        """
        user_medicines = execute_query(user_meds_query, (user_id,)) or []
        
        if not user_medicines:
            # If no medicines, show general recommendations
            return self.get_general_recommendations()
        
        # Get ML-powered recommendations
        ml_recs = self.get_recommendations_by_ml(user_medicines)
        
        # Get condition-based recommendations
        condition_recs = []
        for med in user_medicines:
            # Extract condition from medicine name or get from database
            condition_recs.extend(self.get_recommendations_by_condition(med['medicine_name']))
        
        # Combine and deduplicate
        all_recs = ml_recs + condition_recs
        seen = set()
        unique_recs = []
        
        for rec in all_recs:
            key = rec['medicine_name']
            if key not in seen:
                seen.add(key)
                unique_recs.append(rec)
        
        return unique_recs[:15]  # Return top 15
    
    def get_general_recommendations(self):
        """Get general recommendations when user has no medicines"""
        query = """
            SELECT medicine_name, primary_conditions, secondary_conditions
            FROM medicine_recommendations 
            ORDER BY RAND()
            LIMIT 10
        """
        return execute_query(query) or []

# Global instance
recommendation_engine = MedicineRecommendationEngine()
