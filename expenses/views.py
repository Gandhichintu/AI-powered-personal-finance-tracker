# expenses/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView
from django.db.models import Sum 
from .models import Expense,Receipt, Category
from .forms import ExpenseForm,ReceiptUploadForm
from django.contrib.auth.mixins import LoginRequiredMixin
import re
from decimal import Decimal, InvalidOperation
from dateutil import parser as dateparser
from PIL import Image, ImageFilter, ImageOps
import pytesseract
from django.contrib import messages
from django.utils import timezone
import cv2
import base64
import os
import json
import stanza
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from ml_model.predict import classifier
from django.contrib import messages
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, UpdateView, DeleteView, ListView, DetailView
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from ml_model.predict import classifier
from django.http import JsonResponse
from .analysis import SpendingAnalyzer
import json
from datetime import datetime
from .anomaly_detector import AnomalyDetector
from .predictor import ExpensePredictor
from datetime import timedelta
from .models import Expense, Receipt, Category, MonthlyAggregate



def dashboard(request):
    # simple static dashboard - later will include charts
    total = 0
    recent = []
    if request.user.is_authenticated:
        recent = Expense.objects.filter(owner=request.user).order_by('-date')[:5] 
        total = Expense.objects.filter(owner=request.user).aggregate(total=Sum('amount'))['total'] or 0
    return render(request, 'expenses/dashboard.html', {'recent': recent, 'total': total})

class ExpenseListView(LoginRequiredMixin, ListView):
    model = Expense
    template_name = 'expenses/expense_list.html'
    context_object_name = 'expenses'
    paginate_by = 15

    def get_queryset(self):
        return Expense.objects.filter(owner=self.request.user).order_by('-date')

@login_required
def expense_create(request):
    if request.method == 'POST':
        form = ExpenseForm(request.POST)
        if form.is_valid():
            exp = form.save(commit=False)
            exp.owner = request.user
            exp.save()
            return redirect('expenses:expense_list')
    else:
        form = ExpenseForm()
    return render(request, 'expenses/expense_form.html', {'form': form, 'title': 'Add Expense'})

@login_required
def expense_update(request, pk):
    expense = get_object_or_404(Expense, pk=pk, owner=request.user)
    
    if request.method == 'POST':
        form = ExpenseForm(request.POST, instance=expense)
        if form.is_valid():
            form.save()
            messages.success(request, 'Expense updated successfully!')
            return redirect('expenses:expense_list')
    else:
        form = ExpenseForm(instance=expense)
        
        # If editing, suggest ML category based on description
        if classifier.is_loaded() and expense.description:
            result = classifier.predict(expense.description)
            if result['confidence'] > 0.3:
                request.session['ml_suggestion'] = {
                    'category': result['category'],
                    'confidence': float(result['confidence'])
                }
    
    context = {
        'form': form, 
        'title': 'Edit Expense',
    }
    return render(request, 'expenses/expense_form.html', context)

@login_required
def expense_delete(request, pk):
    expense = get_object_or_404(Expense, pk=pk, owner=request.user)
    if request.method == 'POST':
        expense.delete()
        return redirect('expenses:expense_list')
    return render(request, 'expenses/expense_confirm_delete.html', {'expense': expense})

@login_required
def receipt_list(request):
    receipts = Receipt.objects.filter(owner=request.user).order_by('-uploaded_at')
    return render(request, 'expenses/receipt_list.html', {'receipts': receipts})

@login_required
def receipt_upload(request):
    if request.method == 'POST':
        form = ReceiptUploadForm(request.POST, request.FILES)
        if form.is_valid():
            rec = form.save(commit=False)
            rec.owner = request.user
            rec.save()

            # Debug: Print receipt info
            print(f"Receipt saved: {rec.id}, Image: {rec.image}")
            
            try:
                # Run OCR and parsing
                image_path = rec.image.path
                print(f"Processing image: {image_path}")

                # 1) Open and pre-process image
                img = Image.open(image_path)
                img = ImageOps.grayscale(img)
                img = ImageOps.autocontrast(img)
                
                # 2) OCR
                ocr_result = pytesseract.image_to_string(img, lang='eng')
                print(f"OCR Result: {ocr_result}")
                
                rec.ocr_text = ocr_result

                # 3) Parse the text
                parsed_amount = parse_amount_from_text(ocr_result)
                parsed_date = parse_date_from_text(ocr_result)
                parsed_vendor = parse_vendor_from_text(ocr_result)
                
                print(f"Parsed - Amount: {parsed_amount}, Date: {parsed_date}, Vendor: {parsed_vendor}")

                # Update receipt with parsed data
                rec.parsed_amount = parsed_amount
                rec.parsed_date = parsed_date
                rec.parsed_vendor = parsed_vendor
                rec.save()

                # Create expense if amount was found
                if parsed_amount:
                    # Use ML to predict category
                    predicted_category = 'Other'
                    if classifier.is_loaded():
                        # Use vendor + OCR text for better prediction
                        text_for_prediction = f"{parsed_vendor or ''} {ocr_result[:200]}"
                        result = classifier.predict(text_for_prediction)
                        if result['confidence'] > 0.3:
                            predicted_category = result['category']
                            print(f"🎯 ML predicted: {predicted_category} (confidence: {result['confidence']:.2f})")
                    
                    expense = Expense.objects.create(
                        owner=request.user,
                        amount=parsed_amount,
                        date=parsed_date or timezone.now().date(),
                        vendor=parsed_vendor or 'Unknown Vendor',
                        description=f"Imported from receipt {rec.pk}",
                        category=predicted_category  # ML predicted category
                    )
                    print(f"Expense created: {expense.id}, Amount: {expense.amount}, Category: {expense.category}")
                    messages.success(request, f"Receipt uploaded and expense created (₹{expense.amount}) in {predicted_category}")
                    return redirect('expenses:expense_list')
                else:
                    messages.warning(request, f"Receipt uploaded but amount could not be parsed. OCR text: {ocr_result[:100]}...")
                    return redirect('expenses:receipt_list')

            except Exception as e:
                print(f"Error processing receipt: {e}")
                messages.error(request, f"Error processing receipt: {e}")
                return redirect('expenses:receipt_list')
    else:
        form = ReceiptUploadForm()
    return render(request, 'expenses/receipt_upload.html', {'form': form})
