// Travel Features - Fully Functional Implementation
class TravelFeatures {
    constructor() {
        this.currentTripId = this.getTripId();
        this.budget = new BudgetTracker();
        this.journal = new TravelJournal();
        this.packing = new PackingAssistant();
        this.transport = new TransportGuide();
        this.emergency = new EmergencyInfo();
        this.experiences = new ExperiencesFinder();
        this.init();
    }

    getTripId() {
        const savedTrip = sessionStorage.getItem('selectedRoute');
        if (savedTrip) {
            try {
                const tripData = JSON.parse(savedTrip);
                return tripData.id || 1;
            } catch (e) {
                return 1;
            }
        }
        return 1;
    }

    init() {
        // Initialize all features
        this.setupEventListeners();
        this.loadInitialData();
    }

    setupEventListeners() {
        // Override the placeholder functions in the HTML
        window.openBudgetModal = () => this.budget.openModal();
        window.openJournalModal = () => this.journal.openModal();
        window.openPackingModal = () => this.packing.openModal();
        window.openTransportModal = () => this.transport.openModal();
        window.openEmergencyModal = () => this.emergency.openModal();
        window.openExperiencesModal = () => this.experiences.openModal();
    }

    async loadInitialData() {
        // Load data for all features
        await Promise.all([
            this.budget.loadData(),
            this.journal.loadData(),
            this.packing.loadData(),
            this.transport.loadData()
        ]);
    }

    showToast(message, type = 'success') {
        const toast = document.createElement('div');
        toast.className = `toast ${type} show`;
        toast.innerHTML = `
            <div style="display: flex; align-items: center; gap: 0.5rem;">
                <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'}"></i>
                <span>${message}</span>
            </div>
        `;
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => document.body.removeChild(toast), 300);
        }, 3000);
    }
}

// Budget Tracker Implementation
class BudgetTracker {
    constructor() {
        this.expenses = [];
        this.categories = ['Accommodation', 'Food', 'Transport', 'Activities', 'Shopping', 'Other'];
        this.currencies = ['EUR', 'USD', 'GBP'];
    }

    async loadData() {
        // Load expenses from localStorage
        const saved = localStorage.getItem('tripBudget');
        if (saved) {
            this.expenses = JSON.parse(saved);
            this.updateSummary();
        }
    }

    updateSummary() {
        const total = this.expenses.reduce((sum, exp) => sum + exp.amount, 0);
        const count = this.expenses.length;
        
        const totalEl = document.getElementById('budget-total');
        const countEl = document.getElementById('budget-expenses');
        
        if (totalEl) totalEl.textContent = `€${total.toFixed(0)}`;
        if (countEl) countEl.textContent = count;
    }

    openModal() {
        const modal = this.createModal();
        document.body.appendChild(modal);
        modal.style.display = 'flex';
        this.renderExpenses();
    }

