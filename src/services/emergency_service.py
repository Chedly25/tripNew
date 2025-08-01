"""
Enhanced emergency assistance network service.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import structlog
from src.core.database import get_database
from src.core.exceptions import ValidationError, ServiceError

logger = structlog.get_logger(__name__)


class EmergencyService:
    """Handles emergency assistance and safety information."""
    
    def __init__(self):
        self.db = get_database()
        self._populate_emergency_contacts()
    
    def _populate_emergency_contacts(self):
        """Populate emergency contacts database with European data."""
        try:
            emergency_data = {
                'France': [
                    {'service_type': 'emergency_all', 'service_name': 'Emergency Services', 'phone': '112', 'languages': ['French', 'English']},
                    {'service_type': 'police', 'service_name': 'Police', 'phone': '17', 'languages': ['French']},
                    {'service_type': 'medical', 'service_name': 'SAMU (Medical Emergency)', 'phone': '15', 'languages': ['French']},
                    {'service_type': 'fire', 'service_name': 'Fire Department', 'phone': '18', 'languages': ['French']},
                    {'service_type': 'roadside', 'service_name': 'Roadside Assistance', 'phone': '0800 05 15 15', 'languages': ['French', 'English']},
                    {'service_type': 'embassy', 'service_name': 'US Embassy Paris', 'phone': '+33 1 43 12 22 22', 'address': '2 Avenue Gabriel, 75008 Paris', 'languages': ['English']},
                    {'service_type': 'embassy', 'service_name': 'UK Embassy Paris', 'phone': '+33 1 44 51 31 00', 'address': '35 Rue du Faubourg Saint-Honoré, 75008 Paris', 'languages': ['English']},
                ],
                'Germany': [
                    {'service_type': 'emergency_all', 'service_name': 'Emergency Services', 'phone': '112', 'languages': ['German', 'English']},
                    {'service_type': 'police', 'service_name': 'Police', 'phone': '110', 'languages': ['German']},
                    {'service_type': 'medical', 'service_name': 'Medical Emergency', 'phone': '112', 'languages': ['German', 'English']},
                    {'service_type': 'roadside', 'service_name': 'ADAC Roadside', 'phone': '+49 180 2 22 22 22', 'languages': ['German', 'English']},
                    {'service_type': 'embassy', 'service_name': 'US Embassy Berlin', 'phone': '+49 30 8305-0', 'address': 'Clayallee 170, 14195 Berlin', 'languages': ['English']},
                ],
                'Italy': [
                    {'service_type': 'emergency_all', 'service_name': 'Emergency Services', 'phone': '112', 'languages': ['Italian', 'English']},
                    {'service_type': 'police', 'service_name': 'Carabinieri', 'phone': '112', 'languages': ['Italian']},
                    {'service_type': 'police', 'service_name': 'State Police', 'phone': '113', 'languages': ['Italian']},
                    {'service_type': 'medical', 'service_name': 'Medical Emergency', 'phone': '118', 'languages': ['Italian']},
                    {'service_type': 'fire', 'service_name': 'Fire Brigade', 'phone': '115', 'languages': ['Italian']},
                    {'service_type': 'roadside', 'service_name': 'ACI Roadside', 'phone': '803 116', 'languages': ['Italian', 'English']},
                ],
                'Spain': [
                    {'service_type': 'emergency_all', 'service_name': 'Emergency Services', 'phone': '112', 'languages': ['Spanish', 'English']},
                    {'service_type': 'police', 'service_name': 'National Police', 'phone': '091', 'languages': ['Spanish']},
                    {'service_type': 'police', 'service_name': 'Civil Guard', 'phone': '062', 'languages': ['Spanish']},
                    {'service_type': 'medical', 'service_name': 'Medical Emergency', 'phone': '061', 'languages': ['Spanish']},
                    {'service_type': 'roadside', 'service_name': 'RACE Roadside', 'phone': '902 40 45 45', 'languages': ['Spanish', 'English']},
                ],
                'Netherlands': [
                    {'service_type': 'emergency_all', 'service_name': 'Emergency Services', 'phone': '112', 'languages': ['Dutch', 'English']},
                    {'service_type': 'police', 'service_name': 'Police', 'phone': '0900-8844', 'languages': ['Dutch', 'English']},
                    {'service_type': 'roadside', 'service_name': 'ANWB Roadside', 'phone': '088 269 2222', 'languages': ['Dutch', 'English']},
                ],
                'Austria': [
                    {'service_type': 'emergency_all', 'service_name': 'Emergency Services', 'phone': '112', 'languages': ['German', 'English']},
                    {'service_type': 'police', 'service_name': 'Police', 'phone': '133', 'languages': ['German']},
                    {'service_type': 'medical', 'service_name': 'Medical Emergency', 'phone': '144', 'languages': ['German']},
                    {'service_type': 'fire', 'service_name': 'Fire Department', 'phone': '122', 'languages': ['German']},
                    {'service_type': 'roadside', 'service_name': 'ÖAMTC Roadside', 'phone': '120', 'languages': ['German', 'English']},
                ]
            }
            
            with self.db.get_connection() as conn:
                # Check if data already exists
                existing = conn.execute('SELECT COUNT(*) FROM emergency_contacts').fetchone()[0]
                if existing > 0:
                    return  # Data already populated
                
                # Insert emergency contacts
                for country, contacts in emergency_data.items():
                    for contact in contacts:
                        conn.execute('''
                            INSERT INTO emergency_contacts (
                                country, service_type, service_name, phone_number,
                                address, languages, notes
                            ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            country,
                            contact['service_type'],
                            contact['service_name'],
                            contact['phone'],
                            contact.get('address'),
                            json.dumps(contact.get('languages', [])),
                            contact.get('notes')
                        ))
                
                conn.commit()
                logger.info("Emergency contacts populated successfully")
                
        except Exception as e:
            logger.error(f"Failed to populate emergency contacts: {e}")
    
    def get_emergency_contacts(self, country: str = None, service_type: str = None) -> List[Dict[str, Any]]:
        """Get emergency contacts for a country or service type."""
        try:
            query = 'SELECT * FROM emergency_contacts WHERE 1=1'
            params = []
            
            if country:
                query += ' AND country = ?'
                params.append(country)
            
            if service_type:
                query += ' AND service_type = ?'
                params.append(service_type)
            
            query += ' ORDER BY service_type, service_name'
            
            with self.db.get_connection() as conn:
                contacts = conn.execute(query, params).fetchall()
                
                result = []
                for contact in contacts:
                    contact_dict = dict(contact)
                    if contact_dict.get('languages'):
                        contact_dict['languages'] = json.loads(contact_dict['languages'])
                    result.append(contact_dict)
                
                return result
                
        except Exception as e:
            logger.error(f"Failed to get emergency contacts: {e}")
            raise ServiceError(f"Failed to get emergency contacts: {str(e)}")
    
    def get_nearest_emergency_services(self, latitude: float, longitude: float, 
                                     service_type: str = None) -> List[Dict[str, Any]]:
        """Get nearest emergency services based on location."""
        try:
            # In production, this would use geolocation APIs
            # For now, we'll determine country based on coordinates and return relevant contacts
            country = self._determine_country_from_coordinates(latitude, longitude)
            
            if country:
                contacts = self.get_emergency_contacts(country, service_type)
                
                # Add estimated response times and additional info
                for contact in contacts:
                    contact['estimated_response_time'] = self._estimate_response_time(
                        contact['service_type'], latitude, longitude
                    )
                    contact['available_24_7'] = contact['service_type'] in [
                        'emergency_all', 'police', 'medical', 'fire'
                    ]
                
                return contacts
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to get nearest emergency services: {e}")
            raise ServiceError(f"Failed to get nearest emergency services: {str(e)}")
    
    def _determine_country_from_coordinates(self, lat: float, lon: float) -> Optional[str]:
        """Determine country from coordinates (simplified)."""
        # Simplified country detection - in production use proper geocoding
        if 41.0 <= lat <= 51.0 and -5.0 <= lon <= 10.0:
            if 42.0 <= lat <= 51.5 and -5.0 <= lon <= 8.0:
                return 'France'
            elif 47.0 <= lat <= 55.0 and 6.0 <= lon <= 15.0:
                return 'Germany'
            elif 36.0 <= lat <= 47.0 and 6.0 <= lon <= 19.0:
                return 'Italy'
            elif 36.0 <= lat <= 44.0 and -10.0 <= lon <= 5.0:
                return 'Spain'
            elif 50.0 <= lat <= 54.0 and 3.0 <= lon <= 7.0:
                return 'Netherlands'
            elif 46.0 <= lat <= 49.0 and 9.0 <= lon <= 17.0:
                return 'Austria'
        
        return None
    
    def _estimate_response_time(self, service_type: str, lat: float, lon: float) -> str:
        """Estimate emergency response time based on service type and location."""
        # Simplified estimation - in production use real-time data
        if service_type == 'police':
            return '5-15 minutes'
        elif service_type == 'medical':
            return '8-20 minutes'
        elif service_type == 'fire':
            return '6-18 minutes'
        elif service_type == 'roadside':
            return '30-90 minutes'
        else:
            return 'Variable'
    
    def create_emergency_alert(self, user_id: int, alert_data: Dict[str, Any]) -> int:
        """Create an emergency alert for a user."""
        try:
            required_fields = ['alert_type', 'location', 'message']
            for field in required_fields:
                if field not in alert_data:
                    raise ValidationError(f"Missing required field: {field}")
            
            with self.db.get_connection() as conn:
                cursor = conn.execute('''
                    INSERT INTO travel_alerts (
                        user_id, alert_type, title, message, trip_id
                    ) VALUES (?, ?, ?, ?, ?)
                ''', (
                    user_id,
                    alert_data['alert_type'],
                    alert_data.get('title', 'Emergency Alert'),
                    alert_data['message'],
                    alert_data.get('trip_id')
                ))
                
                alert_id = cursor.lastrowid
                conn.commit()
                
                # Log the emergency alert
                logger.warning(f"Emergency alert created", 
                             alert_id=alert_id, 
                             user_id=user_id, 
                             alert_type=alert_data['alert_type'])
                
                return alert_id
                
        except Exception as e:
            logger.error(f"Failed to create emergency alert: {e}")
            raise ServiceError(f"Failed to create emergency alert: {str(e)}")
    
    def get_safety_tips(self, country: str, travel_type: str = 'road_trip') -> Dict[str, Any]:
        """Get safety tips for a specific country and travel type."""
        try:
            general_tips = [
                "Keep emergency contacts saved in your phone",
                "Share your itinerary with someone at home",
                "Keep copies of important documents",
                "Have local currency for emergencies",
                "Know the local emergency number (112 in EU)",
                "Keep your phone charged and carry a power bank"
            ]
            
            road_trip_tips = [
                "Check your vehicle before long drives",
                "Keep a roadside emergency kit",
                "Plan rest stops every 2 hours",
                "Avoid driving when tired",
                "Keep fuel tank above 1/4 full",
                "Have offline maps downloaded"
            ]
            
            country_specific = self._get_country_specific_tips(country)
            
            return {
                'country': country,
                'general_safety': general_tips,
                'road_trip_safety': road_trip_tips if travel_type == 'road_trip' else [],
                'country_specific': country_specific,
                'emergency_number': '112',  # EU standard
                'important_phrases': self._get_emergency_phrases(country)
            }
            
        except Exception as e:
            logger.error(f"Failed to get safety tips: {e}")
            raise ServiceError(f"Failed to get safety tips: {str(e)}")
    
    def _get_country_specific_tips(self, country: str) -> List[str]:
        """Get country-specific safety tips."""
        tips_by_country = {
            'France': [
                "Carry ID at all times",
                "Be aware of tourist scams in major cities",
                "Respect local driving rules and speed limits",
                "Many businesses close for lunch 12-2pm"
            ],
            'Germany': [
                "Autobahn has no general speed limit but recommended 130 km/h",
                "Strict environmental zones in cities require special stickers",
                "Sunday shopping is generally not available",
                "Punctuality is highly valued"
            ],
            'Italy': [
                "ZTL zones in city centers require permits",
                "Siesta hours: many shops close 1-4pm",
                "Dress codes enforced in religious sites",
                "Watch for pickpockets in tourist areas"
            ],
            'Spain': [
                "Siesta hours: 2-5pm many businesses closed",
                "Dinner is typically late (9-11pm)",
                "Be cautious of bag snatching in tourist areas",
                "Respect local customs and traditions"
            ],
            'Netherlands': [
                "Watch out for cyclists everywhere",
                "Parking in city centers is expensive",
                "Most people speak excellent English",
                "Coffee shops have specific rules"
            ],
            'Austria': [
                "Vignette required for highway driving",
                "Mountain weather can change quickly",
                "Respect quiet hours (typically 10pm-6am)",
                "Tipping 5-10% is customary"
            ]
        }
        
        return tips_by_country.get(country, [])
    
    def _get_emergency_phrases(self, country: str) -> Dict[str, str]:
        """Get essential emergency phrases in local language."""
        phrases_by_country = {
            'France': {
                'Help': 'Au secours',
                'Emergency': 'Urgence',
                'Call the police': 'Appelez la police',
                'I need a doctor': 'J\'ai besoin d\'un médecin',
                'I don\'t speak French': 'Je ne parle pas français'
            },
            'Germany': {
                'Help': 'Hilfe',
                'Emergency': 'Notfall',
                'Call the police': 'Rufen Sie die Polizei',
                'I need a doctor': 'Ich brauche einen Arzt',
                'I don\'t speak German': 'Ich spreche kein Deutsch'
            },
            'Italy': {
                'Help': 'Aiuto',
                'Emergency': 'Emergenza',
                'Call the police': 'Chiama la polizia',
                'I need a doctor': 'Ho bisogno di un medico',
                'I don\'t speak Italian': 'Non parlo italiano'
            },
            'Spain': {
                'Help': 'Ayuda',
                'Emergency': 'Emergencia',
                'Call the police': 'Llama a la policía',
                'I need a doctor': 'Necesito un médico',
                'I don\'t speak Spanish': 'No hablo español'
            },
            'Netherlands': {
                'Help': 'Help',
                'Emergency': 'Noodgeval',
                'Call the police': 'Bel de politie',
                'I need a doctor': 'Ik heb een dokter nodig',
                'I don\'t speak Dutch': 'Ik spreek geen Nederlands'
            },
            'Austria': {
                'Help': 'Hilfe',
                'Emergency': 'Notfall',
                'Call the police': 'Rufen Sie die Polizei',
                'I need a doctor': 'Ich brauche einen Arzt',
                'I don\'t speak German': 'Ich spreche kein Deutsch'
            }
        }
        
        return phrases_by_country.get(country, {})
    
    def get_travel_advisories(self, country: str) -> Dict[str, Any]:
        """Get current travel advisories for a country."""
        try:
            # In production, this would fetch real-time data from government APIs
            return {
                'country': country,
                'last_updated': datetime.now().isoformat(),
                'overall_risk': 'Low',  # Low, Medium, High
                'advisories': [
                    {
                        'type': 'General',
                        'level': 'Standard precautions',
                        'message': 'Exercise normal precautions when traveling'
                    }
                ],
                'health_notices': [],
                'security_alerts': [],
                'entry_requirements': {
                    'passport_required': True,
                    'visa_required': False,  # For EU citizens
                    'covid_restrictions': 'None currently'
                },
                'source': 'Government Travel Advisory',
                'source_url': f'https://travel.state.gov/content/travel/en/traveladvisories/traveladvisories/{country.lower()}.html'
            }
            
        except Exception as e:
            logger.error(f"Failed to get travel advisories: {e}")
            raise ServiceError(f"Failed to get travel advisories: {str(e)}")
    
    def send_emergency_notification(self, user_id: int, emergency_data: Dict[str, Any]) -> bool:
        """Send emergency notification to emergency contacts."""
        try:
            # In production, this would integrate with SMS/email services
            # For now, we'll log the emergency and create an alert
            
            alert_data = {
                'alert_type': 'emergency',
                'title': 'Emergency Notification Sent',
                'message': f"Emergency alert sent: {emergency_data.get('message', 'Emergency situation')}",
                'location': emergency_data.get('location'),
                'trip_id': emergency_data.get('trip_id')
            }
            
            alert_id = self.create_emergency_alert(user_id, alert_data)
            
            logger.critical(f"Emergency notification sent", 
                          user_id=user_id, 
                          alert_id=alert_id,
                          emergency_data=emergency_data)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send emergency notification: {e}")
            return False