def parse_amount_from_text(text):
    """
    Smart amount parsing for Indian receipts - handles both numeric and text amounts
    """
    if not text:
        return None
    
    print(f"=== OCR TEXT FOR PARSING ===")
    print(text)
    print("=============================")
    
    lines = text.splitlines()
    
    # Strategy 1: Convert text amounts to numbers first
    text_amount = parse_text_amount(text)
    if text_amount:
        print(f"✅ Found text amount: {text_amount}")
        return text_amount
    
    # Rest of your existing numeric parsing logic...
    payment_keywords = [
        'total', 'amount', 'net amount', 'grand total', 'final amount',
        'payable', 'balance', 'cash', 'card', 'payment', 'due',
        'final total', 'bill amount', 'invoice amount'
    ]
    
    amount_patterns = [
        r'₹\s*(\d+(?:[.,]\d{1,2})?)',
        r'Rs\.?\s*(\d+(?:[.,]\d{1,2})?)',
        r'INR\s*(\d+(?:[.,]\d{1,2})?)',
        r'(\d+(?:[.,]\d{1,2})?)\s*₹',
        r'(\d+(?:[.,]\d{1,2})?)\s*Rs',
    ]
    
    candidate_amounts = []
    
    # Look for amounts near payment keywords
    for i, line in enumerate(lines):
        line_clean = line.strip().lower()
        
        # Check if this line contains payment keywords
        has_payment_keyword = any(keyword in line_clean for keyword in payment_keywords)
        
        if has_payment_keyword:
            print(f"🔍 Found payment keyword in line {i}: '{line}'")
            
            # First, try text amount conversion on this line
            line_text_amount = parse_text_amount(line)
            if line_text_amount:
                print(f"✅ Found text amount '{line_text_amount}' near payment keyword")
                candidate_amounts.append((line_text_amount, 10))
            
            # Then check for numeric amounts
            for pattern in amount_patterns:
                matches = re.finditer(pattern, line, re.IGNORECASE)
                for match in matches:
                    amount_str = match.group(1).replace(',', '')
                    try:
                        amount = Decimal(amount_str)
                        if is_reasonable_amount(amount):
                            print(f"✅ Found numeric amount '{amount}' near payment keyword")
                            candidate_amounts.append((amount, 10))
                    except (InvalidOperation, ValueError):
                        continue
            
            # Check next 2 lines for amounts
            for j in range(1, 3):
                if i + j < len(lines):
                    next_line = lines[i + j].strip()
                    print(f"   Checking line {i+j} after keyword: '{next_line}'")
                    
                    # Try text amount conversion first
                    next_text_amount = parse_text_amount(next_line)
                    if next_text_amount:
                        confidence = 10 - j
                        print(f"✅ Found text amount '{next_text_amount}' in line after keyword")
                        candidate_amounts.append((next_text_amount, confidence))
                    
                    # Then numeric amounts
                    for pattern in amount_patterns:
                        matches = re.finditer(pattern, next_line, re.IGNORECASE)
                        for match in matches:
                            amount_str = match.group(1).replace(',', '')
                            try:
                                amount = Decimal(amount_str)
                                if is_reasonable_amount(amount):
                                    confidence = 10 - j
                                    print(f"✅ Found numeric amount '{amount}' in line after keyword")
                                    candidate_amounts.append((amount, confidence))
                            except (InvalidOperation, ValueError):
                                continue
    
    # Strategy 2: Look for amounts at bottom (with text conversion)
    print("🔍 Checking bottom of receipt...")
    bottom_lines = lines[-5:]
    for i, line in enumerate(bottom_lines):
        line_num = len(lines) - 5 + i
        print(f"   Bottom line {line_num}: '{line.strip()}'")
        
        # Try text amount conversion
        text_amount = parse_text_amount(line)
        if text_amount:
            print(f"✅ Found text amount '{text_amount}' at bottom")
            candidate_amounts.append((text_amount, 8))
        
        # Look for numeric amounts
        standalone_pattern = r'\b(\d{2,}(?:[.,]\d{1,2})?)\b'
        matches = re.finditer(standalone_pattern, line)
        for match in matches:
            amount_str = match.group(1).replace(',', '')
            try:
                amount = Decimal(amount_str)
                if is_reasonable_amount(amount):
                    print(f"✅ Found numeric amount '{amount}' at bottom")
                    candidate_amounts.append((amount, 8))
            except (InvalidOperation, ValueError):
                continue
    
    # Strategy 3: Currency symbols (existing logic)
    print("🔍 Scanning for currency symbols...")
    for i, line in enumerate(lines):
        currency_patterns = [
            r'₹\s*(\d+(?:[.,]\d{1,2})?)',
            r'Rs\.?\s*(\d+(?:[.,]\d{1,2})?)',
            r'INR\s*(\d+(?:[.,]\d{1,2})?)',
        ]
        
        for pattern in currency_patterns:
            matches = re.finditer(pattern, line, re.IGNORECASE)
            for match in matches:
                amount_str = match.group(1).replace(',', '')
                try:
                    amount = Decimal(amount_str)
                    if is_reasonable_amount(amount):
                        print(f"✅ Found amount '{amount}' with currency symbol")
                        candidate_amounts.append((amount, 7))
                except (InvalidOperation, ValueError):
                    continue
    
    # Filter and select best candidate
    print("🎯 Filtering candidate amounts...")
    filtered_candidates = []
    
    for amount, confidence in candidate_amounts:
        if is_likely_false_positive(amount, text):
            print(f"❌ Filtered out false positive: {amount}")
            continue
        filtered_candidates.append((amount, confidence))
    
    if filtered_candidates:
        filtered_candidates.sort(key=lambda x: (-x[1], -x[0]))
        best_amount, best_confidence = filtered_candidates[0]
        print(f"🏆 Selected best amount: {best_amount} (confidence: {best_confidence})")
        return best_amount
    
    print("❌ No valid amount found after filtering")
    return None


