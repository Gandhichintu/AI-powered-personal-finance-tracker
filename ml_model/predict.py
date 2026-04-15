import joblib
import os
import numpy as np
from pathlib import Path
from django.conf import settings

class ExpenseClassifier:
    """Wrapper class for expense categorization"""
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern to load model only once"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Load the model"""
        model_path = os.path.join(os.path.dirname(__file__), 'models', 'expense_category_model.pkl')
        
        if not os.path.exists(model_path):
            print(f"⚠️ Model not found at {model_path}")
            print("Please run train_model.py first")
            self.model = None
            self.categories = []
            return
        
        try:
            self.model = joblib.load(model_path)
            self.categories = self.model.classes_
            print(f"✅ Expense classifier loaded with {len(self.categories)} categories")
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            self.model = None
            self.categories = []
        self.min_confidence = getattr(settings, 'MODEL_CONFIG', {}).get('MIN_CONFIDENCE', 0.1)
    
    def predict(self, description, min_confidence=0.3):
        """
        Predict category for a description
        
        Args:
            description: Text description of expense
            min_confidence: Minimum confidence threshold (0-1)
            
        Returns:
            dict: {'category': predicted_category, 'confidence': confidence_score}
        """
        if self.model is None:
            return {
                'category': 'Other',
                'confidence': 0.0,
                'error': 'Model not loaded'
            }
        
        # Clean input
        description = description.lower().strip()
        if not description:
            return {
                'category': 'Other',
                'confidence': 0.0
            }
        
        try:
            # Get prediction
            category = self.model.predict([description])[0]
            probabilities = self.model.predict_proba([description])[0]
            confidence = float(max(probabilities))
            
            # If confidence is too low, return 'Other'
            if confidence < min_confidence:
                return {
                    'category': 'Other',
                    'confidence': confidence
                }
            
            return {
                'category': category,
                'confidence': confidence
            }
            
        except Exception as e:
            print(f"❌ Prediction error: {e}")
            return {
                'category': 'Other',
                'confidence': 0.0,
                'error': str(e)
            }
    
    def predict_batch(self, descriptions):
        """Predict categories for multiple descriptions"""
        if self.model is None:
            return [{'category': 'Other', 'confidence': 0.0} for _ in descriptions]
        
        try:
            categories = self.model.predict(descriptions)
            probabilities = self.model.predict_proba(descriptions)
            
            results = []
            for i, cat in enumerate(categories):
                confidence = float(max(probabilities[i]))
                results.append({
                    'category': cat,
                    'confidence': confidence
                })
            
            return results
            
        except Exception as e:
            print(f"❌ Batch prediction error: {e}")
            return [{'category': 'Other', 'confidence': 0.0} for _ in descriptions]
    
    def get_categories(self):
        """Get list of all categories"""
        if hasattr(self, 'categories') and self.categories is not None:
            return list(self.categories)
        return []
    
    def is_loaded(self):
        """Check if model is loaded"""
        return self.model is not None


# Create global instance
classifier = ExpenseClassifier()