/**
 * Advanced Memory Manager for persistent user experience
 * Handles session state, form data, trip preparations, and browsing history
 */

class MemoryManager {
    constructor() {
        this.sessionId = this.getOrCreateSessionId();
        this.autoSaveInterval = 30000; // Auto-save every 30 seconds
        this.stateCache = {};
        this.isInitialized = false;
        
        this.init();
    }
    
    async init() {
        try {
            // Restore session state on page load
            await this.restoreSessionState();
            
            // Set up auto-save
            this.setupAutoSave();
            
            // Set up form monitoring
            this.setupFormMonitoring();
            
            // Set up page state tracking
            this.setupPageStateTracking();
            
            this.isInitialized = true;
            console.log('🧠 Memory Manager initialized');
        } catch (error) {
            console.error('Memory Manager initialization failed:', error);
        }
    }
    
    getOrCreateSessionId() {
        let sessionId = localStorage.getItem('travel_session_id');
        if (!sessionId) {
            // Use crypto.randomUUID() if available, otherwise fallback to timestamp-based ID
            if (crypto && crypto.randomUUID) {
                sessionId = 'session_' + crypto.randomUUID();
            } else {
                // Fallback for older browsers
                sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            }
            localStorage.setItem('travel_session_id', sessionId);
        }
        return sessionId;
    }
    