def parse_text_amount(text):
    """
    Convert written amounts like 'One Hundred Fifty' to numeric 150
    Handles common Indian English number formats
    """
    if not text:
        return None
    
    text_lower = text.lower().strip()
    
    # Common number words mapping
    number_words = {
        'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
        'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
        'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14, 'fifteen': 15,
        'sixteen': 16, 'seventeen': 17, 'eighteen': 18, 'nineteen': 19,
        'twenty': 20, 'thirty': 30, 'forty': 40, 'fifty': 50, 'sixty': 60,
        'seventy': 70, 'eighty': 80, 'ninety': 90,
        'hundred': 100, 'thousand': 1000, 'lakh': 100000, 'crore': 10000000
    }
    
    # Common OCR misrecognitions
    ocr_corrections = {
        'fifty': 'fifty', 'fitty': 'fifty', 'fifthy': 'fifty', 'fifthy': 'fifty',
        'hundred': 'hundred', 'hundered': 'hundred', 'hundread': 'hundred',
        'thousand': 'thousand', 'thusand': 'thousand', 'thousond': 'thousand',
        'twenty': 'twenty', 'twentry': 'twenty', 'twanty': 'twenty',
        'thirty': 'thirty', 'thrity': 'thirty', 'thirity': 'thirty',
        'forty': 'forty', 'fourty': 'forty', 'founty': 'forty',
        'sixty': 'sixty', 'siksty': 'sixty', 'sixti': 'sixty',
        'seventy': 'seventy', 'seventi': 'seventy', 'seventee': 'seventy',
        'eighty': 'eighty', 'eighity': 'eighty', 'eighti': 'eighty',
        'ninety': 'ninety', 'ninty': 'ninety', 'nintety': 'ninety'
    }
    
    # Check for common Indian amount patterns
    patterns = [
        r'rs\.?\s*(.+?)\s*only',  # Rs. One Hundred Fifty only
        r'rupees?\s*(.+?)\s*only',  # Rupees One Hundred Fifty only
        r'rs\.?\s*(.+)',  # Rs. One Hundred Fifty
        r'rupees?\s*(.+)',  # Rupees One Hundred Fifty
        r'inr\s*(.+)',  # INR One Hundred Fifty
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            amount_text = match.group(1).strip()
            print(f"🔤 Found text amount: '{amount_text}'")
            
            # Correct common OCR errors
            for wrong, correct in ocr_corrections.items():
                amount_text = re.sub(r'\b' + wrong + r'\b', correct, amount_text)
            
            # Convert to number
            return convert_words_to_number(amount_text, number_words)
    
    return None


def convert_words_to_number(text, number_words):
    """
    Convert written numbers to numeric values
    """
    words = text.lower().split()
    total = 0
    current = 0
    
    for word in words:
        if word in number_words:
            value = number_words[word]
            
            if value >= 100:
                if current == 0:
                    current = 1
                total += current * value
                current = 0
            else:
                current += value
        else:
            # Skip non-number words
            continue
    
    total += current
    
    # Only return if we found a reasonable amount
    if total > 0 and total <= 1000000:
        print(f"🔢 Converted '{text}' to {total}")
        return Decimal(total)
    
    return None


def is_reasonable_amount(amount):
    """Check if the amount is reasonable for a receipt"""
    if amount <= 0:
        return False
    
    if amount < 1:  # Less than 1 rupee - unlikely
        return False
    if amount > 50000:  # More than 50,000 - possible but rare
        return False
    
    return True


def is_likely_false_positive(amount, text):
    """Filter out common false positives"""
    text_lower = text.lower()
    
    # Skip amounts that look like dates
    if 1 <= amount <= 31:
        date_patterns = [
            rf'{int(amount)}/\d{{1,2}}/\d{{4}}',
            rf'\d{{1,2}}/{int(amount)}/\d{{4}}',
        ]
        for pattern in date_patterns:
            if re.search(pattern, text):
                return True
    
    # Skip bill numbers
    if amount == int(amount):
        bill_keywords = ['bill no', 'bill#', 'order no', 'order#', 'invoice no', 'invoice#']
        for keyword in bill_keywords:
            if keyword in text_lower:
                lines = text_lower.split('\n')
                for line in lines:
                    if keyword in line and str(int(amount)) in line:
                        return True
    
    # Skip quantities
    if amount == int(amount) and amount <= 10:
        item_patterns = [r'\b\d+\s*x\s*\b', r'\bqty\s*:\s*\d+\b']
        for pattern in item_patterns:
            if re.search(pattern, text_lower):
                return True
    
    return False
def parse_date_from_text(text):
    """
    Try to find a date-like substring and parse with dateutil.
    """
    if not text:
        return None
    # simple regex to find date-like tokens (DD/MM/YYYY, YYYY-MM-DD, etc.)
    date_patterns = [
        r'(\d{1,2}[\/\-\.\s]\d{1,2}[\/\-\.\s]\d{2,4})',
        r'(\d{4}[\/\-\.\s]\d{1,2}[\/\-\.\s]\d{1,2})',
        r'([A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})',  # e.g., March 5, 2025
    ]
    for pat in date_patterns:
        m = re.search(pat, text)
        if m:
            s = m.group(1)
            try:
                dt = dateparser.parse(s, dayfirst=True).date()
                return dt
            except Exception:
                continue
    return None

def parse_vendor_from_text(text):
    """
    Heuristic: vendor is often the first non-empty line with letters.
    Returns a string, never None.
    """
    if not text:
        return 'Unknown Vendor'  # Return default instead of None
    
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    
    # choose top few lines that look like text (not totals)
    for i, line in enumerate(lines[:5]):
        # skip lines that contain words like 'total', 'gst', 'invoice'
        if re.search(r'(total|gst|invoice|tax|balanc|amount|date|bill|no|payment)', line, re.I):
            continue
        # if line contains letters and not just numbers, assume vendor
        if re.search(r'[A-Za-z]', line) and len(line) > 3:
            # return first reasonable line
            return line[:128]
    
    return 'Unknown Vendor'  # Return default instead of None

@login_required
def receipt_capture(request):
    """Serve the camera capture page"""
    return render(request, 'expenses/receipt_capture.html')

@login_required
def capture_image(request):
    """Capture image from webcam and save as receipt"""
    if request.method == 'POST':
        try:
            # Get base64 image data from frontend
            image_data = request.POST.get('image')
            if not image_data:
                return JsonResponse({'success': False, 'error': 'No image data'})
            
            # Remove data URL prefix
            if ',' in image_data:
                image_data = image_data.split(',')[1]
            
            # Decode base64 image
            image_bytes = base64.b64decode(image_data)
            
            # Create a temporary file
            temp_path = 'media/receipts/capture_temp.jpg'
            os.makedirs(os.path.dirname(temp_path), exist_ok=True)
            
            with open(temp_path, 'wb') as f:
                f.write(image_bytes)
            
            # Create Receipt object with default values
            receipt = Receipt.objects.create(
                owner=request.user,
                image='receipts/capture_temp.jpg',
                parsed_vendor='Unknown Vendor'  # Add default vendor
            )
            
            # Process the image (same OCR logic as upload)
            try:
                img = Image.open(temp_path)
                img = ImageOps.grayscale(img)
                img = ImageOps.autocontrast(img)
                
                ocr_result = pytesseract.image_to_string(img, lang='eng')
                receipt.ocr_text = ocr_result
                
                # Parse the text
                parsed_amount = parse_amount_from_text(ocr_result)
                parsed_date = parse_date_from_text(ocr_result)
                parsed_vendor = parse_vendor_from_text(ocr_result)
                
                # Update with parsed data, providing defaults if None
                receipt.parsed_amount = parsed_amount
                receipt.parsed_date = parsed_date
                receipt.parsed_vendor = parsed_vendor or 'Unknown Vendor'  # Ensure not empty
                receipt.save()
                
                # Create expense if amount found
                if parsed_amount:
                    expense = Expense.objects.create(
                        owner=request.user,
                        amount=parsed_amount,
                        date=parsed_date or timezone.now().date(),
                        vendor=parsed_vendor or 'Unknown Vendor',
                        description=f"Imported from camera receipt {receipt.pk}",
                        category='Other'
                    )
                    return JsonResponse({
                        'success': True, 
                        'expense_created': True,
                        'amount': float(parsed_amount),
                        'expense_id': expense.id
                    })
                else:
                    return JsonResponse({
                        'success': True,
                        'expense_created': False,
                        'message': 'Receipt captured but amount not found'
                    })
                    
            except Exception as e:
                return JsonResponse({'success': False, 'error': str(e)})
                
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})

