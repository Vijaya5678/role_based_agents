// API Configuration
const API_CONFIG = {
    // FIX: The base URL must include the full prefix from your FastAPI router.
    BASE_URL: 'http://localhost:8081/api/interview',
    TIMEOUT: 30000
};

// Application Configuration
const APP_CONFIG = {
    CATEGORIES: {
        'technical': [
            'software_engineer',
            'data_scientist', 
            'devops_engineer',
            'frontend_developer',
            'backend_developer',
            'fullstack_developer'
        ],
        'non_technical': [
            'product_manager',
            'business_analyst',
            'project_manager',
            'marketing_manager',
            'sales_representative'
        ]
    },
    
    DIFFICULTY_INFO: {
        'beginner': {
            questions: 5,
            time: 15,
            description: 'Basic concepts and fundamentals'
        },
        'intermediate': {
            questions: 8, 
            time: 25,
            description: 'Practical application and problem-solving'
        },
        'advanced': {
            questions: 12,
            time: 40,
            description: 'Complex scenarios and system design'
        }
    }
};

// Format role names for display
function formatRoleName(role) {
    return role.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

// Format category names for display
function formatCategoryName(category) {
    return category.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}