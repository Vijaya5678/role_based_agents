(function() {
    'use strict';

    // Application State
    let appState = {
        sessionId: null,
        timerInterval: null,
        timeRemaining: 0,
    };

    // DOM Elements
    const pages = {
        home: document.getElementById('home-page'),
        config: document.getElementById('config-page'),
        interview: document.getElementById('interview-page'),
        report: document.getElementById('report-page'),
    };
    const loadingOverlay = document.getElementById('loading-overlay');
    const toastContainer = document.getElementById('toast-container');

    // Config Page Elements
    const configForm = document.getElementById('interview-config-form');
    const categorySelect = document.getElementById('category');
    const roleSelect = document.getElementById('role');
    const difficultySelect = document.getElementById('difficulty');
    const difficultyDetails = document.getElementById('difficulty-details');
    const startInterviewBtn = document.getElementById('start-interview-btn');
    const backHomeBtn = document.getElementById('back-home-btn');

    // Interview Page Elements
    const progressInfo = document.getElementById('progress-info');
    const timerDisplay = document.getElementById('timer');
    const chatMessages = document.getElementById('chat-messages');
    const currentQuestionBox = document.getElementById('current-question');
    const answerInput = document.getElementById('answer-input');
    const submitBtn = document.getElementById('submit-btn');
    const hintBtn = document.getElementById('hint-btn');
    const skipBtn = document.getElementById('skip-btn');
    const endBtn = document.getElementById('end-btn');

    // Report Page Elements
    const reportSummary = document.getElementById('report-summary');
    const questionAnalysis = document.getElementById('question-analysis');
    const overallEvaluation = document.getElementById('overall-evaluation');
    const newInterviewBtn = document.getElementById('new-interview-btn');
    const backHomeReportBtn = document.getElementById('back-home-report-btn');

    // --- UTILITY FUNCTIONS ---

    function showPage(pageId) {
        Object.values(pages).forEach(page => page.classList.remove('active'));
        pages[pageId].classList.add('active');
    }

    function showLoading(isLoading) {
        loadingOverlay.style.display = isLoading ? 'flex' : 'none';
    }

    function showToast(message, type = 'success') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        toastContainer.appendChild(toast);
        setTimeout(() => toast.remove(), 4000);
    }

    async function apiClient(endpoint, method = 'GET', body = null) {
        console.log(`API Call: ${method} ${API_CONFIG.BASE_URL}${endpoint}`);
        if (body) {
            console.log('Request body:', body);
        }
        
        showLoading(true);
        try {
            const options = {
                method,
                headers: { 
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
            };
            if (body) {
                options.body = JSON.stringify(body);
            }
            
            const response = await fetch(`${API_CONFIG.BASE_URL}${endpoint}`, options);
            
            console.log(`Response status: ${response.status}`);
            
            if (!response.ok) {
                let errorMessage = `HTTP ${response.status}`;
                try {
                    const errorData = await response.json();
                    errorMessage = errorData.detail || errorData.message || errorMessage;
                } catch (e) {
                    errorMessage = `HTTP ${response.status}: ${response.statusText}`;
                }
                throw new Error(errorMessage);
            }
            
            const data = await response.json();
            console.log('Response data:', data);
            return data;
            
        } catch (error) {
            console.error('API Error:', error);
            showToast(`API Error: ${error.message}`, 'error');
            return null;
        } finally {
            showLoading(false);
        }
    }

    // --- PAGE & UI LOGIC ---

    function populateRoles() {
        const category = categorySelect.value;
        roleSelect.innerHTML = '<option value="">Select Role</option>';
        if (category && APP_CONFIG.CATEGORIES[category]) {
            APP_CONFIG.CATEGORIES[category].forEach(role => {
                const option = document.createElement('option');
                option.value = role;
                option.textContent = formatRoleName(role);
                roleSelect.appendChild(option);
            });
        }
    }

    function updateDifficultyDetails() {
        const difficulty = difficultySelect.value;
        if (difficulty && APP_CONFIG.DIFFICULTY_INFO[difficulty]) {
            const info = APP_CONFIG.DIFFICULTY_INFO[difficulty];
            difficultyDetails.innerHTML = `
                <p><strong>Questions:</strong> ${info.questions}</p>
                <p><strong>Time:</strong> ${info.time} minutes</p>
                <p><strong>Focus:</strong> ${info.description}</p>
            `;
            difficultyDetails.style.display = 'block';
        } else {
            difficultyDetails.style.display = 'none';
        }
    }

    function startTimer(durationMinutes) {
        clearInterval(appState.timerInterval);
        appState.timeRemaining = durationMinutes * 60;
        
        appState.timerInterval = setInterval(() => {
            appState.timeRemaining--;
            const minutes = Math.floor(appState.timeRemaining / 60);
            const seconds = appState.timeRemaining % 60;
            timerDisplay.textContent = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
            
            timerDisplay.classList.remove('warning', 'danger');
            if (appState.timeRemaining < 60) {
                timerDisplay.classList.add('danger');
            } else if (appState.timeRemaining < 300) {
                timerDisplay.classList.add('warning');
            }

            if (appState.timeRemaining <= 0) {
                clearInterval(appState.timerInterval);
                showToast('Time is up! The interview has ended.', 'warning');
                endInterview('end');
            }
        }, 1000);
    }
    
    function displayQuestion(data) {
        console.log('Displaying question:', data);
        if (!data || !data.question_text) {
            console.log('No question data, ending interview');
            endInterview("end");
            return;
        }
        progressInfo.textContent = `Question ${data.question_number} of ${data.total_questions}`;
        currentQuestionBox.innerHTML = `<strong>Q:</strong> ${data.question_text}`;
        answerInput.value = '';
        answerInput.focus();
    }
    
    function addChatMessage(message, sender = 'assistant') {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        messageDiv.innerHTML = message;
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    async function handleAnswerSubmission(action) {
        if (!appState.sessionId) {
            showToast('No active session found', 'error');
            return;
        }

        const payload = { 
            session_id: appState.sessionId,
            answer: answerInput.value.trim(),
            action: action,
        };

        const response = await apiClient(`/${appState.sessionId}/submit-answer`, 'POST', payload);

        if (response) {
            if (action === 'submit' && payload.answer) {
                addChatMessage(`<strong>Your Answer:</strong> ${payload.answer}`, 'user');
                if(response.evaluation) {
                    addChatMessage(`<strong>Feedback:</strong> ${response.evaluation.feedback} (Score: ${response.evaluation.score}/10)`);
                }
            }
            
            if (response.hint) {
                addChatMessage(`<strong>Hint:</strong> ${response.hint}`);
            }
            
            if (response.next_question) {
                displayQuestion(response.next_question);
            }
            
            if (response.report) {
                renderReport(response.report);
                showPage('report');
            }
            
            if (response.message) {
                if (response.message.includes("completed") || response.message.includes("ended")) {
                    showToast("Interview finished!");
                    if (!response.report) {
                        const reportData = await apiClient(`/${appState.sessionId}/report`);
                        if (reportData) {
                            renderReport(reportData);
                            showPage('report');
                        }
                    }
                }
            }
        }
    }
    
    async function endInterview(action) {
        if (!appState.sessionId) {
            showToast('No active session found', 'error');
            return;
        }
        
        clearInterval(appState.timerInterval);
        const response = await apiClient(`/${appState.sessionId}/report`);
        if (response) {
            renderReport(response);
            showPage('report');
        } else {
            showToast("Could not fetch the report.", "error");
        }
    }
    
    function renderReport(report) {
        clearInterval(appState.timerInterval);
        
        // Summary
        const summary = report.session_info;
        reportSummary.innerHTML = `
            <div class="metric"><div class="metric-value">${formatRoleName(summary.role)}</div><div class="metric-label">Role</div></div>
            <div class="metric"><div class="metric-value">${summary.questions_attempted}/${summary.total_questions}</div><div class="metric-label">Attempted</div></div>
            <div class="metric"><div class="metric-value">${(report.final_evaluation.overall_score || 'N/A')} / 10</div><div class="metric-label">Overall Score</div></div>
            <div class="metric"><div class="metric-value">${Math.round(summary.total_time_minutes)} min</div><div class="metric-label">Time Taken</div></div>
        `;
        
        // Question Analysis
        questionAnalysis.innerHTML = '<h3>Question-by-Question Analysis</h3>';
        report.questions.forEach((q, index) => {
            const score = q.evaluation.score || 0;
            let scoreClass = 'score-fair';
            if (score >= 8) scoreClass = 'score-excellent';
            else if (score >= 5) scoreClass = 'score-good';

            questionAnalysis.innerHTML += `
                <div class="question-item">
                    <p><strong>Q${index + 1}:</strong> ${q.question} <span class="score-badge ${scoreClass}">${score}/10</span></p>
                    <p><strong>Answer:</strong> ${q.answer || '<em>Not answered</em>'}</p>
                    <p><strong>Feedback:</strong> ${q.evaluation.feedback || 'No feedback available'}</p>
                </div>
            `;
        });
        
        // Overall Evaluation
        overallEvaluation.innerHTML = `
            <h3>Final Evaluation</h3>
            <p><strong>Strengths:</strong> ${report.final_evaluation.strengths || 'Not available'}</p>
            <p><strong>Areas for Improvement:</strong> ${report.final_evaluation.areas_for_improvement || 'Not available'}</p>
        `;
        
        showPage('report');
    }

    // --- EVENT LISTENERS ---

    document.addEventListener('DOMContentLoaded', () => {
        console.log('DOM loaded, initializing app...');
        showPage('home');
        
        // Navigation event listeners
        startInterviewBtn.addEventListener('click', () => {
            console.log('Start interview button clicked');
            showPage('config');
        });
        
        backHomeBtn.addEventListener('click', () => showPage('home'));
        backHomeReportBtn.addEventListener('click', () => showPage('home'));
        
        newInterviewBtn.addEventListener('click', () => {
            // Reset form for new interview
            configForm.reset();
            difficultyDetails.style.display = 'none';
            roleSelect.innerHTML = '<option value="">Select Role</option>';
            showPage('config');
        });

        // Form event listeners
        categorySelect.addEventListener('change', populateRoles);
        difficultySelect.addEventListener('change', updateDifficultyDetails);

        // Main form submission
        configForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            console.log('Form submitted');
            
            const config = {
                category: categorySelect.value,
                role: roleSelect.value,
                difficulty: difficultySelect.value,
            };
            
            console.log('Interview config:', config);
            
            // Validate form
            if (!config.category || !config.role || !config.difficulty) {
                showToast('Please fill in all fields', 'error');
                return;
            }
            
            // Start the interview
            const sessionData = await apiClient('/start', 'POST', config);
            
            if (sessionData && sessionData.session_id) {
                console.log('Session created:', sessionData);
                appState.sessionId = sessionData.session_id;
                showPage('interview');
                startTimer(sessionData.time_limit_minutes);
                
                // Clear previous messages
                chatMessages.innerHTML = '';
                
                // Fetch first question
                const questionData = await apiClient(`/${appState.sessionId}/current-question`);
                if (questionData) {
                    displayQuestion(questionData);
                } else {
                    showToast('Failed to load first question', 'error');
                }
            } else {
                showToast('Failed to start interview session', 'error');
            }
        });

        // Interview action buttons
        submitBtn.addEventListener('click', () => {
            if (!answerInput.value.trim()) {
                showToast('Please enter an answer before submitting', 'warning');
                return;
            }
            handleAnswerSubmission('submit');
        });
        
        hintBtn.addEventListener('click', () => handleAnswerSubmission('hint'));
        skipBtn.addEventListener('click', () => handleAnswerSubmission('skip'));
        
        endBtn.addEventListener('click', () => {
            if (confirm('Are you sure you want to end the interview?')) {
                endInterview('end');
            }
        });

        // Add Enter key support for answer submission
        answerInput.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 'Enter') {
                e.preventDefault();
                if (answerInput.value.trim()) {
                    handleAnswerSubmission('submit');
                }
            }
        });

        console.log('App initialization complete');
    });

})();