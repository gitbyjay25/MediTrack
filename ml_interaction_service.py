import pickle
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
import numpy as np
from database.db_config import execute_query

class DrugInteractionEngine:
    def __init__(self):
        self.model = None
        self.tfidf = None
        self.label_encoder = None
        self.load_model()
    
    def load_model(self):
        try:
            # Try to load trained model files
            with open('ml/Models/interaction_model.pkl', 'rb') as f:
                self.model = pickle.load(f)
            with open('ml/Models/interaction_tfidf.pkl', 'rb') as f:
                self.tfidf = pickle.load(f)
            with open('ml/Models/interaction_label_encoder.pkl', 'rb') as f:
                self.label_encoder = pickle.load(f)
            print(" Drug Interaction ML Model loaded successfully!")
        except FileNotFoundError:
            print(" Drug Interaction ML Model files not found, using database lookup")
            self.model = None
    
    def predict_interaction_severity(self, drug1, drug2):
        """Predict interaction severity using ML model"""
        if not self.model:
            return self.get_database_interaction(drug1, drug2)
        
        try:
            # Combine drug names for prediction
            drug_text = f"{drug1} {drug2}"
            
            # Transform using TF-IDF
            X = self.tfidf.transform([drug_text])
            
            # Get prediction
            prediction = self.model.predict(X)[0]
            probability = self.model.predict_proba(X)[0]
            
            # Get confidence
            confidence = max(probability)
            
            # Map prediction to severity
            severity_map = {0: 'Low', 1: 'Medium', 2: 'High'}
            predicted_severity = severity_map.get(prediction, 'Unknown')
            
            return {
                'severity': predicted_severity,
                'confidence': confidence,
                'description': f"ML predicted {predicted_severity} interaction between {drug1} and {drug2}",
                'recommendation': f"Consult healthcare provider before combining {drug1} and {drug2}",
                'source': 'ML Model'
            }
            
        except Exception as e:
            print(f"ML prediction error: {e}")
            return self.get_database_interaction(drug1, drug2)
    
    def get_database_interaction(self, drug1, drug2):
        """Get interaction from database"""
        query = """
            SELECT * FROM interactions 
            WHERE (drug1 = %s AND drug2 = %s) OR (drug1 = %s AND drug2 = %s)
            ORDER BY 
                CASE severity_level 
                    WHEN 'High' THEN 1 
                    WHEN 'Medium' THEN 2 
                    WHEN 'Low' THEN 3 
                    ELSE 4 
                END
            LIMIT 1
        """
        result = execute_query(query, (drug1, drug2, drug2, drug1))
        
        if result and result[0]:
            interaction = result[0]
            return {
                'severity': interaction['severity_level'],
                'confidence': 0.9,  # High confidence for database results
                'description': interaction['description'],
                'recommendation': interaction['recommendation'],
                'source': 'Database'
            }
        
        return None
    
    def check_multiple_interactions(self, medicines):
        """Check interactions between multiple medicines"""
        interactions = []
        
        for i in range(len(medicines)):
            for j in range(i + 1, len(medicines)):
                drug1 = medicines[i]['medicine_name']
                drug2 = medicines[j]['medicine_name']
                
                interaction = self.predict_interaction_severity(drug1, drug2)
                if interaction:
                    interactions.append({
                        'drug1': drug1,
                        'drug2': drug2,
                        **interaction
                    })
        
        return interactions

# Global instance
interaction_engine = DrugInteractionEngine()