    createModal() {
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content" style="max-width: 800px;">
                <div class="modal-header">
                    <h3><i class="fas fa-euro-sign"></i> Budget Tracker</h3>
                    <button onclick="this.closest('.modal').remove()" class="close-btn">&times;</button>
                </div>
                <div class="modal-body">
                    <!-- Add Expense Form -->
                    <div style="background: rgba(255,255,255,0.05); padding: 1.5rem; border-radius: 15px; margin-bottom: 2rem;">
                        <h4 style="color: white; margin-bottom: 1rem;">Add New Expense</h4>
                        <div style="display: grid; grid-template-columns: 2fr 1fr 1fr 1fr; gap: 1rem;">
                            <input type="text" id="expense-name" class="form-control" placeholder="Expense name">
                            <input type="number" id="expense-amount" class="form-control" placeholder="Amount" step="0.01">
                            <select id="expense-category" class="form-control">
                                ${this.categories.map(cat => `<option value="${cat}">${cat}</option>`).join('')}
                            </select>
                            <button onclick="travelFeatures.budget.addExpense()" class="btn">
                                <i class="fas fa-plus"></i> Add
                            </button>
                        </div>
                    </div>

                    <!-- Summary Cards -->
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem;">
                        <div style="background: rgba(255,107,53,0.1); padding: 1.5rem; border-radius: 15px; text-align: center;">
                            <div style="font-size: 2rem; font-weight: 700; color: var(--tuscan-gold);" id="modal-total">€0</div>
                            <div style="color: rgba(255,255,255,0.8);">Total Spent</div>
                        </div>
                        <div style="background: rgba(114,9,183,0.1); padding: 1.5rem; border-radius: 15px; text-align: center;">
                            <div style="font-size: 2rem; font-weight: 700; color: var(--coastal-mint);" id="modal-daily">€0</div>
                            <div style="color: rgba(255,255,255,0.8);">Daily Average</div>
                        </div>
                        <div style="background: rgba(6,255,165,0.1); padding: 1.5rem; border-radius: 15px; text-align: center;">
                            <div style="font-size: 2rem; font-weight: 700; color: var(--sunset-orange);" id="modal-count">0</div>
                            <div style="color: rgba(255,255,255,0.8);">Expenses</div>
                        </div>
                    </div>

                    <!-- Category Breakdown -->
                    <div id="category-breakdown" style="margin-bottom: 2rem;"></div>

                    <!-- Expenses List -->
                    <h4 style="color: white; margin-bottom: 1rem;">Recent Expenses</h4>
                    <div id="expenses-list" style="max-height: 300px; overflow-y: auto;"></div>
                </div>
            </div>
        `;
        return modal;
    }

    addExpense() {
        const name = document.getElementById('expense-name').value;
        const amount = parseFloat(document.getElementById('expense-amount').value);
        const category = document.getElementById('expense-category').value;

        if (!name || !amount) {
            travelFeatures.showToast('Please fill in all fields', 'error');
            return;
        }

        const expense = {
            id: Date.now(),
            name,
            amount,
            category,
            date: new Date().toISOString(),
            currency: 'EUR'
        };

        this.expenses.push(expense);
        this.saveData();
        this.renderExpenses();
        
        // Clear form
        document.getElementById('expense-name').value = '';
        document.getElementById('expense-amount').value = '';
        
        travelFeatures.showToast('Expense added successfully!');
    }

    deleteExpense(id) {
        this.expenses = this.expenses.filter(exp => exp.id !== id);
        this.saveData();
        this.renderExpenses();
        travelFeatures.showToast('Expense deleted');
    }

    renderExpenses() {
        const listEl = document.getElementById('expenses-list');
        const totalEl = document.getElementById('modal-total');
        const dailyEl = document.getElementById('modal-daily');
        const countEl = document.getElementById('modal-count');
        
        if (!listEl) return;

        // Calculate totals
        const total = this.expenses.reduce((sum, exp) => sum + exp.amount, 0);
        const days = this.getUniqueDays();
        const dailyAvg = days > 0 ? total / days : 0;

        // Update summary
        if (totalEl) totalEl.textContent = `€${total.toFixed(2)}`;
        if (dailyEl) dailyEl.textContent = `€${dailyAvg.toFixed(2)}`;
        if (countEl) countEl.textContent = this.expenses.length;

        // Render category breakdown
        this.renderCategoryBreakdown();

        // Render expenses list
        listEl.innerHTML = this.expenses.length === 0 ? 
            '<p style="color: rgba(255,255,255,0.6); text-align: center;">No expenses yet</p>' :
            this.expenses.sort((a, b) => new Date(b.date) - new Date(a.date)).map(exp => `
                <div style="background: rgba(255,255,255,0.05); padding: 1rem; border-radius: 10px; margin-bottom: 0.5rem; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="color: white; font-weight: 600;">${exp.name}</div>
                        <div style="color: rgba(255,255,255,0.6); font-size: 0.9rem;">
                            ${exp.category} • ${new Date(exp.date).toLocaleDateString()}
                        </div>
                    </div>
                    <div style="display: flex; align-items: center; gap: 1rem;">
                        <div style="color: var(--tuscan-gold); font-weight: 700; font-size: 1.1rem;">
                            €${exp.amount.toFixed(2)}
                        </div>
                        <button onclick="travelFeatures.budget.deleteExpense(${exp.id})" 
                                style="background: rgba(255,107,53,0.2); border: none; color: var(--sunset-orange); 
                                       padding: 0.5rem; border-radius: 8px; cursor: pointer;">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
            `).join('');

        this.updateSummary();
    }

    renderCategoryBreakdown() {
        const breakdownEl = document.getElementById('category-breakdown');
        if (!breakdownEl) return;

        // Calculate category totals
        const categoryTotals = {};
        this.expenses.forEach(exp => {
            categoryTotals[exp.category] = (categoryTotals[exp.category] || 0) + exp.amount;
        });

        const total = Object.values(categoryTotals).reduce((sum, val) => sum + val, 0);

        breakdownEl.innerHTML = `
            <h4 style="color: white; margin-bottom: 1rem;">Spending by Category</h4>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1rem;">
                ${Object.entries(categoryTotals).map(([category, amount]) => {
                    const percentage = total > 0 ? (amount / total * 100) : 0;
                    return `
                        <div style="text-align: center;">
                            <div style="font-size: 1.3rem; font-weight: 700; color: var(--tuscan-gold);">
                                €${amount.toFixed(2)}
                            </div>
                            <div style="color: rgba(255,255,255,0.8); font-size: 0.9rem;">${category}</div>
                            <div style="color: rgba(255,255,255,0.6); font-size: 0.8rem;">${percentage.toFixed(1)}%</div>
                        </div>
                    `;
                }).join('')}
            </div>
        `;
    }

    getUniqueDays() {
        const dates = new Set();
        this.expenses.forEach(exp => {
            dates.add(new Date(exp.date).toDateString());
        });
        return dates.size;
    }

    saveData() {
        localStorage.setItem('tripBudget', JSON.stringify(this.expenses));
    }
}

// Travel Journal Implementation
class TravelJournal {
    constructor() {
        this.entries = [];
    }

    async loadData() {
        const saved = localStorage.getItem('travelJournal');
        if (saved) {
            this.entries = JSON.parse(saved);
        }
    }

    openModal() {
        const modal = this.createModal();
        document.body.appendChild(modal);
        modal.style.display = 'flex';
        this.renderEntries();
    }

    createModal() {
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content" style="max-width: 900px;">
                <div class="modal-header">
                    <h3><i class="fas fa-book-open"></i> Travel Journal</h3>
                    <button onclick="this.closest('.modal').remove()" class="close-btn">&times;</button>
                </div>
                <div class="modal-body">
                    <!-- Write Entry Form -->
                    <div id="entry-form" style="background: rgba(255,255,255,0.05); padding: 2rem; border-radius: 15px; margin-bottom: 2rem;">
                        <h4 style="color: white; margin-bottom: 1rem;">Write New Entry</h4>
                        <input type="text" id="entry-title" class="form-control" placeholder="Entry title" style="margin-bottom: 1rem;">
                        <input type="text" id="entry-location" class="form-control" placeholder="Location" style="margin-bottom: 1rem;">
                        <textarea id="entry-content" class="form-control" placeholder="Share your experience..." 
                                  style="min-height: 150px; margin-bottom: 1rem;"></textarea>
                        <div style="display: flex; gap: 1rem;">
                            <select id="entry-mood" class="form-control" style="flex: 1;">
                                <option value="">Select mood</option>
                                <option value="happy">😊 Happy</option>
                                <option value="excited">🎉 Excited</option>
                                <option value="peaceful">😌 Peaceful</option>
                                <option value="adventurous">🏔️ Adventurous</option>
                                <option value="romantic">❤️ Romantic</option>
                            </select>
                            <button onclick="travelFeatures.journal.saveEntry()" class="btn" style="flex: 1;">
                                <i class="fas fa-save"></i> Save Entry
                            </button>
                        </div>
                    </div>

                    <!-- Entries List -->
                    <h4 style="color: white; margin-bottom: 1rem;">Your Travel Stories</h4>
                    <div id="journal-entries" style="max-height: 500px; overflow-y: auto;"></div>
                </div>
            </div>
        `;
        return modal;
    }

