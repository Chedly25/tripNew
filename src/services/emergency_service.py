"""
Emergency assistance service for travel safety and support.
"""
import os
import json
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import structlog
from ..core.database import get_database
from ..services.claude_ai_service import get_claude_service

logger = structlog.get_logger(__name__)

class EmergencyService:
    """Service for emergency assistance and travel safety."""
    
    def __init__(self):
        self.db = get_database()
        self.claude_service = get_claude_service()
        
        # Emergency contact numbers by country
        self.emergency_numbers = {
            'france': {'police': '17', 'medical': '15', 'fire': '18', 'general': '112'},
            'italy': {'police': '113', 'medical': '118', 'fire': '115', 'general': '112'},
            'spain': {'police': '091', 'medical': '061', 'fire': '080', 'general': '112'},
            'germany': {'police': '110', 'medical': '112', 'fire': '112', 'general': '112'},
            'switzerland': {'police': '117', 'medical': '144', 'fire': '118', 'general': '112'},
            'austria': {'police': '133', 'medical': '144', 'fire': '122', 'general': '112'},
            'netherlands': {'police': '112', 'medical': '112', 'fire': '112', 'general': '112'},
            'belgium': {'police': '101', 'medical': '100', 'fire': '100', 'general': '112'},
            'czech_republic': {'police': '158', 'medical': '155', 'fire': '150', 'general': '112'},
            'default': {'general': '112'}  # EU standard
        }
        
        # Embassy contact information (simplified)
        self.embassy_info = {
            'us_embassy': {
                'france': '+33-1-43-12-22-22',
                'italy': '+39-06-46741',
                'germany': '+49-30-8305-0',
                'spain': '+34-91-587-2200'
            },
            'uk_embassy': {
                'france': '+33-1-44-51-31-00',
                'italy': '+39-06-4220-0001',
                'germany': '+49-30-204-570',
                'spain': '+34-91-714-6300'
            }
        }
    
    async def handle_emergency_request(self, user_id: int, emergency_type: str, 
                                     location: str, description: str, 
                                     user_info: Dict = None) -> Dict:
        """Handle emergency assistance request."""
        try:
            # Log emergency request
            emergency_id = await self._log_emergency_request(
                user_id, emergency_type, location, description
            )
            
            # Get location-specific emergency info
            country = self._detect_country(location)
            emergency_contacts = self._get_emergency_contacts(country)
            
            # Get AI assistance for the emergency
            ai_response = await self._get_ai_emergency_assistance(
                emergency_type, location, description, user_info
            )
            
            # Create emergency response
            response = {
                'emergency_id': emergency_id,
                'immediate_actions': self._get_immediate_actions(emergency_type),
                'emergency_contacts': emergency_contacts,
                'ai_guidance': ai_response,
                'nearby_services': await self._find_nearby_services(location, emergency_type),
                'follow_up_actions': self._get_follow_up_actions(emergency_type),
                'timestamp': datetime.now().isoformat()
            }
            
            # Send alert to emergency contacts if configured
            await self._notify_emergency_contacts(user_id, emergency_type, location)
            
            return response
            
        except Exception as e:
            logger.error(f"Emergency handling failed: {e}")
            return {
                'error': 'Emergency service temporarily unavailable',
                'fallback_number': '112',  # EU emergency number
                'message': 'Please call 112 for immediate assistance'
            }
    
    async def get_safety_briefing(self, destination: str, route_type: str) -> Dict:
        """Get safety briefing for a destination."""
        try:
            # Get country-specific safety information
            country = self._detect_country(destination)
            
            # Get AI-powered safety briefing
            ai_briefing = await self._get_ai_safety_briefing(destination, route_type, country)
            
            return {
                'destination': destination,
                'country': country,
                'emergency_contacts': self._get_emergency_contacts(country),
                'safety_briefing': ai_briefing,
                'health_recommendations': self._get_health_recommendations(country),
                'driving_requirements': self._get_driving_requirements(country),
                'cultural_considerations': self._get_cultural_considerations(country),
                'common_scams': self._get_common_scams(country)
            }
            
        except Exception as e:
            logger.error(f"Safety briefing failed: {e}")
            return {'error': 'Safety briefing unavailable'}
    
    def setup_emergency_contacts(self, user_id: int, contacts: List[Dict]) -> Dict:
        """Setup emergency contacts for a user."""
        try:
            with self.db.get_connection() as conn:
                # Create emergency contacts table if not exists
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS emergency_contacts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        name TEXT NOT NULL,
                        phone TEXT NOT NULL,
                        email TEXT,
                        relationship TEXT,
                        is_primary BOOLEAN DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                ''')
                
                # Delete existing contacts
                conn.execute('DELETE FROM emergency_contacts WHERE user_id = ?', (user_id,))
                
                # Add new contacts
                for contact in contacts:
                    conn.execute('''
                        INSERT INTO emergency_contacts (user_id, name, phone, email, relationship, is_primary)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        user_id, contact['name'], contact['phone'], 
                        contact.get('email', ''), contact.get('relationship', ''),
                        contact.get('is_primary', False)
                    ))
                
                conn.commit()
                
                return {'success': True, 'message': 'Emergency contacts updated'}
                
        except Exception as e:
            logger.error(f"Emergency contacts setup failed: {e}")
            return {'success': False, 'error': 'Failed to setup emergency contacts'}
    
    def get_travel_health_info(self, destinations: List[str]) -> Dict:
        """Get health information for travel destinations."""
        health_info = {}
        
        for destination in destinations:
            country = self._detect_country(destination)
            health_info[destination] = {
                'vaccinations': self._get_vaccination_requirements(country),
                'health_risks': self._get_health_risks(country),
                'medical_facilities': self._get_medical_facilities_info(country),
                'insurance_recommendations': self._get_insurance_recommendations(country),
                'emergency_medical_number': self.emergency_numbers.get(country, {}).get('medical', '112')
            }
        
        return health_info
    
    async def _log_emergency_request(self, user_id: int, emergency_type: str, 
                                   location: str, description: str) -> str:
        """Log emergency request to database."""
        try:
            with self.db.get_connection() as conn:
                # Create emergency logs table if not exists
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS emergency_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        emergency_id TEXT UNIQUE NOT NULL,
                        user_id INTEGER NOT NULL,
                        emergency_type TEXT NOT NULL,
                        location TEXT NOT NULL,
                        description TEXT,
                        status TEXT DEFAULT 'active',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        resolved_at TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                ''')
                
                emergency_id = f"EMG_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{user_id}"
                
                conn.execute('''
                    INSERT INTO emergency_logs (emergency_id, user_id, emergency_type, location, description)
                    VALUES (?, ?, ?, ?, ?)
                ''', (emergency_id, user_id, emergency_type, location, description))
                
                conn.commit()
                return emergency_id
                
        except Exception as e:
            logger.error(f"Emergency logging failed: {e}")
            return f"EMG_FALLBACK_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    async def _get_ai_emergency_assistance(self, emergency_type: str, location: str, 
                                         description: str, user_info: Dict = None) -> str:
        """Get AI-powered emergency assistance."""
        try:
            prompt = f"""
            EMERGENCY ASSISTANCE REQUEST:
            Type: {emergency_type}
            Location: {location}
            Description: {description}
            User Info: {user_info or 'Not provided'}
            
            Please provide immediate, practical guidance for this emergency situation.
            Focus on:
            1. Immediate safety actions
            2. Who to contact
            3. What information to have ready
            4. Next steps to take
            
            Keep advice practical and location-specific.
            """
            
            messages = [{'role': 'user', 'content': prompt}]
            
            response = await self.claude_service._make_request(
                messages, 
                max_tokens=1000,
                system_prompt="You are an emergency assistance AI. Provide clear, actionable guidance for travel emergencies. Always prioritize safety and direct users to appropriate emergency services."
            )
            
            return response or "Contact local emergency services immediately. In EU countries, dial 112."
            
        except Exception as e:
            logger.error(f"AI emergency assistance failed: {e}")
            return "Contact local emergency services immediately. In EU countries, dial 112."
    
    async def _get_ai_safety_briefing(self, destination: str, route_type: str, country: str) -> str:
        """Get AI-powered safety briefing."""
        try:
            prompt = f"""
            Provide a comprehensive safety briefing for:
            Destination: {destination}
            Country: {country}
            Route Type: {route_type}
            
            Include:
            1. Current safety situation
            2. Common risks for travelers
            3. Precautions to take
            4. Areas or situations to avoid
            5. Local safety tips
            6. Cultural considerations for safety
            
            Keep advice current and practical.
            """
            
            messages = [{'role': 'user', 'content': prompt}]
            
            response = await self.claude_service._make_request(
                messages,
                max_tokens=1500,
                system_prompt="You are a travel safety expert. Provide accurate, up-to-date safety information for travelers."
            )
            
            return response or f"General safety precautions apply for {destination}. Stay aware of surroundings and follow local guidelines."
            
        except Exception as e:
            logger.error(f"AI safety briefing failed: {e}")
            return f"Safety briefing unavailable. Follow standard travel safety precautions for {destination}."
    
    def _detect_country(self, location: str) -> str:
        """Detect country from location string."""
        location_lower = location.lower()
        
        country_keywords = {
            'france': ['france', 'french', 'paris', 'lyon', 'marseille', 'nice', 'cannes'],
            'italy': ['italy', 'italian', 'rome', 'milan', 'venice', 'florence', 'naples'],
            'spain': ['spain', 'spanish', 'madrid', 'barcelona', 'valencia', 'seville'],
            'germany': ['germany', 'german', 'berlin', 'munich', 'hamburg', 'cologne'],
            'switzerland': ['switzerland', 'swiss', 'zurich', 'geneva', 'bern', 'basel'],
            'austria': ['austria', 'austrian', 'vienna', 'salzburg', 'innsbruck'],
            'netherlands': ['netherlands', 'dutch', 'amsterdam', 'rotterdam', 'hague'],
            'belgium': ['belgium', 'belgian', 'brussels', 'antwerp', 'ghent'],
            'czech_republic': ['czech', 'prague', 'brno', 'ostrava']
        }
        
        for country, keywords in country_keywords.items():
            if any(keyword in location_lower for keyword in keywords):
                return country
        
        return 'default'
    
    def _get_emergency_contacts(self, country: str) -> Dict:
        """Get emergency contact numbers for a country."""
        return self.emergency_numbers.get(country, self.emergency_numbers['default'])
    
    def _get_immediate_actions(self, emergency_type: str) -> List[str]:
        """Get immediate actions for emergency type."""
        actions = {
            'medical': [
                "Ensure your safety first",
                "Call local medical emergency number immediately",
                "Provide clear location information",
                "Stay with the injured person if safe to do so",
                "Have passport and insurance information ready"
            ],
            'accident': [
                "Move to safety if possible",
                "Call local emergency services",
                "Take photos if safe to do so",
                "Exchange information with other parties",
                "Contact your insurance company"
            ],
            'theft': [
                "Report to local police immediately",
                "Contact your bank to freeze cards",
                "Get a police report number",
                "Contact your embassy if passport stolen",
                "Keep copies of all documents"
            ],
            'breakdown': [
                "Pull over safely",
                "Turn on hazard lights",
                "Call roadside assistance",
                "Stay in vehicle if on busy road",
                "Have vehicle documents ready"
            ],
            'lost': [
                "Stay where you are if safe",
                "Use GPS on phone if available",
                "Call local emergency services if in danger",
                "Contact someone who knows your itinerary",
                "Look for tourist information centers"
            ]
        }
        
        return actions.get(emergency_type, [
            "Assess your immediate safety",
            "Call local emergency services (112 in EU)",
            "Provide clear location information",
            "Stay calm and follow official instructions"
        ])
    
    def _get_follow_up_actions(self, emergency_type: str) -> List[str]:
        """Get follow-up actions for emergency type."""
        actions = {
            'medical': [
                "Keep all medical records and receipts",
                "Contact travel insurance provider",
                "Follow up with your doctor at home",
                "Consider adjusting travel plans"
            ],
            'accident': [
                "File insurance claim promptly",
                "Get vehicle repairs documented",
                "Keep all receipts for expenses",
                "Review and update travel plans"
            ],
            'theft': [
                "Apply for replacement documents",
                "Monitor bank statements",
                "Update passwords for online accounts",
                "Consider additional security measures"
            ]
        }
        
        return actions.get(emergency_type, [
            "Document everything",
            "Contact relevant authorities",
            "Review travel insurance coverage",
            "Consider safety improvements"
        ])
    
    async def _find_nearby_services(self, location: str, emergency_type: str) -> List[Dict]:
        """Find nearby emergency services (simplified implementation)."""
        # This would integrate with Google Places API in a real implementation
        services = {
            'medical': ['Hospital', 'Pharmacy', 'Medical Center'],
            'accident': ['Police Station', 'Auto Repair', 'Car Rental'],
            'theft': ['Police Station', 'Embassy', 'Bank'],
            'breakdown': ['Auto Repair', 'Gas Station', 'Car Rental']
        }
        
        service_types = services.get(emergency_type, ['Police Station', 'Hospital'])
        
        return [
            {
                'name': f'{service_type} near {location}',
                'type': service_type,
                'note': 'Use local directory or ask locals for specific locations'
            }
            for service_type in service_types
        ]
    
    async def _notify_emergency_contacts(self, user_id: int, emergency_type: str, location: str):
        """Notify user's emergency contacts (placeholder for future SMS/email integration)."""
        try:
            with self.db.get_connection() as conn:
                contacts = conn.execute('''
                    SELECT * FROM emergency_contacts WHERE user_id = ? AND is_primary = 1
                ''', (user_id,)).fetchall()
                
                # In a real implementation, this would send SMS/email notifications
                logger.info(f"Would notify {len(contacts)} emergency contacts about {emergency_type} in {location}")
                
        except Exception as e:
            logger.error(f"Emergency contact notification failed: {e}")
    
    def _get_health_recommendations(self, country: str) -> List[str]:
        """Get health recommendations for a country."""
        recommendations = {
            'italy': ["Drink bottled water in some areas", "Sun protection essential", "Mosquito protection in summer"],
            'france': ["Standard European health precautions", "Tick protection in rural areas"],
            'spain': ["Sun protection essential", "Stay hydrated", "Be aware of jellyfish in coastal areas"],
            'default': ["Check with your doctor before travel", "Ensure routine vaccinations are up to date", "Consider travel insurance"]
        }
        
        return recommendations.get(country, recommendations['default'])
    
    def _get_driving_requirements(self, country: str) -> List[str]:
        """Get driving requirements for a country."""
        requirements = {
            'italy': ["International Driving Permit required", "ZTL zones in cities", "Autostrade tolls"],
            'france': ["UK/EU license valid", "Breathalyzer kit required", "High-vis vests mandatory"],
            'spain': ["International Driving Permit recommended", "Speed cameras common", "Parking restrictions in cities"],
            'default': ["Check local driving requirements", "International Driving Permit recommended", "Research local traffic laws"]
        }
        
        return requirements.get(country, requirements['default'])
    
    def _get_cultural_considerations(self, country: str) -> List[str]:
        """Get cultural safety considerations."""
        considerations = {
            'italy': ["Dress modestly in churches", "Be aware of pickpockets in tourist areas", "Siesta hours affect business"],
            'france': ["Learn basic French phrases", "Dining etiquette important", "Strike actions can affect transport"],
            'spain': ["Late dining hours", "Siesta affects business hours", "Regional languages important"],
            'default': ["Research local customs", "Dress appropriately", "Be respectful of local traditions"]
        }
        
        return considerations.get(country, considerations['default'])
    
    def _get_common_scams(self, country: str) -> List[str]:
        """Get common travel scams for a country."""
        scams = {
            'italy': ["Fake petition signers", "Overcharging in restaurants", "ATM skimming"],
            'france': ["Gold ring scam", "Friendship bracelet scam", "Metro pickpocketing"],
            'spain': ["Fake police checkpoints", "Distraction theft", "Overpriced tourist menus"],
            'default': ["ATM skimming", "Overcharging tourists", "Distraction theft", "Fake officials"]
        }
        
        return scams.get(country, scams['default'])
    
    def _get_vaccination_requirements(self, country: str) -> List[str]:
        """Get vaccination requirements (simplified)."""
        return ["Routine vaccinations up to date", "Check with healthcare provider", "No special requirements for most EU countries"]
    
    def _get_health_risks(self, country: str) -> List[str]:
        """Get health risks for a country."""
        return ["Standard European health risks", "Seasonal allergies possible", "Food safety generally good"]
    
    def _get_medical_facilities_info(self, country: str) -> str:
        """Get medical facilities information."""
        return f"Good medical facilities available in {country}. EU health insurance card valid."
    
    def _get_insurance_recommendations(self, country: str) -> List[str]:
        """Get insurance recommendations."""
        return ["Comprehensive travel insurance recommended", "Check coverage for activities", "Keep insurance documents accessible"]

# Global service instance
_emergency_service = None

def get_emergency_service() -> EmergencyService:
    """Get global emergency service instance."""
    global _emergency_service
    if _emergency_service is None:
        _emergency_service = EmergencyService()
    return _emergency_service