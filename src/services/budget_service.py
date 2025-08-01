"""
Budget tracking and expense splitting service for trips.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import structlog
from ..core.database import get_database
from ..core.exceptions import ValidationError, ServiceError

logger = structlog.get_logger(__name__)


class BudgetService:
    """Handles budget tracking and expense splitting for trips."""
    
    def __init__(self):
        self.db = get_database()
    
    def add_expense(self, trip_id: int, user_id: int, expense_data: Dict[str, Any]) -> int:
        """Add a new expense to a trip."""
        try:
            # Validate required fields
            required_fields = ['category', 'description', 'amount', 'paid_by']
            for field in required_fields:
                if field not in expense_data:
                    raise ValidationError(f"Missing required field: {field}")
            
            # Handle expense splitting
            split_with = expense_data.get('split_with', [])
            if split_with and not isinstance(split_with, list):
                raise ValidationError("split_with must be a list of user IDs")
            
            with self.db.get_connection() as conn:
                cursor = conn.execute('''
                    INSERT INTO trip_expenses (
                        trip_id, user_id, expense_category, description, 
                        amount, currency, paid_by, split_with, receipt_url, expense_date
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    trip_id,
                    user_id,
                    expense_data['category'],
                    expense_data['description'],
                    expense_data['amount'],
                    expense_data.get('currency', 'EUR'),
                    expense_data['paid_by'],
                    json.dumps(split_with) if split_with else None,
                    expense_data.get('receipt_url'),
                    expense_data.get('expense_date', datetime.now())
                ))
                
                expense_id = cursor.lastrowid
                conn.commit()
                
                logger.info(f"Expense added successfully", expense_id=expense_id, trip_id=trip_id)
                return expense_id
                
        except Exception as e:
            logger.error(f"Failed to add expense: {e}")
            raise ServiceError(f"Failed to add expense: {str(e)}")
    
    def get_trip_expenses(self, trip_id: int) -> List[Dict[str, Any]]:
        """Get all expenses for a trip."""
        try:
            with self.db.get_connection() as conn:
                expenses = conn.execute('''
                    SELECT e.*, u.username as paid_by_name, u.profile_picture
                    FROM trip_expenses e
                    JOIN users u ON e.paid_by = u.id
                    WHERE e.trip_id = ?
                    ORDER BY e.expense_date DESC
                ''', (trip_id,)).fetchall()
                
                result = []
                for expense in expenses:
                    expense_dict = dict(expense)
                    # Parse JSON fields
                    if expense_dict.get('split_with'):
                        expense_dict['split_with'] = json.loads(expense_dict['split_with'])
                    result.append(expense_dict)
                
                return result
                
        except Exception as e:
            logger.error(f"Failed to get expenses: {e}")
            raise ServiceError(f"Failed to get expenses: {str(e)}")
    
    def calculate_trip_budget_summary(self, trip_id: int) -> Dict[str, Any]:
        """Calculate budget summary including splits and balances."""
        try:
            expenses = self.get_trip_expenses(trip_id)
            
            # Calculate totals by category
            category_totals = {}
            user_paid = {}
            user_owes = {}
            
            for expense in expenses:
                # Add to category totals
                category = expense['expense_category']
                amount = expense['amount']
                category_totals[category] = category_totals.get(category, 0) + amount
                
                # Track who paid
                paid_by = expense['paid_by']
                user_paid[paid_by] = user_paid.get(paid_by, 0) + amount
                
                # Calculate splits
                split_with = expense.get('split_with', [])
                if split_with:
                    # Include the payer in the split
                    all_participants = split_with + [paid_by]
                    split_amount = amount / len(all_participants)
                    
                    for participant in split_with:
                        if participant != paid_by:
                            user_owes[participant] = user_owes.get(participant, 0) + split_amount
            
            # Calculate net balances
            balances = {}
            all_users = set(user_paid.keys()) | set(user_owes.keys())
            
            for user_id in all_users:
                paid = user_paid.get(user_id, 0)
                owes = user_owes.get(user_id, 0)
                balances[user_id] = paid - owes
            
            # Get total spent
            total_spent = sum(category_totals.values())
            
            # Get user details for balances
            with self.db.get_connection() as conn:
                user_details = {}
                for user_id in all_users:
                    user = conn.execute('''
                        SELECT id, username, profile_picture 
                        FROM users WHERE id = ?
                    ''', (user_id,)).fetchone()
                    if user:
                        user_details[user_id] = dict(user)
            
            return {
                'total_spent': total_spent,
                'category_breakdown': category_totals,
                'user_balances': balances,
                'user_details': user_details,
                'expense_count': len(expenses),
                'currency': 'EUR'  # Default currency
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate budget summary: {e}")
            raise ServiceError(f"Failed to calculate budget summary: {str(e)}")
    
    def settle_balance(self, trip_id: int, from_user: int, to_user: int, amount: float) -> int:
        """Record a balance settlement between users."""
        try:
            settlement_data = {
                'category': 'settlement',
                'description': f'Balance settlement',
                'amount': amount,
                'paid_by': from_user,
                'split_with': []
            }
            
            return self.add_expense(trip_id, from_user, settlement_data)
            
        except Exception as e:
            logger.error(f"Failed to settle balance: {e}")
            raise ServiceError(f"Failed to settle balance: {str(e)}")
    
    def get_expense_categories(self) -> List[str]:
        """Get standard expense categories."""
        return [
            'transport',
            'accommodation', 
            'food',
            'activities',
            'shopping',
            'entertainment',
            'fuel',
            'tolls',
            'parking',
            'other'
        ]
    
    def update_expense(self, expense_id: int, user_id: int, update_data: Dict[str, Any]) -> bool:
        """Update an existing expense."""
        try:
            allowed_fields = ['description', 'amount', 'category', 'receipt_url']
            update_fields = []
            update_values = []
            
            for field in allowed_fields:
                if field in update_data:
                    update_fields.append(f"{field} = ?")
                    update_values.append(update_data[field])
            
            if not update_fields:
                return False
            
            update_values.extend([expense_id, user_id])
            
            with self.db.get_connection() as conn:
                cursor = conn.execute(f'''
                    UPDATE trip_expenses 
                    SET {', '.join(update_fields)}
                    WHERE id = ? AND user_id = ?
                ''', update_values)
                
                success = cursor.rowcount > 0
                conn.commit()
                return success
                
        except Exception as e:
            logger.error(f"Failed to update expense: {e}")
            raise ServiceError(f"Failed to update expense: {str(e)}")
    
    def delete_expense(self, expense_id: int, user_id: int) -> bool:
        """Delete an expense."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.execute('''
                    DELETE FROM trip_expenses 
                    WHERE id = ? AND user_id = ?
                ''', (expense_id, user_id))
                
                success = cursor.rowcount > 0
                conn.commit()
                return success
                
        except Exception as e:
            logger.error(f"Failed to delete expense: {e}")
            raise ServiceError(f"Failed to delete expense: {str(e)}")