    saveEntry() {
        const title = document.getElementById('entry-title').value;
        const location = document.getElementById('entry-location').value;
        const content = document.getElementById('entry-content').value;
        const mood = document.getElementById('entry-mood').value;

        if (!title || !content) {
            travelFeatures.showToast('Please fill in title and content', 'error');
            return;
        }

        const entry = {
            id: Date.now(),
            title,
            location,
            content,
            mood,
            date: new Date().toISOString()
        };

        this.entries.unshift(entry);
        this.saveData();
        this.renderEntries();
        
        // Clear form
        document.getElementById('entry-title').value = '';
        document.getElementById('entry-location').value = '';
        document.getElementById('entry-content').value = '';
        document.getElementById('entry-mood').value = '';
        
        travelFeatures.showToast('Journal entry saved!');
    }

    deleteEntry(id) {
        this.entries = this.entries.filter(entry => entry.id !== id);
        this.saveData();
        this.renderEntries();
        travelFeatures.showToast('Entry deleted');
    }

    renderEntries() {
        const container = document.getElementById('journal-entries');
        if (!container) return;

        container.innerHTML = this.entries.length === 0 ?
            '<p style="color: rgba(255,255,255,0.6); text-align: center;">No journal entries yet. Start documenting your journey!</p>' :
            this.entries.map(entry => `
                <div style="background: rgba(255,255,255,0.05); padding: 2rem; border-radius: 15px; margin-bottom: 1rem;">
                    <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 1rem;">
                        <div>
                            <h5 style="color: white; margin: 0; font-size: 1.2rem;">${entry.title}</h5>
                            <div style="color: rgba(255,255,255,0.6); font-size: 0.9rem; margin-top: 0.5rem;">
                                ${entry.location ? `📍 ${entry.location} • ` : ''}
                                ${new Date(entry.date).toLocaleDateString()}
                                ${entry.mood ? ` • ${this.getMoodEmoji(entry.mood)}` : ''}
                            </div>
                        </div>
                        <button onclick="travelFeatures.journal.deleteEntry(${entry.id})" 
                                style="background: rgba(255,107,53,0.2); border: none; color: var(--sunset-orange); 
                                       padding: 0.5rem 1rem; border-radius: 8px; cursor: pointer;">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                    <div style="color: rgba(255,255,255,0.9); line-height: 1.6; white-space: pre-wrap;">
                        ${entry.content}
                    </div>
                </div>
            `).join('');
    }

    getMoodEmoji(mood) {
        const moods = {
            happy: '😊',
            excited: '🎉',
            peaceful: '😌',
            adventurous: '🏔️',
            romantic: '❤️'
        };
        return moods[mood] || '';
    }

    saveData() {
        localStorage.setItem('travelJournal', JSON.stringify(this.entries));
    }
}

