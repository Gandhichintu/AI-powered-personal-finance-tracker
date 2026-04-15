class SpeechRecognitionHandler {
    constructor() {
        this.recognition = null;
        this.isListening = false;
        this.initSpeechRecognition();
    }

    initSpeechRecognition() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        
        if (!SpeechRecognition) {
            console.error('Speech Recognition not supported in this browser');
            return;
        }

        this.recognition = new SpeechRecognition();
        this.recognition.continuous = false;
        this.recognition.interimResults = false;
        this.recognition.lang = 'en-IN'; // Indian English

        this.recognition.onstart = () => {
            this.isListening = true;
            this.updateUI('listening');
        };

        this.recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            this.handleSpeechResult(transcript);
        };

        this.recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            this.updateUI('error', event.error);
            this.isListening = false;
        };

        this.recognition.onend = () => {
            this.isListening = false;
            this.updateUI('ready');
        };
    }

    startListening() {
        if (this.recognition && !this.isListening) {
            try {
                this.recognition.start();
            } catch (error) {
                console.error('Error starting speech recognition:', error);
            }
        }
    }

    stopListening() {
        if (this.recognition && this.isListening) {
            this.recognition.stop();
        }
    }

    updateUI(state, error = null) {
        const micBtn = document.getElementById('mic-btn');
        const statusDiv = document.getElementById('speech-status');
        
        if (!micBtn) return;

        switch(state) {
            case 'listening':
                micBtn.innerHTML = '🎤 Listening...';
                micBtn.classList.add('bg-red-500');
                micBtn.classList.remove('bg-blue-500', 'bg-green-500', 'bg-purple-600');
                if (statusDiv) {
                    statusDiv.innerHTML = '<div class="text-blue-600 mt-2 text-sm">🎤 Listening... Speak now</div>';
                }
                break;
            case 'processing':
                micBtn.innerHTML = '⏳ Processing...';
                micBtn.classList.add('bg-yellow-500');
                micBtn.classList.remove('bg-blue-500', 'bg-red-500', 'bg-purple-600');
                if (statusDiv) {
                    statusDiv.innerHTML = '<div class="text-yellow-600 mt-2 text-sm">⏳ Processing your speech...</div>';
                }
                break;
            case 'success':
                micBtn.innerHTML = '🎤 Speak Expense';
                micBtn.classList.add('bg-green-500');
                micBtn.classList.remove('bg-blue-500', 'bg-red-500', 'bg-purple-600');
                setTimeout(() => {
                    if (micBtn) {
                        micBtn.classList.remove('bg-green-500');
                        micBtn.classList.add('bg-purple-600');
                    }
                }, 2000);
                break;
            case 'error':
                micBtn.innerHTML = '🎤 Speak Expense';
                micBtn.classList.remove('bg-blue-500', 'bg-red-500', 'bg-yellow-500', 'bg-purple-600');
                micBtn.classList.add('bg-purple-600');
                if (statusDiv) {
                    statusDiv.innerHTML = `<div class="text-red-600 mt-2 text-sm">❌ Error: ${error || 'Speech recognition failed'}</div>`;
                }
                setTimeout(() => {
                    if (statusDiv) {
                        statusDiv.innerHTML = '<div class="text-gray-600 mt-2 text-sm">Click the mic and speak your expense</div>';
                    }
                }, 3000);
                break;
            default:
                micBtn.innerHTML = '🎤 Speak Expense';
                micBtn.classList.remove('bg-red-500', 'bg-yellow-500', 'bg-green-500');
                micBtn.classList.add('bg-purple-600');
                if (statusDiv) {
                    statusDiv.innerHTML = '<div class="text-gray-600 mt-2 text-sm">Click the mic and speak your expense</div>';
                }
        }
    }

    async handleSpeechResult(transcript) {
        this.updateUI('processing');
        
        console.log('Speech transcript:', transcript);

        try {
            const response = await fetch('/expenses/voice-input/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken(),
                },
                body: JSON.stringify({ speech_text: transcript })
            });

            const data = await response.json();

            if (data.success) {
                this.updateUI('success');
                this.showSuccessMessage(data);
                
                // Redirect to expense list if expense was created
                if (data.expense_created) {
                    setTimeout(() => {
                        window.location.href = '/expenses/';
                    }, 2000);
                }
            } else {
                this.updateUI('error', data.error);
            }

        } catch (error) {
            console.error('Error sending speech to server:', error);
            this.updateUI('error', 'Network error');
        }
    }

    showSuccessMessage(data) {
        const statusDiv = document.getElementById('speech-status');
        if (statusDiv) {
            if (data.expense_created) {
                statusDiv.innerHTML = `
                    <div class="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mt-2">
                        ✅ Expense created: ₹${data.amount} for ${data.vendor}
                        <br><small>Redirecting to expenses...</small>
                    </div>
                `;
            } else {
                statusDiv.innerHTML = `
                    <div class="bg-yellow-100 border border-yellow-400 text-yellow-700 px-4 py-3 rounded mt-2">
                        📝 ${data.message}
                        ${data.ml_suggestion ? `<br><small>ML suggests: ${data.ml_suggestion.category} (${(data.ml_suggestion.confidence * 100).toFixed(0)}% confidence)</small>` : ''}
                    </div>
                `;
            }
        }
    }

    getCSRFToken() {
        const cookieValue = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='))
            ?.split('=')[1];
        return cookieValue;
    }
    // Add to speech.js, inside the SpeechRecognitionHandler class
