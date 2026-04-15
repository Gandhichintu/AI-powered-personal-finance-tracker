import pandas as pd
import numpy as np
import joblib
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns

class ExpenseCategoryTrainer:
    def __init__(self, data_path='data/expense_categories.csv'):
        self.data_path = os.path.join(os.path.dirname(__file__), data_path)
        self.model_path = os.path.join(os.path.dirname(__file__), 'models')
        self.pipeline = None
        self.vectorizer = None
        self.classifier = None
        self.categories = None
        
        # Create models directory if it doesn't exist
        os.makedirs(self.model_path, exist_ok=True)
    
    def load_data(self):
        """Load and preprocess the dataset"""
        print("📊 Loading dataset...")
        df = pd.read_csv(self.data_path)
        
        # Clean data
        df['description'] = df['description'].str.lower().str.strip()
        df['category'] = df['category'].str.strip()
        
        # Remove any rows with missing values
        df = df.dropna()
        
        print(f"✅ Loaded {len(df)} samples")
        print(f"📊 Categories: {df['category'].value_counts().to_dict()}")
        
        return df['description'], df['category']
    
    def create_pipeline(self):
        """Create ML pipeline with TF-IDF and Logistic Regression"""
        self.pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(
                max_features=5000,
                ngram_range=(1, 2),  # Use both unigrams and bigrams
                stop_words='english',
                min_df=2,  # Ignore terms that appear in less than 2 documents
                max_df=0.8  # Ignore terms that appear in more than 80% of documents
            )),
            ('clf', LogisticRegression(
                solver='lbfgs',  # lbfgs supports multinomial automatically
                max_iter=1000,
                C=1.0,
                random_state=42
                # multi_class parameter removed - it's auto-detected
            ))
        ])
        
        print("✅ Created ML pipeline")
    
    def train(self, X, y):
        """Train the model"""
        print("🚀 Training model...")
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Train pipeline
        self.pipeline.fit(X_train, y_train)
        
        # Evaluate
        y_pred = self.pipeline.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        
        print(f"✅ Model trained with accuracy: {accuracy:.4f}")
        print("\n📈 Classification Report:")
        print(classification_report(y_test, y_pred))
        
        # Cross-validation
        cv_scores = cross_val_score(self.pipeline, X, y, cv=5)
        print(f"\n📊 Cross-validation scores: {cv_scores}")
        print(f"📊 Average CV score: {cv_scores.mean():.4f} (+/- {cv_scores.std() * 2:.4f})")
        
        # Get categories
        self.categories = self.pipeline.classes_
        
        # Plot confusion matrix
        self.plot_confusion_matrix(y_test, y_pred)
        
        return accuracy
    
    def plot_confusion_matrix(self, y_test, y_pred):
        """Plot and save confusion matrix"""
        plt.figure(figsize=(10, 8))
        cm = confusion_matrix(y_test, y_pred)
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
                    xticklabels=self.pipeline.classes_,
                    yticklabels=self.pipeline.classes_)
        plt.title('Confusion Matrix')
        plt.xlabel('Predicted')
        plt.ylabel('Actual')
        plt.xticks(rotation=45)
        plt.yticks(rotation=45)
        plt.tight_layout()
        
        # Save plot
        plot_path = os.path.join(self.model_path, 'confusion_matrix.png')
        plt.savefig(plot_path)
        print(f"✅ Confusion matrix saved to {plot_path}")
        plt.close()
    
    def save_model(self):
        """Save the trained model and vectorizer"""
        model_file = os.path.join(self.model_path, 'expense_category_model.pkl')
        joblib.dump(self.pipeline, model_file)
        
        # Save categories separately for reference
        categories_file = os.path.join(self.model_path, 'categories.txt')
        with open(categories_file, 'w') as f:
            for cat in self.categories:
                f.write(f"{cat}\n")
        
        print(f"✅ Model saved to {model_file}")
        print(f"✅ Categories saved to {categories_file}")
    
    def load_model(self):
        """Load a trained model"""
        model_file = os.path.join(self.model_path, 'expense_category_model.pkl')
        if os.path.exists(model_file):
            self.pipeline = joblib.load(model_file)
            self.categories = self.pipeline.classes_
            print(f"✅ Model loaded from {model_file}")
            return True
        return False
    
    def predict(self, description):
        """Predict category for a single description"""
        if self.pipeline is None:
            if not self.load_model():
                raise Exception("No trained model found. Please train first.")
        
        # Clean input
        description = description.lower().strip()
        
        # Predict
        category = self.pipeline.predict([description])[0]
        probabilities = self.pipeline.predict_proba([description])[0]
        
        # Get top 3 predictions with confidence
        top_3_idx = np.argsort(probabilities)[-3:][::-1]
        top_3 = [(self.categories[i], probabilities[i]) for i in top_3_idx]
        
        return {
            'category': category,
            'confidence': float(max(probabilities)),
            'top_3': top_3,
            'all_categories': list(zip(self.categories, probabilities))
        }

def main():
    """Main training function"""
    trainer = ExpenseCategoryTrainer()
    
    # Load data
    X, y = trainer.load_data()
    
    # Create pipeline
    trainer.create_pipeline()
    
    # Train model
    accuracy = trainer.train(X, y)
    
    # Save model
    trainer.save_model()
    
    # Test predictions
    print("\n🔍 Testing predictions:")
    test_descriptions = [
        "pizza hut dinner",
        "uber to airport",
        "electricity bill",
        "netflix monthly",
        "grocery shopping",
        "rent payment",
        "doctor appointment"
    ]
    
    for desc in test_descriptions:
        result = trainer.predict(desc)
        print(f"  '{desc}' -> {result['category']} (confidence: {result['confidence']:.2f})")

if __name__ == "__main__":
    main()