// Packing Assistant Implementation
class PackingAssistant {
    constructor() {
        this.lists = [];
        this.templates = {
            summer: {
                clothing: ['T-shirts (5)', 'Shorts (3)', 'Swimsuit', 'Light jacket', 'Underwear (7)', 'Socks (7)'],
                essentials: ['Passport', 'Tickets', 'Phone charger', 'Adapter', 'Sunscreen', 'Sunglasses'],
                toiletries: ['Toothbrush', 'Toothpaste', 'Shampoo', 'Deodorant', 'Medications'],
                extras: ['Camera', 'Beach towel', 'Flip flops', 'Hat']
            },
            winter: {
                clothing: ['Warm jacket', 'Sweaters (3)', 'Long pants (3)', 'Thermal underwear', 'Gloves', 'Scarf'],
                essentials: ['Passport', 'Tickets', 'Phone charger', 'Adapter', 'Lip balm', 'Hand cream'],
                toiletries: ['Toothbrush', 'Toothpaste', 'Shampoo', 'Deodorant', 'Medications'],
                extras: ['Camera', 'Boots', 'Warm hat', 'Hand warmers']
            }
        };
    }

    async loadData() {
        const saved = localStorage.getItem('packingLists');
        if (saved) {
            this.lists = JSON.parse(saved);
            this.updateProgress();
        }
    }

    updateProgress() {
        const progressCircle = document.querySelector('.progress-circle');
        const progressValue = document.querySelector('.progress-value');
        
        if (!progressCircle || !progressValue || this.lists.length === 0) return;

        const currentList = this.lists[0];
        if (!currentList) return;

        const totalItems = Object.values(currentList.items).flat().length;
        const packedItems = Object.values(currentList.packed).flat().filter(Boolean).length;
        const percentage = totalItems > 0 ? Math.round((packedItems / totalItems) * 100) : 0;

        progressValue.textContent = `${percentage}%`;
        progressCircle.style.background = 
            `conic-gradient(from 0deg, var(--tuscan-gold) ${percentage * 3.6}deg, rgba(255,255,255,0.2) ${percentage * 3.6}deg)`;
    }

    openModal() {
        const modal = this.createModal();
        document.body.appendChild(modal);
        modal.style.display = 'flex';
        this.renderLists();
    }