updateMicButtonState(state) {
    const micNavButton = document.getElementById('mic-nav-btn');
    if (!micNavButton) return;
    
    const svg = micNavButton.querySelector('svg');
    const dot = micNavButton.querySelector('.animate-pulse');
    
    switch(state) {
        case 'listening':
            svg.classList.add('text-red-500');
            svg.classList.remove('text-gray-600', 'text-purple-600');
            if (dot) dot.classList.add('bg-red-500');
            break;
        case 'processing':
            svg.classList.add('text-yellow-500');
            svg.classList.remove('text-gray-600', 'text-purple-600');
            break;
        case 'success':
            svg.classList.add('text-green-500');
            svg.classList.remove('text-gray-600', 'text-purple-600');
            setTimeout(() => {
                svg.classList.remove('text-green-500');
                svg.classList.add('text-gray-600');
                if (dot) dot.classList.remove('bg-red-500');
            }, 2000);
            break;
        case 'error':
            svg.classList.add('text-red-500');
            svg.classList.remove('text-gray-600', 'text-purple-600');
            setTimeout(() => {
                svg.classList.remove('text-red-500');
                svg.classList.add('text-gray-600');
            }, 3000);
            break;
        default:
            svg.classList.remove('text-red-500', 'text-yellow-500', 'text-green-500');
            svg.classList.add('text-gray-600');
    }
}
}

// Check if user is authenticated and on appropriate page
function shouldShowSpeechButton() {
    // Don't show on login, register, or landing page
    const currentPath = window.location.pathname;
    const excludedPaths = ['/accounts/login/', '/accounts/register/', '/'];
    
    // Check if current path is excluded
    if (excludedPaths.includes(currentPath)) {
        return false;
    }
    
    // Check if user is authenticated (has auth token in cookies)
    const hasAuthToken = document.cookie.split('; ').some(row => row.startsWith('sessionid='));
    
    return hasAuthToken;
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Only initialize speech recognition on pages where it makes sense
    if (!shouldShowSpeechButton()) {
        return;
    }
    
    const speechHandler = new SpeechRecognitionHandler();
    
    // Add mic button to expense form page
    const expenseForm = document.querySelector('form');
    const isExpenseForm = window.location.pathname.includes('/expenses/add/') || 
                          window.location.pathname.includes('/expenses/') && document.querySelector('#id_description');
    
    if (expenseForm && isExpenseForm) {
        addMicButtonToForm(speechHandler);
    }
    
    // Add mic button to dashboard
    const isDashboard = window.location.pathname === '/dashboard/' || 
                        window.location.pathname === '/';
    
    if (isDashboard) {
        addMicButtonToDashboard(speechHandler);
    }
});

function addMicButtonToForm(speechHandler) {
    const form = document.querySelector('form');
    if (!form) return;
    
    const submitButton = form.querySelector('button[type="submit"]');
    if (!submitButton) return;
    
    // Check if mic button already exists
    if (document.getElementById('mic-btn')) return;
    
    const micButton = document.createElement('button');
    micButton.type = 'button';
    micButton.id = 'mic-btn';
    micButton.className = 'ml-2 bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg flex items-center transition';
    micButton.innerHTML = '🎤 Speak Expense';
    
    micButton.addEventListener('click', function(e) {
        e.preventDefault();
        speechHandler.startListening();
    });
    
    // Insert after submit button
    submitButton.parentNode.insertBefore(micButton, submitButton.nextSibling);
    
    // Add status div
    let statusDiv = document.getElementById('speech-status');
    if (!statusDiv) {
        statusDiv = document.createElement('div');
        statusDiv.id = 'speech-status';
        statusDiv.className = 'mt-3';
        form.appendChild(statusDiv);
    }
}

function addMicButtonToDashboard(speechHandler) {
    const dashboardSection = document.querySelector('main .container');
    if (!dashboardSection) return;
    
    // Check if voice section already exists
    if (document.getElementById('voice-section')) return;
    
    const voiceSection = document.createElement('div');
    voiceSection.id = 'voice-section';
    voiceSection.className = 'bg-gradient-to-r from-purple-50 to-pink-50 p-6 rounded-xl shadow mb-6';
    voiceSection.innerHTML = `
        <div class="flex items-center justify-between flex-wrap">
            <div>
                <h3 class="text-lg font-semibold text-gray-800">🎤 Quick Voice Expense</h3>
                <p class="text-sm text-gray-600 mt-1">Speak your expense naturally:</p>
                <p class="text-xs text-gray-500 mt-1">
                    Examples: "Spent 500 on pizza" or "Paid 200 for uber ride"
                </p>
            </div>
            <button id="mic-btn" class="bg-purple-600 hover:bg-purple-700 text-white px-6 py-3 rounded-lg text-lg font-medium transition transform hover:scale-105">
                🎤 Speak Now
            </button>
        </div>
        <div id="speech-status" class="mt-3"></div>
    `;
    
    // Insert at the top of the dashboard
    const firstChild = dashboardSection.firstChild;
    dashboardSection.insertBefore(voiceSection, firstChild);
    
    const micButton = document.getElementById('mic-btn');
    if (micButton) {
        micButton.addEventListener('click', function() {
            speechHandler.startListening();
        });
    }
}