# Initialize Stanza NLP pipeline
try:
    nlp = stanza.Pipeline('en', processors='tokenize,lemma,pos,ner')
    STANZA_AVAILABLE = True
    print("✅ Stanza NLP pipeline loaded successfully")
except Exception as e:
    nlp = None
    STANZA_AVAILABLE = False
    print(f"❌ Stanza NLP pipeline failed to load: {e}")

@csrf_exempt
@require_POST
@login_required
def voice_input(request):
    """
    Process voice input with ML categorization
    """
    try:
        data = json.loads(request.body)
        speech_text = data.get('speech_text', '').strip()
        
        if not speech_text:
            return JsonResponse({'success': False, 'error': 'No speech text provided'})
        
        print(f"🎤 Processing speech: {speech_text}")
        
        # Parse the speech text
        parsed_data = parse_speech_with_nlp(speech_text)
        
        # Use ML to predict category
        ml_category = 'Other'
        ml_confidence = 0
        if classifier.is_loaded():
            result = classifier.predict(speech_text)
            ml_confidence = result['confidence']
            if ml_confidence > 0.3:  # Only use if confidence is decent
                ml_category = result['category']
                print(f"🎯 ML predicted: {ml_category} (confidence: {ml_confidence:.2f})")
        
        # Override category with ML prediction if confident enough
        if ml_confidence > 0.3:
            parsed_data['category'] = ml_category
        
        if parsed_data['amount']:
            # Create expense directly
            expense = Expense.objects.create(
                owner=request.user,
                amount=parsed_data['amount'],
                date=parsed_data['date'] or timezone.now().date(),
                vendor=parsed_data['vendor'] or 'Voice Input',
                description=speech_text,
                category=parsed_data['category']
            )
            
            return JsonResponse({
                'success': True,
                'expense_created': True,
                'amount': float(parsed_data['amount']),
                'vendor': parsed_data['vendor'] or 'Voice Input',
                'category': parsed_data['category'],
                'ml_category': ml_category,
                'ml_confidence': ml_confidence,
                'message': f'Expense of ₹{parsed_data["amount"]} created in {parsed_data["category"]}'
            })
        else:
            # Return parsed data for form filling
            return JsonResponse({
                'success': True,
                'expense_created': False,
                'parsed_data': parsed_data,
                'ml_suggestion': {'category': ml_category, 'confidence': ml_confidence},
                'message': f'Fill the form: {speech_text}'
            })
            
    except Exception as e:
        print(f"Error processing voice input: {e}")
        return JsonResponse({'success': False, 'error': str(e)})

def parse_speech_with_nlp(text):
    """
    Use NLP to parse natural language expense descriptions
    """
    # Default values
    result = {
        'amount': None,
        'vendor': '',
        'category': 'Other',
        'date': None,
        'description': text
    }
    
    if not STANZA_AVAILABLE:
        # Fallback to regex parsing if Stanza is not available
        return parse_speech_with_regex(text)
    
    try:
        # Process text with Stanza
        doc = nlp(text)
        
        amount = extract_amount(doc, text)
        vendor = extract_vendor(doc, text)
        category = extract_category(doc, text)
        
        result['amount'] = amount
        result['vendor'] = vendor
        result['category'] = category
        
    except Exception as e:
        print(f"NLP parsing failed, using regex fallback: {e}")
        return parse_speech_with_regex(text)
    
    return result