    createModal() {
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content" style="max-width: 900px;">
                <div class="modal-header">
                    <h3><i class="fas fa-suitcase-rolling"></i> Smart Packing Assistant</h3>
                    <button onclick="this.closest('.modal').remove()" class="close-btn">&times;</button>
                </div>
                <div class="modal-body">
                    <!-- Generate New List -->
                    <div style="background: rgba(255,255,255,0.05); padding: 1.5rem; border-radius: 15px; margin-bottom: 2rem;">
                        <h4 style="color: white; margin-bottom: 1rem;">Generate New Packing List</h4>
                        <div style="display: grid; grid-template-columns: 2fr 1fr 1fr; gap: 1rem;">
                            <input type="text" id="list-name" class="form-control" placeholder="List name (e.g., Weekend in Paris)">
                            <select id="list-season" class="form-control">
                                <option value="summer">Summer</option>
                                <option value="winter">Winter</option>
                                <option value="spring">Spring/Fall</option>
                            </select>
                            <button onclick="travelFeatures.packing.generateList()" class="btn">
                                <i class="fas fa-magic"></i> Generate
                            </button>
                        </div>
                    </div>

                    <!-- Packing Lists -->
                    <div id="packing-lists"></div>
                </div>
            </div>
        `;
        return modal;
    }

    generateList() {
        const name = document.getElementById('list-name').value || 'My Packing List';
        const season = document.getElementById('list-season').value;

        const template = season === 'winter' ? this.templates.winter : this.templates.summer;
        
        const list = {
            id: Date.now(),
            name,
            season,
            items: { ...template },
            packed: {
                clothing: new Array(template.clothing.length).fill(false),
                essentials: new Array(template.essentials.length).fill(false),
                toiletries: new Array(template.toiletries.length).fill(false),
                extras: new Array(template.extras.length).fill(false)
            },
            customItems: []
        };

        this.lists.unshift(list);
        this.saveData();
        this.renderLists();
        
        travelFeatures.showToast('Packing list generated!');
    }

    toggleItem(listId, category, index) {
        const list = this.lists.find(l => l.id === listId);
        if (!list) return;

        list.packed[category][index] = !list.packed[category][index];
        this.saveData();
        this.updateListProgress(listId);
        this.updateProgress();
    }

    updateListProgress(listId) {
        const progressEl = document.getElementById(`progress-${listId}`);
        if (!progressEl) return;

        const list = this.lists.find(l => l.id === listId);
        if (!list) return;

        const totalItems = Object.values(list.items).flat().length;
        const packedItems = Object.values(list.packed).flat().filter(Boolean).length;
        const percentage = totalItems > 0 ? Math.round((packedItems / totalItems) * 100) : 0;

        progressEl.textContent = `${percentage}% Complete`;
        progressEl.style.color = percentage === 100 ? 'var(--coastal-mint)' : 'var(--tuscan-gold)';
    }

    addCustomItem(listId, category) {
        const input = document.getElementById(`custom-${listId}-${category}`);
        if (!input || !input.value) return;

        const list = this.lists.find(l => l.id === listId);
        if (!list) return;

        list.items[category].push(input.value);
        list.packed[category].push(false);
        
        input.value = '';
        this.saveData();
        this.renderLists();
        
        travelFeatures.showToast('Item added!');
    }

    deleteList(id) {
        this.lists = this.lists.filter(list => list.id !== id);
        this.saveData();
        this.renderLists();
        travelFeatures.showToast('List deleted');
    }

    renderLists() {
        const container = document.getElementById('packing-lists');
        if (!container) return;

        container.innerHTML = this.lists.length === 0 ?
            '<p style="color: rgba(255,255,255,0.6); text-align: center;">No packing lists yet. Generate one above!</p>' :
            this.lists.map(list => `
                <div style="background: rgba(255,255,255,0.05); padding: 2rem; border-radius: 15px; margin-bottom: 1.5rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
                        <div>
                            <h4 style="color: white; margin: 0;">${list.name}</h4>
                            <div style="color: rgba(255,255,255,0.6); font-size: 0.9rem;">
                                ${list.season.charAt(0).toUpperCase() + list.season.slice(1)} Trip
                            </div>
                        </div>
                        <div style="display: flex; align-items: center; gap: 1rem;">
                            <div id="progress-${list.id}" style="color: var(--tuscan-gold); font-weight: 600;">
                                0% Complete
                            </div>
                            <button onclick="travelFeatures.packing.deleteList(${list.id})" 
                                    style="background: rgba(255,107,53,0.2); border: none; color: var(--sunset-orange); 
                                           padding: 0.5rem 1rem; border-radius: 8px; cursor: pointer;">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1.5rem;">
                        ${Object.entries(list.items).map(([category, items]) => `
                            <div>
                                <h5 style="color: var(--tuscan-gold); text-transform: capitalize; margin-bottom: 0.5rem;">
                                    ${category}
                                </h5>
                                ${items.map((item, index) => `
                                    <label style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem; cursor: pointer;">
                                        <input type="checkbox" 
                                               ${list.packed[category][index] ? 'checked' : ''}
                                               onchange="travelFeatures.packing.toggleItem(${list.id}, '${category}', ${index})"
                                               style="width: 18px; height: 18px; cursor: pointer;">
                                        <span style="color: rgba(255,255,255,0.9); ${list.packed[category][index] ? 'text-decoration: line-through; opacity: 0.6;' : ''}">
                                            ${item}
                                        </span>
                                    </label>
                                `).join('')}
                                <div style="display: flex; gap: 0.5rem; margin-top: 0.5rem;">
                                    <input type="text" 
                                           id="custom-${list.id}-${category}"
                                           placeholder="Add item" 
                                           style="flex: 1; padding: 0.3rem 0.5rem; background: rgba(255,255,255,0.1); 
                                                  border: 1px solid rgba(255,255,255,0.2); border-radius: 5px; 
                                                  color: white; font-size: 0.9rem;">
                                    <button onclick="travelFeatures.packing.addCustomItem(${list.id}, '${category}')"
                                            style="background: rgba(255,210,63,0.2); border: none; color: var(--tuscan-gold); 
                                                   padding: 0.3rem 0.8rem; border-radius: 5px; cursor: pointer;">
                                        <i class="fas fa-plus"></i>
                                    </button>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `).join('');

        // Update progress for all lists
        this.lists.forEach(list => this.updateListProgress(list.id));
    }

    saveData() {
        localStorage.setItem('packingLists', JSON.stringify(this.lists));
    }
}

// Transport Guide Implementation
class TransportGuide {
    constructor() {
        this.transportData = {
            'Paris': {
                metro: { lines: 14, price: '€1.90', hours: '5:30 AM - 1:15 AM', app: 'Citymapper' },
                bus: { price: '€1.90', night: true, app: 'RATP' },
                bike: { service: 'Vélib', price: '€5/day', stations: 1400 },
                taxi: { app: 'Uber, Bolt, G7', airport: '€50-70' }
            },
            'Rome': {
                metro: { lines: 3, price: '€1.50', hours: '5:30 AM - 11:30 PM', app: 'Moovit' },
                bus: { price: '€1.50', night: true, app: 'Roma Mobilità' },
                bike: { service: 'Lime, Bird', price: '€0.25/min', electric: true },
                taxi: { app: 'FreeNow, Uber', airport: '€48 fixed' }
            },
            'Barcelona': {
                metro: { lines: 12, price: '€2.40', hours: '5:00 AM - 12:00 AM', app: 'TMB App' },
                bus: { price: '€2.40', night: true, app: 'TMB App' },
                bike: { service: 'Bicing', price: '€50/year', stations: 500 },
                taxi: { app: 'Cabify, FreeNow', airport: '€35-40' }
            }
        };
    }

    async loadData() {
        // Load any saved preferences
    }

    openModal() {
        const modal = this.createModal();
        document.body.appendChild(modal);
        modal.style.display = 'flex';
        this.renderGuide();
    }

