import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_tracker.settings')
django.setup()

from ml_model.predict import classifier

def test_classifier():
    print("🔍 Testing Expense Classifier")
    print("=" * 50)
    
    if not classifier.is_loaded():
        print("❌ Model not loaded. Please train first.")
        return
    
    print(f"✅ Model loaded with {len(classifier.get_categories())} categories")
    print(f"📊 Categories: {classifier.get_categories()}")
    print()
    
    test_cases = [
        "pizza hut dinner with friends",
        "uber to airport",
        "electricity bill payment",
        "netflix monthly subscription",
        "grocery shopping at walmart",
        "monthly rent payment",
        "doctor consultation",
        "amazon purchase headphones",
        "movie tickets",
        "gas station fuel"
    ]
    
    print("📝 Test Results:")
    print("-" * 50)
    
    for desc in test_cases:
        result = classifier.predict(desc)
        confidence_percent = result['confidence'] * 100
        
        # Color coding based on confidence
        if result['confidence'] > 0.8:
            status = "✅ HIGH"
        elif result['confidence'] > 0.5:
            status = "⚠️ MEDIUM"
        else:
            status = "❌ LOW"
        
        print(f"{desc[:30]:<30} -> {result['category']:<12} [{status}] {confidence_percent:.1f}%")
    
    print("=" * 50)

if __name__ == "__main__":
    test_classifier()