def parse_speech_with_regex(text):
    """
    Fallback regex-based parsing for expense information
    """
    text_lower = text.lower()
    result = {
        'amount': None,
        'vendor': '',
        'category': 'Other',
        'date': None,
        'description': text
    }
    
    # Extract amount - look for numbers with currency context
    amount_patterns = [
        r'(\d+(?:\.\d{1,2})?)\s*(?:rs|rupees|₹|inr)',
        r'(?:rs|rupees|₹|inr)\s*(\d+(?:\.\d{1,2})?)',
        r'spent\s*(\d+(?:\.\d{1,2})?)',
        r'paid\s*(\d+(?:\.\d{1,2})?)',
        r'(\d+(?:\.\d{1,2})?)\s*(?:on|for)',
    ]
    
    for pattern in amount_patterns:
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            try:
                amount = Decimal(match.group(1))
                if is_reasonable_amount(amount):
                    result['amount'] = amount
                    break
            except (InvalidOperation, ValueError):
                continue
    
    # Extract vendor - look for words after prepositions
    vendor_patterns = [
        r'on\s+(\w+(?:\s+\w+){0,2})',
        r'for\s+(\w+(?:\s+\w+){0,2})',
        r'at\s+(\w+(?:\s+\w+){0,2})',
        r'from\s+(\w+(?:\s+\w+){0,2})',
    ]
    
    for pattern in vendor_patterns:
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            vendor = match.group(1).strip().title()
            if len(vendor) > 2:  # Avoid very short vendors
                result['vendor'] = vendor
                break
    
    # Extract category based on keywords
    category_keywords = {
        'Food': ['food', 'restaurant', 'lunch', 'dinner', 'breakfast', 'groceries', 'vegetables', 'milk', 'bread'],
        'Transport': ['transport', 'taxi', 'bus', 'train', 'fuel', 'petrol', 'diesel', 'auto', 'uber', 'ola'],
        'Shopping': ['shopping', 'mall', 'market', 'clothes', 'electronics', 'online'],
        'Bills': ['bill', 'electricity', 'water', 'internet', 'mobile', 'rent'],
        'Entertainment': ['movie', 'cinema', 'game', 'party', 'entertainment'],
        'Healthcare': ['hospital', 'doctor', 'medicine', 'medical', 'pharmacy']
    }
    
    for category, keywords in category_keywords.items():
        if any(keyword in text_lower for keyword in keywords):
            result['category'] = category
            break
    
    return result

def extract_amount(doc, text):
    """
    Extract amount using NLP
    """
    # Look for numbers in the text
    amount_pattern = r'(\d+(?:\.\d{1,2})?)'
    matches = re.finditer(amount_pattern, text)
    
    for match in matches:
        try:
            amount = Decimal(match.group(1))
            if is_reasonable_amount(amount):
                return amount
        except (InvalidOperation, ValueError):
            continue
    
    return None

def extract_vendor(doc, text):
    """
    Extract vendor using NLP named entity recognition
    """
    text_lower = text.lower()
    
    # Look for organizations or proper nouns
    for sentence in doc.sentences:
        for word in sentence.words:
            if word.upos in ['PROPN', 'NOUN'] and word.text.lower() not in ['rs', 'rupees', 'spent', 'paid']:
                # Check if it's likely a vendor name
                if len(word.text) > 2 and not word.text.isdigit():
                    return word.text.title()
    
    return ''

def extract_category(doc, text):
    """
    Extract category using NLP
    """
    text_lower = text.lower()
    category_keywords = {
        'Food': ['food', 'restaurant', 'lunch', 'dinner', 'breakfast', 'groceries', 'eat', 'meal'],
        'Transport': ['taxi', 'bus', 'train', 'fuel', 'petrol', 'auto', 'uber', 'ola', 'travel'],
        'Shopping': ['shopping', 'mall', 'market', 'clothes', 'electronics', 'buy', 'purchase'],
        'Bills': ['bill', 'electricity', 'water', 'internet', 'mobile', 'rent'],
        'Entertainment': ['movie', 'cinema', 'game', 'party', 'entertainment', 'fun'],
        'Healthcare': ['hospital', 'doctor', 'medicine', 'medical', 'pharmacy', 'health']
    }
    
    for category, keywords in category_keywords.items():
        if any(keyword in text_lower for keyword in keywords):
            return category
    
    return 'Other'

@login_required
def voice_test(request):
    """Test page for voice input"""
    return render(request, 'expenses/voice_test.html')