    createModal() {
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content" style="max-width: 800px;">
                <div class="modal-header">
                    <h3><i class="fas fa-train"></i> City Transport Guide</h3>
                    <button onclick="this.closest('.modal').remove()" class="close-btn">&times;</button>
                </div>
                <div class="modal-body">
                    <!-- City Selector -->
                    <div style="margin-bottom: 2rem;">
                        <select id="city-select" class="form-control" onchange="travelFeatures.transport.renderGuide()">
                            <option value="">Select a city</option>
                            ${Object.keys(this.transportData).map(city => 
                                `<option value="${city}">${city}</option>`
                            ).join('')}
                        </select>
                    </div>

                    <!-- Transport Info -->
                    <div id="transport-info"></div>

                    <!-- General Tips -->
                    <div style="background: rgba(255,255,255,0.05); padding: 1.5rem; border-radius: 15px; margin-top: 2rem;">
                        <h4 style="color: white; margin-bottom: 1rem;">
                            <i class="fas fa-lightbulb"></i> Pro Tips
                        </h4>
                        <ul style="color: rgba(255,255,255,0.9); line-height: 1.8; margin: 0; padding-left: 1.5rem;">
                            <li>Download city transport apps before arrival</li>
                            <li>Buy multi-day passes for savings</li>
                            <li>Keep tickets until exiting - fines are common</li>
                            <li>Validate tickets before boarding</li>
                            <li>Rush hours: 7-9 AM and 5-7 PM</li>
                        </ul>
                    </div>
                </div>
            </div>
        `;
        return modal;
    }

    renderGuide() {
        const citySelect = document.getElementById('city-select');
        const infoContainer = document.getElementById('transport-info');
        
        if (!citySelect || !infoContainer) return;

        const city = citySelect.value;
        if (!city || !this.transportData[city]) {
            infoContainer.innerHTML = '<p style="color: rgba(255,255,255,0.6); text-align: center;">Select a city to see transport options</p>';
            return;
        }

        const data = this.transportData[city];
        
        infoContainer.innerHTML = `
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem;">
                <!-- Metro -->
                <div style="background: rgba(255,255,255,0.05); padding: 1.5rem; border-radius: 15px;">
                    <h5 style="color: var(--tuscan-gold); margin-bottom: 1rem;">
                        <i class="fas fa-subway"></i> Metro/Underground
                    </h5>
                    <div style="color: rgba(255,255,255,0.9); line-height: 1.8;">
                        <div><strong>Lines:</strong> ${data.metro.lines}</div>
                        <div><strong>Single Ticket:</strong> ${data.metro.price}</div>
                        <div><strong>Hours:</strong> ${data.metro.hours}</div>
                        <div><strong>App:</strong> ${data.metro.app}</div>
                    </div>
                </div>

                <!-- Bus -->
                <div style="background: rgba(255,255,255,0.05); padding: 1.5rem; border-radius: 15px;">
                    <h5 style="color: var(--coastal-mint); margin-bottom: 1rem;">
                        <i class="fas fa-bus"></i> Bus Network
                    </h5>
                    <div style="color: rgba(255,255,255,0.9); line-height: 1.8;">
                        <div><strong>Single Ticket:</strong> ${data.bus.price}</div>
                        <div><strong>Night Service:</strong> ${data.bus.night ? 'Available' : 'Limited'}</div>
                        <div><strong>App:</strong> ${data.bus.app}</div>
                        <div><strong>Tip:</strong> Same ticket works for metro</div>
                    </div>
                </div>

                <!-- Bike -->
                <div style="background: rgba(255,255,255,0.05); padding: 1.5rem; border-radius: 15px;">
                    <h5 style="color: var(--alpine-green); margin-bottom: 1rem;">
                        <i class="fas fa-bicycle"></i> Bike Sharing
                    </h5>
                    <div style="color: rgba(255,255,255,0.9); line-height: 1.8;">
                        <div><strong>Service:</strong> ${data.bike.service}</div>
                        <div><strong>Price:</strong> ${data.bike.price}</div>
                        ${data.bike.stations ? `<div><strong>Stations:</strong> ${data.bike.stations}+</div>` : ''}
                        ${data.bike.electric ? '<div><strong>Type:</strong> Electric scooters</div>' : ''}
                    </div>
                </div>

                <!-- Taxi/Ride-sharing -->
                <div style="background: rgba(255,255,255,0.05); padding: 1.5rem; border-radius: 15px;">
                    <h5 style="color: var(--sunset-orange); margin-bottom: 1rem;">
                        <i class="fas fa-taxi"></i> Taxi & Ride-sharing
                    </h5>
                    <div style="color: rgba(255,255,255,0.9); line-height: 1.8;">
                        <div><strong>Apps:</strong> ${data.taxi.app}</div>
                        <div><strong>Airport:</strong> ${data.taxi.airport}</div>
                        <div><strong>Tip:</strong> Uber works in most EU cities</div>
                    </div>
                </div>
            </div>
        `;
    }
}

// Emergency Info Implementation
class EmergencyInfo {
    constructor() {
        this.emergencyNumbers = {
            'EU': { police: '112', medical: '112', fire: '112' },
            'France': { police: '17', medical: '15', fire: '18' },
            'Italy': { police: '113', medical: '118', fire: '115' },
            'Spain': { police: '091', medical: '061', fire: '080' }
        };
        
        this.embassies = {
            'US': {
                'France': { phone: '+33 1 43 12 22 22', address: '2 Avenue Gabriel, 75008 Paris' },
                'Italy': { phone: '+39 06 46741', address: 'Via Vittorio Veneto 121, 00187 Rome' },
                'Spain': { phone: '+34 91 587 2200', address: 'Calle de Serrano 75, 28006 Madrid' }
            },
            'UK': {
                'France': { phone: '+33 1 44 51 31 00', address: '35 rue du Faubourg St Honoré, 75008 Paris' },
                'Italy': { phone: '+39 06 4220 0001', address: 'Via XX Settembre 80/a, 00187 Rome' },
                'Spain': { phone: '+34 91 714 6300', address: 'Torre Emperador Castellana, 28046 Madrid' }
            }
        };
    }

    openModal() {
        const modal = this.createModal();
        document.body.appendChild(modal);
        modal.style.display = 'flex';
    }

    createModal() {
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content" style="max-width: 800px;">
                <div class="modal-header">
                    <h3><i class="fas fa-shield-heart"></i> Emergency Information</h3>
                    <button onclick="this.closest('.modal').remove()" class="close-btn">&times;</button>
                </div>
                <div class="modal-body">
                    <!-- Emergency Numbers -->
                    <div style="background: rgba(255,107,53,0.15); padding: 1.5rem; border-radius: 15px; margin-bottom: 2rem;">
                        <h4 style="color: white; margin-bottom: 1rem;">🚨 Emergency Numbers</h4>
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem;">
                            <div style="text-align: center;">
                                <div style="font-size: 2rem; font-weight: 800; color: var(--sunset-orange);">112</div>
                                <div style="color: white;">EU Emergency</div>
                                <div style="color: rgba(255,255,255,0.6); font-size: 0.9rem;">Works in all EU countries</div>
                            </div>
                            ${Object.entries(this.emergencyNumbers).slice(1).map(([country, numbers]) => `
                                <div>
                                    <h5 style="color: var(--tuscan-gold); margin-bottom: 0.5rem;">${country}</h5>
                                    <div style="color: rgba(255,255,255,0.9); font-size: 0.9rem;">
                                        <div>Police: ${numbers.police}</div>
                                        <div>Medical: ${numbers.medical}</div>
                                        <div>Fire: ${numbers.fire}</div>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>

                    <!-- Embassy Contacts -->
                    <div style="background: rgba(255,255,255,0.05); padding: 1.5rem; border-radius: 15px; margin-bottom: 2rem;">
                        <h4 style="color: white; margin-bottom: 1rem;">🏛️ Embassy Contacts</h4>
                        <select id="embassy-country" class="form-control" style="margin-bottom: 1rem;" 
                                onchange="travelFeatures.emergency.showEmbassies()">
                            <option value="">Select your country</option>
                            <option value="US">United States</option>
                            <option value="UK">United Kingdom</option>
                        </select>
                        <div id="embassy-info"></div>
                    </div>

                    <!-- Safety Tips -->
                    <div style="background: rgba(255,255,255,0.05); padding: 1.5rem; border-radius: 15px;">
                        <h4 style="color: white; margin-bottom: 1rem;">🛡️ Safety Tips</h4>
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem;">
                            <div>
                                <h5 style="color: var(--coastal-mint); margin-bottom: 0.5rem;">
                                    <i class="fas fa-wallet"></i> Money Safety
                                </h5>
                                <ul style="color: rgba(255,255,255,0.9); font-size: 0.9rem; line-height: 1.6; margin: 0; padding-left: 1.5rem;">
                                    <li>Use ATMs inside banks</li>
                                    <li>Keep cash in multiple places</li>
                                    <li>Have backup cards</li>
                                    <li>Notify bank of travel</li>
                                </ul>
                            </div>
                            <div>
                                <h5 style="color: var(--alpine-green); margin-bottom: 0.5rem;">
                                    <i class="fas fa-id-card"></i> Documents
                                </h5>
                                <ul style="color: rgba(255,255,255,0.9); font-size: 0.9rem; line-height: 1.6; margin: 0; padding-left: 1.5rem;">
                                    <li>Scan passport & ID</li>
                                    <li>Email copies to yourself</li>
                                    <li>Keep originals in hotel safe</li>
                                    <li>Carry photocopies</li>
                                </ul>
                            </div>
                            <div>
                                <h5 style="color: var(--tuscan-gold); margin-bottom: 0.5rem;">
                                    <i class="fas fa-user-shield"></i> Personal Safety
                                </h5>
                                <ul style="color: rgba(255,255,255,0.9); font-size: 0.9rem; line-height: 1.6; margin: 0; padding-left: 1.5rem;">
                                    <li>Stay in well-lit areas</li>
                                    <li>Trust your instincts</li>
                                    <li>Keep valuables hidden</li>
                                    <li>Learn basic local phrases</li>
                                </ul>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        return modal;
    }

