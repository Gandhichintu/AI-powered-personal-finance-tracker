import pandas as pd
import numpy as np
from prophet import Prophet
from datetime import datetime, timedelta
from django.utils import timezone
from .models import MonthlyAggregate
import logging
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

class ExpensePredictor:
    """Predict future expenses using Prophet"""
    
    def __init__(self, user):
        self.user = user
        self.model = None
        self.historical_data = None
    
    def prepare_data(self):
        """Prepare historical data for Prophet"""
        # Get monthly aggregates
        aggregates = MonthlyAggregate.objects.filter(
            user=self.user
        ).order_by('month')
        
        if aggregates.count() < 6:  # Need at least 6 months of data
            logger.warning(f"Insufficient data for user {self.user.username}. Need at least 6 months.")
            return None
        
        # Convert to DataFrame
        data = []
        for agg in aggregates:
            data.append({
                'ds': agg.month,
                'y': float(agg.total_expense)
            })
        
        df = pd.DataFrame(data)
        self.historical_data = df
        return df
    
    def train_prophet(self, seasonality_mode='multiplicative'):
        """Train Prophet model on historical data"""
        df = self.prepare_data()
        
        if df is None:
            return False
        
        try:
            # Initialize Prophet
            self.model = Prophet(
                yearly_seasonality=True,
                weekly_seasonality=False,
                daily_seasonality=False,
                seasonality_mode=seasonality_mode,
                changepoint_prior_scale=0.05,
                seasonality_prior_scale=10.0
            )
            
            # Add custom seasonality for monthly patterns
            self.model.add_seasonality(
                name='monthly',
                period=30.5,
                fourier_order=5
            )
            
            # Fit the model
            self.model.fit(df)
            
            logger.info(f"✅ Prophet model trained successfully for {self.user.username}")
            return True
            
        except Exception as e:
            logger.error(f"Error training Prophet: {e}")
            return False
    
    def predict_future(self, periods=3):
        """Predict future months"""
        if self.model is None:
            if not self.train_prophet():
                return None
        
        try:
            # Create future dataframe
            future = self.model.make_future_dataframe(
                periods=periods,
                freq='ME',
                include_history=True
            )
            
            # Make predictions
            forecast = self.model.predict(future)
            
            # Get last 'periods' predictions
            predictions = forecast.tail(periods)
            
            result = []
            for _, row in predictions.iterrows():
                result.append({
                    'date': row['ds'],
                    'predicted': round(row['yhat'], 2),
                    'lower_bound': round(row['yhat_lower'], 2),
                    'upper_bound': round(row['yhat_upper'], 2)
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error making predictions: {e}")
            return None
    
    def get_forecast_components(self):
        """Get forecast components for insights"""
        if self.model is None:
            if not self.train_prophet():
                return None
        
        future = self.model.make_future_dataframe(periods=3, freq='ME')
        forecast = self.model.predict(future)
        
        components = {
            'trend': forecast['trend'].tail(3).tolist(),
            'yearly': forecast['yearly'].tail(3).tolist(),
            'monthly': forecast['monthly'].tail(3).tolist()
        }
        
        return components
    
    def generate_insights(self, predictions):
        """Generate smart insights from predictions"""
        if not predictions:
            return None
        
        insights = []
        
        # Get current month's total
        current_month = timezone.now().date().replace(day=1)
        current_aggregate = MonthlyAggregate.objects.filter(
            user=self.user,
            month=current_month
        ).first()
        
        current_total = float(current_aggregate.total_expense) if current_aggregate else 0
        
        # Next month prediction
        next_month = predictions[0]
        predicted = next_month['predicted']
        
        if current_total > 0:
            change = ((predicted - current_total) / current_total) * 100
            
            if change > 20:
                insights.append({
                    'type': 'increase',
                    'icon': '📈',
                    'message': f"Your predicted spending is {change:.0f}% higher than this month. Consider reviewing your budget.",
                    'priority': 'high'
                })
            elif change < -10:
                insights.append({
                    'type': 'decrease',
                    'icon': '📉',
                    'message': f"Your predicted spending is {abs(change):.0f}% lower. Great job!",
                    'priority': 'medium'
                })
            else:
                insights.append({
                    'type': 'stable',
                    'icon': '📊',
                    'message': f"Your spending is predicted to remain stable (±{abs(change):.0f}%).",
                    'priority': 'low'
                })
        
        # Budget recommendation
        recommended_budget = predicted * 1.05  # 5% buffer
        insights.append({
            'type': 'budget',
            'icon': '💰',
            'message': f"Based on your trend, consider setting a budget of ₹{int(recommended_budget)} for next month.",
            'priority': 'medium'
        })
        
        # Check if there's a seasonal pattern
        if len(predictions) >= 2:
            seasonal_change = ((predictions[1]['predicted'] - predictions[0]['predicted']) / predictions[0]['predicted']) * 100
            if abs(seasonal_change) > 15:
                insights.append({
                    'type': 'seasonal',
                    'icon': '🌍',
                    'message': f"Seasonal pattern detected: {seasonal_change:.0f}% change expected next month.",
                    'priority': 'medium'
                })
        
        return insights
    
    def get_budget_suggestion(self, predictions):
        """Get smart budget suggestion"""
        if not predictions:
            return None
        
        # Use weighted average of predictions
        weights = [0.5, 0.3, 0.2]  # More weight on near-term predictions
        weighted_avg = sum(p['predicted'] * w for p, w in zip(predictions[:3], weights[:len(predictions)]))
        
        # Add 10% buffer for unexpected expenses
        suggested_budget = weighted_avg * 1.1
        
        # Get category breakdown from last month
        last_month = timezone.now().date().replace(day=1) - timedelta(days=1)
        last_aggregate = MonthlyAggregate.objects.filter(
            user=self.user,
            month=last_month.replace(day=1)
        ).first()
        
        category_suggestions = []
        if last_aggregate and last_aggregate.categories:
            categories = last_aggregate.categories
            total = sum(categories.values())
            
            for cat, amount in categories.items():
                percentage = (amount / total) * 100
                suggested = (percentage / 100) * suggested_budget
                category_suggestions.append({
                    'category': cat,
                    'percentage': round(percentage, 1),
                    'suggested': round(suggested, 2)
                })
        
        return {
            'month': predictions[0]['date'].strftime('%B %Y'),
            'predicted': round(predictions[0]['predicted'], 0),
            'range': (round(predictions[0]['lower_bound'], 0), round(predictions[0]['upper_bound'], 0)),
            'suggested_budget': round(suggested_budget, 0),
            'category_breakdown': category_suggestions,
            'confidence': 'high' if (predictions[0]['upper_bound'] - predictions[0]['lower_bound']) / predictions[0]['predicted'] < 0.3 else 'medium'
        }