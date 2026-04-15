from django.core.management.base import BaseCommand
from ml_model.train_model import ExpenseCategoryTrainer

class Command(BaseCommand):
    help = 'Train the expense categorization model'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--data',
            type=str,
            default='data/expense_categories.csv',
            help='Path to training data CSV'
        )
    
    def handle(self, *args, **options):
        self.stdout.write("🚀 Starting model training...")
        
        trainer = ExpenseCategoryTrainer(data_path=options['data'])
        
        # Load data
        X, y = trainer.load_data()
        
        # Create pipeline
        trainer.create_pipeline()
        
        # Train model
        accuracy = trainer.train(X, y)
        
        # Save model
        trainer.save_model()
        
        self.stdout.write(self.style.SUCCESS(f"✅ Model trained successfully with accuracy: {accuracy:.4f}"))