    showEmbassies() {
        const countrySelect = document.getElementById('embassy-country');
        const infoContainer = document.getElementById('embassy-info');
        
        if (!countrySelect || !infoContainer) return;

        const country = countrySelect.value;
        if (!country || !this.embassies[country]) {
            infoContainer.innerHTML = '';
            return;
        }

        const embassies = this.embassies[country];
        
        infoContainer.innerHTML = `
            <div style="display: grid; gap: 1rem;">
                ${Object.entries(embassies).map(([location, info]) => `
                    <div style="background: rgba(255,255,255,0.03); padding: 1rem; border-radius: 10px;">
                        <h5 style="color: var(--tuscan-gold); margin-bottom: 0.5rem;">${location}</h5>
                        <div style="color: rgba(255,255,255,0.9); font-size: 0.9rem;">
                            <div><i class="fas fa-phone"></i> ${info.phone}</div>
                            <div><i class="fas fa-map-marker-alt"></i> ${info.address}</div>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }
}

// Experiences Finder Implementation
class ExperiencesFinder {
    constructor() {
        this.experiences = {
            'Food Tours': [
                { name: 'Pasta Making in Rome', price: '€65', duration: '3 hours', rating: 4.9 },
                { name: 'Wine Tasting in Tuscany', price: '€85', duration: '4 hours', rating: 4.8 },
                { name: 'Tapas Tour Barcelona', price: '€45', duration: '3 hours', rating: 4.7 }
            ],
            'Cultural': [
                { name: 'Skip-the-Line Louvre', price: '€55', duration: '2 hours', rating: 4.6 },
                { name: 'Vatican Early Access', price: '€75', duration: '3 hours', rating: 4.9 },
                { name: 'Sagrada Familia Tour', price: '€50', duration: '1.5 hours', rating: 4.8 }
            ],
            'Adventure': [
                { name: 'Swiss Alps Paragliding', price: '€180', duration: '2 hours', rating: 5.0 },
                { name: 'Cinque Terre Hiking', price: '€95', duration: '6 hours', rating: 4.7 },
                { name: 'Iceland Glacier Walk', price: '€120', duration: '4 hours', rating: 4.9 }
            ]
        };
    }

