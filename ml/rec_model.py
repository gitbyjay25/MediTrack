# ml/simple_model.py
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
import os

class SimpleMedicineModel:
    def __init__(self):
        self.model = None
        self.categories = []
        self.medicine_map = {}
        
    def load_and_train(self):
        
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_path = os.path.join(base_dir, 'database', 'data', 'medicines.csv')
            
            df = pd.read_csv(data_path, delimiter=';')
            print(f" Training model on {len(df)} medicines")
            
            # med_map fr mtch
            for _, row in df.iterrows():
                if pd.notna(row['medicine_name']):
                    self.medicine_map[row['medicine_name'].lower()] = row['main_category']
            
            # training dta prep 
            texts = []
            labels = []
            
            for _, row in df.iterrows():
                if pd.notna(row['medicine_name']) and pd.notna(row['main_category']):
                    text = str(row['medicine_name']).lower()
                    if pd.notna(row['generic_name']):
                        text += " " + str(row['generic_name']).lower()
                    
                    texts.append(text)
                    labels.append(row['main_category'])
            
            # Train model
            if len(set(labels)) > 1:
                self.model = Pipeline([
                    ('tfidf', TfidfVectorizer(max_features=100, stop_words='english')),
                    ('clf', RandomForestClassifier(n_estimators=50, random_state=42))
                ])
                self.model.fit(texts, labels)
                self.categories = self.model.classes_
                print(f" Model trained on  {len(texts)} samples")
            else:
                print("less data")
                
        except Exception as e:
            print(f"train fail: {e}")
    
    def predict(self, medicine_name):
        #med cate pred
        medicine_lower = medicine_name.lower().strip()
        
        # Exact match
        if medicine_lower in self.medicine_map:
            return self.medicine_map[medicine_lower], 1.0
        
        # ml 
        if self.model:
            try:
                prediction = self.model.predict([medicine_lower])[0]
                proba = self.model.predict_proba([medicine_lower])[0]
                confidence = np.max(proba)
                
                if confidence > 0.3:  # Only use if confident
                    return prediction, confidence
            except Exception as e:
                print(f"ML prediction failed: {e}")
        
        # 3. Keyword mtch
        keyword_rules = {
            'VITAMINS AND MINERALS': ['vitamin', 'calcium', 'mineral', 'iron', 'zinc'],
            'CARDIOVASCULAR MEDICINES': ['blood', 'pressure', 'heart', 'warfarin', 'cholesterol'],
            'ANALGESICS': ['pain', 'ache', 'fever', 'paracetamol', 'aspirin', 'ibuprofen'],
            'ANTI-INFECTIVE MEDICINES': ['antibiotic', 'infection', 'amoxicillin', 'antiviral'],
            'MEDICINES FOR ENDOCRINE DISORDERS': ['diabetes', 'metformin', 'insulin', 'thyroid'],
            'GASTROINTESTINAL MEDICINES': ['stomach', 'acid', 'ulcer', 'digestion'],
            'RESPIRATORY MEDICINES': ['cough', 'asthma', 'breathing', 'respiratory']
        }
        
        for category, keywords in keyword_rules.items():
            if any(keyword in medicine_lower for keyword in keywords):
                return category, 0.7
        
        return 'UNKNOWN', 0.5

medicine_model = SimpleMedicineModel()