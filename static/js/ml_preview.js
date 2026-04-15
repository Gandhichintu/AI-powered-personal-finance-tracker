// Real-time ML category preview
document.addEventListener('DOMContentLoaded', function() {
    const descriptionInput = document.querySelector('#id_description');
    const categorySelect = document.querySelector('#id_category');
    const mlPreview = document.querySelector('#id_ml_preview');
    
    if (descriptionInput && categorySelect && mlPreview) {
        descriptionInput.addEventListener('input', debounce(function() {
            const description = this.value;
            if (description.length > 3) {
                fetch('/api/predict-category/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: JSON.stringify({description: description})
                })
                .then(response => response.json())
                .then(data => {
                    if (data.category) {
                        mlPreview.value = `${data.category} (${(data.confidence*100).toFixed(1)}%)`;
                        
                        // Optional: Auto-select if confidence is high
                        if (data.confidence > 0.7) {
                            categorySelect.value = data.category;
                        }
                    }
                });
            }
        }, 500));
    }
});

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func.apply(this, args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}