    openModal() {
        const modal = this.createModal();
        document.body.appendChild(modal);
        modal.style.display = 'flex';
    }

    createModal() {
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content" style="max-width: 900px;">
                <div class="modal-header">
                    <h3><i class="fas fa-compass"></i> Local Experiences & Activities</h3>
                    <button onclick="this.closest('.modal').remove()" class="close-btn">&times;</button>
                </div>
                <div class="modal-body">
                    <!-- Search Bar -->
                    <div style="display: flex; gap: 1rem; margin-bottom: 2rem;">
                        <input type="text" class="form-control" placeholder="Search experiences..." style="flex: 1;">
                        <select class="form-control" style="width: 200px;">
                            <option value="">All Categories</option>
                            <option value="food">Food & Wine</option>
                            <option value="cultural">Cultural</option>
                            <option value="adventure">Adventure</option>
                            <option value="tours">Tours</option>
                        </select>
                    </div>

                    <!-- Experience Categories -->
                    ${Object.entries(this.experiences).map(([category, items]) => `
                        <div style="margin-bottom: 2rem;">
                            <h4 style="color: var(--tuscan-gold); margin-bottom: 1rem;">${category}</h4>
                            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1rem;">
                                ${items.map(exp => `
                                    <div style="background: rgba(255,255,255,0.05); padding: 1.5rem; border-radius: 15px; 
                                                cursor: pointer; transition: all 0.3s ease;"
                                         onmouseover="this.style.background='rgba(255,255,255,0.08)'"
                                         onmouseout="this.style.background='rgba(255,255,255,0.05)'">
                                        <h5 style="color: white; margin-bottom: 0.5rem;">${exp.name}</h5>
                                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                                            <span style="color: var(--coastal-mint); font-weight: 600; font-size: 1.1rem;">
                                                ${exp.price}
                                            </span>
                                            <span style="color: rgba(255,255,255,0.6); font-size: 0.9rem;">
                                                <i class="fas fa-clock"></i> ${exp.duration}
                                            </span>
                                        </div>
                                        <div style="display: flex; justify-content: space-between; align-items: center;">
                                            <div style="color: var(--tuscan-gold);">
                                                ${'★'.repeat(Math.floor(exp.rating))} ${exp.rating}
                                            </div>
                                            <button style="background: var(--accent-gradient); border: none; 
                                                           padding: 0.5rem 1rem; border-radius: 8px; color: var(--midnight-navy); 
                                                           font-weight: 600; cursor: pointer;"
                                                    onclick="travelFeatures.showToast('Booking feature coming soon!')">
                                                Book Now
                                            </button>
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    `).join('')}

                    <!-- Coming Soon Message -->
                    <div style="background: rgba(255,210,63,0.1); padding: 1.5rem; border-radius: 15px; text-align: center;">
                        <p style="color: var(--tuscan-gold); margin: 0;">
                            <i class="fas fa-rocket"></i> More experiences and real-time booking coming soon!
                        </p>
                    </div>
                </div>
            </div>
        `;
        return modal;
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.travelFeatures = new TravelFeatures();
});