    // Session State Management
    async saveSessionState(stateData) {
        try {
            const response = await fetch('/api/session/save', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(stateData)
            });
            
            if (response.ok) {
                this.stateCache = { ...this.stateCache, ...stateData };
                console.log('💾 Session state saved');
                return true;
            }
            return false;
        } catch (error) {
            console.error('Failed to save session state:', error);
            return false;
        }
    }
    
    async restoreSessionState() {
        try {
            const response = await fetch('/api/session/restore');
            const data = await response.json();
            
            if (data.state) {
                this.stateCache = data.state;
                this.applyRestoredState(data.state);
                console.log('🔄 Session state restored');
            }
        } catch (error) {
            console.error('Failed to restore session state:', error);
        }
    }
    
    applyRestoredState(state) {
        // Restore form values
        if (state.formData) {
            this.restoreFormData(state.formData);
        }
        
        // Restore selections
        if (state.selections) {
            this.restoreSelections(state.selections);
        }
        
        // Restore page-specific data
        if (state.pageData) {
            this.restorePageData(state.pageData);
        }
    }
    
    // Trip Preparation Management
    async saveTripPreparation(prepData) {
        try {
            const response = await fetch('/api/trip-preparation/save', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(prepData)
            });
            
            const result = await response.json();
            if (result.success) {
                console.log('📝 Trip preparation saved:', result.prep_id);
                return result.prep_id;
            }
            return null;
        } catch (error) {
            console.error('Failed to save trip preparation:', error);
            return null;
        }
    }
    
    async getTripPreparations() {
        try {
            const response = await fetch('/api/trip-preparation/list');
            const data = await response.json();
            
            if (data.success) {
                return data.preparations;
            }
            return [];
        } catch (error) {
            console.error('Failed to get trip preparations:', error);
            return [];
        }
    }
    
    async getSearchHistory(limit = 20) {
        try {
            const response = await fetch(`/api/search-history?limit=${limit}`);
            const data = await response.json();
            
            if (data.success) {
                return data.history;
            }
            return [];
        } catch (error) {
            console.error('Failed to get search history:', error);
            return [];
        }
    }
    
    // Form Monitoring and Auto-save
    setupFormMonitoring() {
        const forms = document.querySelectorAll('form');
        forms.forEach(form => {
            const inputs = form.querySelectorAll('input, select, textarea');
            inputs.forEach(input => {
                input.addEventListener('input', () => {
                    this.captureFormState();
                });
                input.addEventListener('change', () => {
                    this.captureFormState();
                });
            });
        });
    }
    
    captureFormState() {
        const formData = {};
        const forms = document.querySelectorAll('form');
        
        forms.forEach((form, index) => {
            const formId = form.id || `form_${index}`;
            formData[formId] = {};
            
            const inputs = form.querySelectorAll('input, select, textarea');
            inputs.forEach(input => {
                if (input.name) {
                    if (input.type === 'checkbox' || input.type === 'radio') {
                        formData[formId][input.name] = input.checked;
                    } else {
                        formData[formId][input.name] = input.value;
                    }
                }
            });
        });
        
        // Capture route type selections
        const selectedRouteTypes = [];
        document.querySelectorAll('.route-type-card.selected').forEach(card => {
            selectedRouteTypes.push(card.dataset.type);
        });
        
        this.stateCache.formData = formData;
        this.stateCache.selectedRouteTypes = selectedRouteTypes;
        this.stateCache.timestamp = new Date().toISOString();
    }
    
    restoreFormData(formData) {
        Object.keys(formData).forEach(formId => {
            const form = document.getElementById(formId) || document.querySelectorAll('form')[parseInt(formId.replace('form_', '')) || 0];
            if (!form) return;
            
            Object.keys(formData[formId]).forEach(inputName => {
                const input = form.querySelector(`[name="${inputName}"]`);
                if (input) {
                    if (input.type === 'checkbox' || input.type === 'radio') {
                        input.checked = formData[formId][inputName];
                    } else {
                        input.value = formData[formId][inputName];
                    }
                }
            });
        });
    }
    
    restoreSelections(selections) {
        // Restore route type selections
        if (selections.selectedRouteTypes) {
            document.querySelectorAll('.route-type-card').forEach(card => {
                if (selections.selectedRouteTypes.includes(card.dataset.type)) {
                    card.classList.add('selected');
                }
            });
        }
    }
    
    // Page State Tracking
    setupPageStateTracking() {
        // Track scroll position
        let scrollTimeout;
        window.addEventListener('scroll', () => {
            clearTimeout(scrollTimeout);
            scrollTimeout = setTimeout(() => {
                this.stateCache.scrollPosition = window.pageYOffset;
            }, 100);
        });
        
        // Restore scroll position
        if (this.stateCache.scrollPosition) {
            setTimeout(() => {
                window.scrollTo(0, this.stateCache.scrollPosition);
            }, 100);
        }
    }
    
    restorePageData(pageData) {
        // Restore scroll position
        if (pageData.scrollPosition) {
            setTimeout(() => {
                window.scrollTo(0, pageData.scrollPosition);
            }, 100);
        }
    }
    
    // Auto-save functionality
    setupAutoSave() {
        setInterval(() => {
            if (this.isInitialized && Object.keys(this.stateCache).length > 0) {
                this.saveSessionState(this.stateCache);
            }
        }, this.autoSaveInterval);
        
        // Save on page unload
        window.addEventListener('beforeunload', () => {
            this.captureFormState();
            if (Object.keys(this.stateCache).length > 0) {
                // Use sendBeacon for reliable saving on page unload
                navigator.sendBeacon('/api/session/save', JSON.stringify(this.stateCache));
            }
        });
    }
    
    // Trip Preparation Helpers
    async autoSaveTripPreparation() {
        const currentForm = this.getCurrentTripFormData();
        if (currentForm && (currentForm.start_location || currentForm.end_location)) {
            const prepId = await this.saveTripPreparation(currentForm);
            if (prepId) {
                this.showNotification('Trip preparation auto-saved', 'success');
            }
        }
    }
    
    getCurrentTripFormData() {
        return {
            start_location: document.getElementById('startLocation')?.value || '',
            end_location: document.getElementById('endLocation')?.value || '',
            route_types: this.stateCache.selectedRouteTypes || [],
            timestamp: new Date().toISOString(),
            status: 'draft'
        };
    }
    
    // History Management
    async displayTripPreparations() {
        const preparations = await this.getTripPreparations();
        const container = document.getElementById('tripPreparationsContainer');
        
        if (!container || preparations.length === 0) return;
        
        const html = preparations.map(prep => {
            const data = JSON.parse(prep.prep_data);
            return `
                <div class="trip-preparation-item" onclick="memoryManager.loadTripPreparation('${prep.prep_id}')">
                    <h4>${prep.prep_name}</h4>
                    <p>${data.start_location} → ${data.end_location}</p>
                    <small>Saved: ${new Date(prep.created_at).toLocaleDateString()}</small>
                </div>
            `;
        }).join('');
        
        container.innerHTML = html;
    }
    
    async loadTripPreparation(prepId) {
        const preparations = await this.getTripPreparations();
        const prep = preparations.find(p => p.prep_id === prepId);
        
        if (prep) {
            const data = JSON.parse(prep.prep_data);
            this.applyTripData(data);
            this.showNotification('Trip preparation loaded', 'success');
        }
    }
    
    applyTripData(data) {
        if (data.start_location) {
            const startInput = document.getElementById('startLocation');
            if (startInput) startInput.value = data.start_location;
        }
        
        if (data.end_location) {
            const endInput = document.getElementById('endLocation');
            if (endInput) endInput.value = data.end_location;
        }
        
        if (data.route_types) {
            document.querySelectorAll('.route-type-card').forEach(card => {
                if (data.route_types.includes(card.dataset.type)) {
                    card.classList.add('selected');
                } else {
                    card.classList.remove('selected');
                }
            });
        }
    }
    
    // Utility Methods
    showNotification(message, type = 'info') {
        // Create or update notification element
        let notification = document.getElementById('memoryNotification');
        if (!notification) {
            notification = document.createElement('div');
            notification.id = 'memoryNotification';
            notification.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 12px 20px;
                border-radius: 8px;
                color: white;
                font-weight: 500;
                z-index: 10000;
                opacity: 0;
                transition: opacity 0.3s ease;
            `;
            document.body.appendChild(notification);
        }
        
        notification.textContent = message;
        notification.className = `notification-${type}`;
        
        // Style based on type
        const styles = {
            success: 'background: #10b981;',
            error: 'background: #ef4444;',
            info: 'background: #3b82f6;',
            warning: 'background: #f59e0b;'
        };
        
        notification.style.cssText += styles[type] || styles.info;
        notification.style.opacity = '1';
        
        setTimeout(() => {
            notification.style.opacity = '0';
        }, 3000);
    }
    
    // Public API
    clearMemory() {
        this.stateCache = {};
        localStorage.removeItem('travel_session_id');
        this.showNotification('Memory cleared', 'info');
    }
    
    exportData() {
        return {
            sessionState: this.stateCache,
            sessionId: this.sessionId,
            timestamp: new Date().toISOString()
        };
    }
}

// Initialize Memory Manager
let memoryManager;
document.addEventListener('DOMContentLoaded', () => {
    memoryManager = new MemoryManager();
    
    // Make it globally available
    window.memoryManager = memoryManager;
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MemoryManager;
}