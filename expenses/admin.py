# expenses/admin.py
from django.contrib import admin
from django import forms
from .models import Expense, Category
from ml_model.predict import classifier

# Register Category
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)

admin.site.register(Category, CategoryAdmin)

# Register Expense with custom admin
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('id', 'owner', 'description', 'vendor', 'amount', 'date', 'category')
    list_filter = ('category', 'date')
    search_fields = ('vendor', 'description', 'owner__username')
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        
        # Add ML preview for new expenses
        if not obj and classifier and classifier.is_loaded():
            form.base_fields['ml_preview'] = forms.CharField(
                required=False,
                label='ML Category Preview',
                widget=forms.TextInput(attrs={
                    'readonly': 'readonly',
                    'style': 'background-color: #f8f9fa; color: #495057;'
                })
            )
        
        return form
    
    class Media:
        js = ('js/ml_preview.js',)

admin.site.register(Expense, ExpenseAdmin)