class ExpenseCreateView(LoginRequiredMixin, CreateView):
    model = Expense
    form_class = ExpenseForm
    template_name = 'expenses/expense_form.html'
    success_url = reverse_lazy('expenses:expense_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add Expense'
        context['categories'] = Expense.CATEGORY_CHOICES
        context['ml_available'] = classifier.is_loaded()
        return context
    
    def get_initial(self):
        initial = super().get_initial()
        # Auto-predict category from description in GET params (if any)
        description = self.request.GET.get('description', '')
        if description and classifier.is_loaded():
            result = classifier.predict(description)
            if result['confidence'] > 0.3:
                initial['category'] = result['category']
                # Store in session for form display
                self.request.session['ml_suggestion'] = {
                    'category': result['category'],
                    'confidence': result['confidence']
                }
        return initial
    
    def form_valid(self, form):
        form.instance.owner = self.request.user
        # CRITICAL: Auto-assign category using ML if not already set
        if not form.instance.category and classifier.is_loaded():
            # Use description for prediction
            description = form.instance.description or form.instance.vendor or ''
            if description:
                result = classifier.predict(description)
                if result['confidence'] > 0.3:  # Only assign if confidence > 30%
                    form.instance.category = result['category']
                    messages.info(self.request, 
                        f"🤖 Auto-categorized as: {result['category']} "
                        f"(confidence: {result['confidence']:.1%})"
                    )
                else:
                    # If confidence is low, set to 'Other'
                    form.instance.category = 'Other'
                    messages.warning(self.request, 
                        "⚠️ Couldn't determine category confidently. Set to 'Other'."
                    )
        
        response = super().form_valid(form)
        # Clear the session suggestion
        if 'ml_suggestion' in self.request.session:
            del self.request.session['ml_suggestion']
        messages.success(self.request, 'Expense created successfully!')
        return response
        
        


# Also add ML to the expense_update view
@login_required
def expense_update(request, pk):
    expense = get_object_or_404(Expense, pk=pk, owner=request.user)
    if request.method == 'POST':
        form = ExpenseForm(request.POST, instance=expense)
        if form.is_valid():
            form.save()
            messages.success(request, 'Expense updated successfully!')
            return redirect('expenses:expense_list')
    else:
        form = ExpenseForm(instance=expense)
    
    context = {
        'form': form, 
        'title': 'Edit Expense',
        'categories': Expense.CATEGORY_CHOICES
    }
    return render(request, 'expenses/expense_form.html', context)



            
@csrf_exempt
@require_POST
def predict_category(request):
    """API endpoint for real-time category prediction"""
    try:
        data = json.loads(request.body)
        description = data.get('description', '')
        
        if not description:
            return JsonResponse({'error': 'No description provided'}, status=400)
        
        if not classifier.is_loaded():
            return JsonResponse({'error': 'Model not loaded'}, status=503)
        
        result = classifier.predict(description)
        
        return JsonResponse({
            'category': result['category'],
            'confidence': result['confidence'],
            'all_categories': classifier.get_categories() if hasattr(classifier, 'get_categories') else []
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
@login_required
def model_stats(request):
    """Show model performance statistics"""
    if not request.user.is_staff:
        messages.error(request, 'Access denied')
        return redirect('expenses:dashboard')
    
    stats = {
        'model_loaded': classifier.is_loaded(),
        'categories': classifier.get_categories(),
        'total_categories': len(classifier.get_categories()),
    }
    
    # Load confusion matrix if exists
    import os
    cm_path = os.path.join(os.path.dirname(__file__), '..', 'ml_model', 'models', 'confusion_matrix.png')
    if os.path.exists(cm_path):
        stats['confusion_matrix'] = '/static/models/confusion_matrix.png'
    
    return render(request, 'expenses/model_stats.html', stats)

@login_required
def analysis_dashboard(request):
    """Main analysis dashboard view"""
    analyzer = SpendingAnalyzer(request.user)
    
    context = {
        'insights': analyzer.generate_insights(),
        'trends': analyzer.calculate_trends(),
        'distribution': analyzer.get_category_distribution(),
        'yearly_comparison': analyzer.get_yearly_comparison(),
        'anomalies': analyzer.detect_anomalies(),
        'moving_avg': analyzer.calculate_moving_average(),
    }
    
    return render(request, 'expenses/analysis_dashboard.html', context)


@login_required
def analysis_data_api(request):
    """API endpoint for chart data"""
    analyzer = SpendingAnalyzer(request.user)
    
    # Get monthly data for charts
    monthly_data = analyzer.get_monthly_data(months=12)
    
    if monthly_data.empty:
        return JsonResponse({'error': 'No data available'}, status=404)
    
    # Format for charts
    chart_data = {
        'labels': [str(m) for m in monthly_data.index],
        'datasets': []
    }
    
    # Color palette for categories
    colors = [
        '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF',
        '#FF9F40', '#FF6384', '#C9CBCF', '#7BC225', '#00A1B2'
    ]
    
    for i, category in enumerate(monthly_data.columns):
        if category != 'Total':
            chart_data['datasets'].append({
                'label': category,
                'data': monthly_data[category].tolist(),
                'borderColor': colors[i % len(colors)],
                'backgroundColor': colors[i % len(colors)] + '20',  # Add transparency
                'fill': False,
                'tension': 0.1
            })
    
    # Add total as a separate dataset with thicker line
    if 'Total' in monthly_data.columns:
        chart_data['datasets'].append({
            'label': 'Total',
            'data': monthly_data['Total'].tolist(),
            'borderColor': '#000000',
            'backgroundColor': '#00000020',
            'borderWidth': 3,
            'fill': False,
            'tension': 0.1
        })
    
    return JsonResponse(chart_data)


@login_required
def category_pie_data_api(request):
    """API endpoint for category pie chart"""
    analyzer = SpendingAnalyzer(request.user)
    distribution = analyzer.get_category_distribution()
    
    pie_data = {
        'labels': [],
        'datasets': [{
            'data': [],
            'backgroundColor': [
                '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF',
                '#FF9F40', '#FF6384', '#C9CBCF', '#7BC225', '#00A1B2'
            ]
        }]
    }
    
    for category, data in distribution.items():
        pie_data['labels'].append(category)
        pie_data['datasets'][0]['data'].append(data['amount'])
    
    return JsonResponse(pie_data)


@login_required
def export_analysis_report(request):
    """Export analysis as PDF/CSV"""
    import csv
    from django.http import HttpResponse
    
    analyzer = SpendingAnalyzer(request.user)
    monthly_data = analyzer.get_monthly_data(months=12)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="spending_analysis_{datetime.now().strftime("%Y%m%d")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Month', 'Category', 'Amount'])
    
    for month in monthly_data.index:
        for category in monthly_data.columns:
            if category != 'Total':
                writer.writerow([str(month), category, monthly_data.loc[month, category]])
    
    return response

@login_required
def anomaly_dashboard(request):
    """Main anomaly detection dashboard"""
    detector = AnomalyDetector(request.user)
    
    # Run detection on recent expenses
    new_anomalies = detector.detect_anomalies(threshold=2.0)
    
    context = {
        'anomalies': detector.get_recent_anomalies(),
        'stats': detector.get_anomaly_stats(),
        'timeline': detector.get_anomaly_timeline(),
        'new_count': len(new_anomalies),
    }
    
    return render(request, 'expenses/anomaly_dashboard.html', context)

@login_required
def anomaly_detail(request, expense_id):
    """View details of an anomaly"""
    expense = get_object_or_404(Expense, id=expense_id, owner=request.user)
    detector = AnomalyDetector(request.user)
    
    # Get category stats for comparison
    stats = detector.calculate_category_stats()
    cat_stats = stats.get(expense.category, {})
    
    # Get similar expenses for comparison
    similar = Expense.objects.filter(
        owner=request.user,
        category=expense.category,
        date__gte=expense.date - timedelta(days=90),
        date__lte=expense.date + timedelta(days=90)
    ).exclude(id=expense.id).order_by('-date')[:10]
    
    context = {
        'expense': expense,
        'stats': cat_stats,
        'similar': similar,
        'zscore': expense.anomaly_score,
    }
    
    return render(request, 'expenses/anomaly_detail.html', context)

@login_required
def mark_anomaly_reviewed(request, expense_id):
    """Mark an anomaly as reviewed"""
    expense = get_object_or_404(Expense, id=expense_id, owner=request.user)
    
    if request.method == 'POST':
        expense.mark_as_reviewed()
        messages.success(request, 'Anomaly marked as reviewed')
    
    return redirect('expenses:anomaly_dashboard')

@login_required
def dismiss_anomaly(request, expense_id):
    """Dismiss an anomaly (mark as not anomaly)"""
    expense = get_object_or_404(Expense, id=expense_id, owner=request.user)
    
    if request.method == 'POST':
        expense.is_anomaly = False
        expense.anomaly_score = None
        expense.anomaly_reason = ''
        expense.reviewed = True
        expense.save()
        messages.success(request, 'Anomaly dismissed')
    
    return redirect('expenses:anomaly_dashboard')

@login_required
def anomaly_data_api(request):
    """API endpoint for anomaly charts"""
    detector = AnomalyDetector(request.user)
    stats = detector.get_anomaly_stats()
    
    # Get anomaly timeline data
    timeline = detector.get_anomaly_timeline()
    
    # Category breakdown data
    categories_data = {
        'labels': [],
        'datasets': [{
            'data': [],
            'backgroundColor': '#FF6384'
        }]
    }
    
    for cat in stats['by_category']:
        categories_data['labels'].append(cat['category'])
        categories_data['datasets'][0]['data'].append(cat['count'])
    
    return JsonResponse({
        'stats': stats,
        'timeline': {
            'labels': [t['month'].strftime('%b %Y') for t in timeline],
            'data': [t['count'] for t in timeline]
        },
        'categories': categories_data
    })


def dashboard(request):
    total = 0
    recent = []
    stats = {'unreviewed': 0}
    
    if request.user.is_authenticated:
        recent = Expense.objects.filter(owner=request.user).order_by('-date')[:5] 
        total = Expense.objects.filter(owner=request.user).aggregate(total=Sum('amount'))['total'] or 0
        
        # Get anomaly stats
        detector = AnomalyDetector(request.user)
        anomaly_stats = detector.get_anomaly_stats()
        stats['unreviewed'] = anomaly_stats['unreviewed']
    
    return render(request, 'expenses/dashboard.html', {
        'recent': recent, 
        'total': total,
        'stats': stats
    })

@login_required
def prediction_dashboard(request):
    """Show budget predictions and suggestions"""
    from .predictor import ExpensePredictor
    predictor = ExpensePredictor(request.user)
    
    # Train model and get predictions
    predictions = predictor.predict_future(periods=3)
    insights = predictor.generate_insights(predictions) if predictions else None
    budget_suggestion = predictor.get_budget_suggestion(predictions) if predictions else None
    
    # Get historical data for chart
    historical_data = []
    aggregates = MonthlyAggregate.objects.filter(
        user=request.user
    ).order_by('month')[:12]
    
    for agg in aggregates:
        historical_data.append({
            'month': agg.month.strftime('%b %Y'),
            'total': float(agg.total_expense)
        })
    
    # Combine historical and predicted for chart
    chart_data = historical_data.copy()
    if predictions:
        for pred in predictions[:3]:
            chart_data.append({
                'month': pred['date'].strftime('%b %Y'),
                'total': pred['predicted'],
                'predicted': True
            })
    
    context = {
        'predictions': predictions,
        'insights': insights,
        'budget_suggestion': budget_suggestion,
        'historical_data': historical_data,
        'chart_data': chart_data,
        'has_data': MonthlyAggregate.objects.filter(user=request.user).exists()
    }
    
    return render(request, 'expenses/prediction_dashboard.html', context)

@login_required
def prediction_api(request):
    """API endpoint for prediction data"""
    predictor = ExpensePredictor(request.user)
    predictions = predictor.predict_future(periods=3)
    
    if predictions:
        return JsonResponse({
            'success': True,
            'predictions': predictions,
            'budget_suggestion': predictor.get_budget_suggestion(predictions)
        })
    else:
        return JsonResponse({'success': False, 'error': 'Insufficient data'})

@login_required
def refresh_monthly_data(request):
    """Manually refresh monthly aggregated data"""
    from django.db.models import Sum
    from datetime import datetime
    
    # Aggregate actual expenses by month
    expenses = Expense.objects.filter(owner=request.user)
    
    months = {}
    for expense in expenses:
        month_key = expense.date.replace(day=1)
        if month_key not in months:
            months[month_key] = {
                'total': 0,
                'categories': {}
            }
        months[month_key]['total'] += float(expense.amount)
        cat = expense.category
        months[month_key]['categories'][cat] = months[month_key]['categories'].get(cat, 0) + float(expense.amount)
    
    # Save or update monthly aggregates
    for month, data in months.items():
        MonthlyAggregate.objects.update_or_create(
            user=request.user,
            month=month,
            defaults={
                'total_expense': data['total'],
                'categories': data['categories']
            }
        )
    
    messages.success(request, 'Monthly data refreshed successfully!')
    return redirect('expenses:prediction_dashboard')

from .forms import IncomeForm, DebtForm, AssetForm, EmergencyFundForm, FinancialGoalForm
from .models import Income, Debt, Asset, EmergencyFund, FinancialGoal
from .financial_health import FinancialHealthAnalyzer

@login_required
def financial_health_dashboard(request):
    """Main financial health dashboard"""
    analyzer = FinancialHealthAnalyzer(request.user)
    summary = analyzer.get_financial_summary()
    insights = analyzer.generate_health_insights()
    
    # Get recent entries
    recent_incomes = Income.objects.filter(user=request.user).order_by('-date')[:5]
    recent_debts = Debt.objects.filter(user=request.user, is_paid=False).order_by('-due_date')[:5]
    recent_assets = Asset.objects.filter(user=request.user).order_by('-created_at')[:5]
    goals = FinancialGoal.objects.filter(user=request.user, is_completed=False).order_by('deadline')
    
    context = {
        'summary': summary,
        'insights': insights,
        'recent_incomes': recent_incomes,
        'recent_debts': recent_debts,
        'recent_assets': recent_assets,
        'goals': goals,
    }
    
    return render(request, 'expenses/financial_health.html', context)

@login_required
def add_income(request):
    """Add income record"""
    if request.method == 'POST':
        form = IncomeForm(request.POST)
        if form.is_valid():
            income = form.save(commit=False)
            income.user = request.user
            income.save()
            messages.success(request, f'Income of ₹{income.amount} added successfully!')
            return redirect('expenses:financial_health')
    else:
        form = IncomeForm()
    
    return render(request, 'expenses/add_income.html', {'form': form, 'title': 'Add Income'})

@login_required
def add_debt(request):
    """Add debt record"""
    if request.method == 'POST':
        form = DebtForm(request.POST)
        if form.is_valid():
            debt = form.save(commit=False)
            debt.user = request.user
            debt.save()
            messages.success(request, f'Debt "{debt.name}" of ₹{debt.amount} added successfully!')
            return redirect('expenses:financial_health')
    else:
        form = DebtForm()
    
    return render(request, 'expenses/add_debt.html', {'form': form, 'title': 'Add Debt'})

@login_required
def add_asset(request):
    """Add asset record"""
    if request.method == 'POST':
        form = AssetForm(request.POST)
        if form.is_valid():
            asset = form.save(commit=False)
            asset.user = request.user
            asset.save()
            messages.success(request, f'Asset "{asset.name}" of ₹{asset.value} added successfully!')
            return redirect('expenses:financial_health')
    else:
        form = AssetForm()
    
    return render(request, 'expenses/add_asset.html', {'form': form, 'title': 'Add Asset'})

@login_required
def setup_emergency_fund(request):
    """Setup or update emergency fund"""
    try:
        emergency_fund = EmergencyFund.objects.get(user=request.user)
    except EmergencyFund.DoesNotExist:
        emergency_fund = None
    
    if request.method == 'POST':
        form = EmergencyFundForm(request.POST, instance=emergency_fund)
        if form.is_valid():
            ef = form.save(commit=False)
            ef.user = request.user
            ef.save()
            messages.success(request, 'Emergency fund updated successfully!')
            return redirect('expenses:financial_health')
    else:
        form = EmergencyFundForm(instance=emergency_fund)
    
    return render(request, 'expenses/setup_emergency.html', {'form': form, 'title': 'Emergency Fund'})

@login_required
def add_financial_goal(request):
    """Add financial goal"""
    if request.method == 'POST':
        form = FinancialGoalForm(request.POST)
        if form.is_valid():
            goal = form.save(commit=False)
            goal.user = request.user
            goal.save()
            messages.success(request, f'Goal "{goal.name}" added successfully!')
            return redirect('expenses:financial_health')
    else:
        form = FinancialGoalForm()
    
    return render(request, 'expenses/add_financial_goal.html', {'form': form, 'title': 'Add Financial Goal'})

@login_required
def update_emergency_fund(request):
    """Add contribution to emergency fund"""
    try:
        ef = EmergencyFund.objects.get(user=request.user)
    except EmergencyFund.DoesNotExist:
        messages.error(request, 'Please setup emergency fund first')
        return redirect('expenses:setup_emergency')
    
    if request.method == 'POST':
        amount = Decimal(request.POST.get('amount', 0))
        if amount > 0:
            ef.current_amount += amount
            ef.save()
            messages.success(request, f'Added ₹{amount} to emergency fund!')
        else:
            messages.error(request, 'Amount must be greater than 0')
        return redirect('expenses:financial_health')
    
    return render(request, 'expenses/update_emergency.html', {'emergency_fund': ef})

# Add this decorator to ensure all views require login
from django.contrib.auth.decorators import login_required

# Make sure these views filter by user:

@login_required
def dashboard(request):
    total = 0
    recent = []
    anomaly_stats = {'unreviewed': 0}
    
    if request.user.is_authenticated:
        # Filter by current user
        recent = Expense.objects.filter(owner=request.user).order_by('-date')[:5] 
        total = Expense.objects.filter(owner=request.user).aggregate(total=Sum('amount'))['total'] or 0
        
        # Get anomaly stats for current user
        try:
            detector = AnomalyDetector(request.user)
            stats = detector.get_anomaly_stats()
            anomaly_stats['unreviewed'] = stats.get('unreviewed', 0)
        except Exception as e:
            print(f"Error getting anomaly stats: {e}")
    
    return render(request, 'expenses/dashboard.html', {
        'recent': recent, 
        'total': total,
        'stats': anomaly_stats
    })

# Update ExpenseListView
class ExpenseListView(LoginRequiredMixin, ListView):
    model = Expense
    template_name = 'expenses/expense_list.html'
    context_object_name = 'expenses'
    paginate_by = 15

    def get_queryset(self):
        # Filter by logged-in user
        return Expense.objects.filter(owner=self.request.user).order_by('-date')

# Update ExpenseCreateView
class ExpenseCreateView(LoginRequiredMixin, CreateView):
    model = Expense
    form_class = ExpenseForm
    template_name = 'expenses/expense_form.html'
    success_url = reverse_lazy('expenses:expense_list')
    
    def form_valid(self, form):
        form.instance.owner = self.request.user  # Set owner to current user
        if not form.instance.category and classifier.is_loaded():
            description = form.instance.description or form.instance.vendor or ''
            if description:
                result = classifier.predict(description)
                if result['confidence'] > 0.3:
                    form.instance.category = result['category']
        return super().form_valid(form)