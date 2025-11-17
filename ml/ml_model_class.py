# ml/ml_model_class.py
import pandas as pd
import numpy as np
import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
import re

class MedicineClassifier:
    def __init__(self, data_path='medicines.csv'):
        # Load dataset
        self.df = pd.read_csv(data_path, delimiter=';')
        self.medicine_to_category = {}
        self.generic_to_category = {}
        self.ml_model = None
        self._build_knowledge_base()
        self._train_ml_model()

    def _build_knowledge_base(self):
        """Create lookup dictionaries for exact matching"""
        for _, row in self.df.iterrows():
            if pd.notna(row['medicine_name']):
                self.medicine_to_category[row['medicine_name'].lower()] = row['main_category']
            if pd.notna(row['generic_name']):
                self.generic_to_category[row['generic_name'].lower()] = row['main_category']

        print(f"Knowledge base: {len(self.medicine_to_category)} medicines, {len(self.generic_to_category)} generics")

    def _train_ml_model(self):
        """Train ML model for unknown medicines"""
        texts = []
        labels = []

        for _, row in self.df.iterrows():
            text_parts = []
            for col in ['medicine_name', 'generic_name', 'sub_category_1', 'sub_category_2', 'specific_indication']:
                if pd.notna(row[col]):
                    text_parts.append(str(row[col]))

            if text_parts:
                texts.append(' '.join(text_parts).lower())
                labels.append(row['main_category'])

        # Train model if we have enough data
        if len(set(labels)) > 1:
            self.ml_model = Pipeline([
                ('tfidf', TfidfVectorizer(max_features=500, ngram_range=(1, 2))),
                ('clf', LogisticRegression(class_weight='balanced', max_iter=1000))
            ])
            self.ml_model.fit(texts, labels)
            print(f"ML model trained on {len(texts)} samples")

    def predict(self, text, top_k=3):
        """Main prediction function"""
        text_lower = text.lower().strip()

        # 1. Exact match
        if text_lower in self.medicine_to_category:
            return [(self.medicine_to_category[text_lower], 1.0)]
        if text_lower in self.generic_to_category:
            return [(self.generic_to_category[text_lower], 1.0)]

        # 2. Partial match
        for med, category in self.medicine_to_category.items():
            if text_lower in med or med in text_lower:
                return [(category, 0.9)]

        # 3. ML prediction
        if self.ml_model is not None:
            try:
                probs = self.ml_model.predict_proba([text_lower])[0]
                categories = self.ml_model.classes_
                top_indices = np.argsort(probs)[-top_k:][::-1]
                results = [(categories[i], probs[i]) for i in top_indices if probs[i] > 0.1]
                if results and results[0][1] > 0.3:
                    return results
            except:
                pass

        # 4. Keyword matching
        keyword_rules = {
            'VITAMINS AND MINERALS': ['vitamin', 'calcium', 'zinc', 'iron', 'b1', 'b2', 'b6', 'b12', 'mineral'],
            'ANTI-INFECTIVE MEDICINES': ['antibiotic', 'antiviral', 'antifungal', 'infection', 'bacterial'],
            'CARDIOVASCULAR MEDICINES': ['warfarin', 'blood pressure', 'cholesterol', 'heart', 'cardiac'],
            'MEDICINES FOR ENDOCRINE DISORDERS': ['diabetes', 'insulin', 'metformin', 'thyroid', 'endocrine'],
            'MEDICINES FOR MENTAL AND BEHAVIOURAL DISORDERS': ['mental', 'behavioral', 'antidepressant', 'anxiety'],
        }

        matches = []
        for category, keywords in keyword_rules.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                matches.append((category, score))

        if matches:
            total = sum(score for _, score in matches)
            return [(cat, score/total) for cat, score in matches[:top_k]]

        return [("UNKNOWN", 1.0)]

    def add_medicine(self, name, generic, category):
        """Add new medicine to knowledge base"""
        self.medicine_to_category[name.lower()] = category
        if generic:
            self.generic_to_category[generic.lower()] = category
        print(f"Added: {name} → {category}")

    def save(self, path='medicine_classifier.pkl'):
        with open(path, 'wb') as f:
            pickle.dump(self, f)
        print(f"Classifier saved to {path}")

    @classmethod
    def load(cls, path='medicine_classifier.pkl'):
        with open(path, 'rb') as f:
            return pickle.load(f)