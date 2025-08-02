"""
AI-powered City Description Service

Generates rich, contextual descriptions for intermediate cities using AI.
Provides personalized descriptions based on travel preferences and route context.
"""
import os
import asyncio
import json
from typing import Dict, List, Optional
from dataclasses import dataclass
import structlog

from ..core.models import City, TripRequest

logger = structlog.get_logger(__name__)


@dataclass
class CityDescription:
    """Comprehensive city description with multiple facets."""
    city_name: str
    short_description: str      # 1-2 sentences
    detailed_description: str   # 2-3 paragraphs
    highlights: List[str]       # Key attractions/features
    best_for: List[str]        # What type of travelers would love this
    hidden_gems: List[str]     # Local secrets
    practical_info: str       # Transportation, timing, etc.
    why_visit_reason: str     # Compelling reason for this route
    photo_keywords: List[str] # For finding representative images


class CityDescriptionService:
    """AI-powered service for generating rich city descriptions."""
    
    def __init__(self):
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        self.description_cache: Dict[str, CityDescription] = {}
        self.predefined_descriptions = self._load_predefined_descriptions()
        
    def _load_predefined_descriptions(self) -> Dict[str, CityDescription]:
        """Load high-quality predefined descriptions for key cities."""
        return {
            'pietrasanta': CityDescription(
                city_name="Pietrasanta",
                short_description="A captivating Tuscan town where Renaissance artistry meets contemporary sculpture, nestled between marble quarries and sandy beaches.",
                detailed_description="Known as the 'Little Athens' of Tuscany, Pietrasanta has been a magnet for artists and sculptors for centuries. This enchanting town sits in the shadow of the Apuan Alps, where Michelangelo himself once selected marble for his masterpieces. Today, the medieval streets buzz with contemporary energy as international artists work alongside local craftsmen in historic workshops. The town square, dominated by the striking Duomo, serves as an open-air gallery where bronze and marble sculptures create an ever-changing exhibition. Beyond art, Pietrasanta offers authentic Tuscan cuisine in charming trattorias and easy access to the glamorous beaches of Forte dei Marmi just minutes away.",
                highlights=["Historic marble workshops", "Contemporary sculpture galleries", "Medieval cathedral square", "Artists' studios and foundries"],
                best_for=["Art enthusiasts", "Culture seekers", "Authentic Italy lovers", "Beach and mountain combination"],
                hidden_gems=["Gipsoteca Bartolini sculpture museum", "Local marble artisan workshops", "Sunset views from Rocca di Sala"],
                practical_info="Perfect 2-3 hour stop between French Riviera and Florence. Easy parking in town center, walkable historic district.",
                why_visit_reason="Experience where Michelangelo's marble meets modern artistry in an authentic Tuscan setting.",
                photo_keywords=["marble sculptures", "tuscan town square", "art workshops", "cathedral facade"]
            ),
            
            'barga': CityDescription(
                city_name="Barga",
                short_description="A hilltop medieval gem offering sweeping valley views and an unexpected Scottish connection in the heart of Tuscany.",
                detailed_description="Perched dramatically on a hillside in the Garfagnana valley, Barga reveals one of Tuscany's most intriguing stories. This perfectly preserved medieval town, with its maze of stone streets and stunning Romanesque cathedral, harbors a surprising secret: it's known as the most Scottish town in Italy. Waves of emigration to Scotland in the 19th century created lasting bonds, celebrated today in the town's Scottish heritage museum and annual festivals. The views from Barga are breathtaking – the Apuan Alps rise majestically to the west while the green Serchio valley unfolds below. The town's cultural life thrives with opera festivals, jazz concerts, and art exhibitions that attract visitors from across Europe who come to experience this unique blend of Italian beauty and Scottish spirit.",
                highlights=["Medieval cathedral with stunning views", "Scottish heritage museum", "Panoramic Apuan Alps vistas", "Opera and jazz festivals"],
                best_for=["History buffs", "Cultural travelers", "Photography enthusiasts", "Unique story seekers"],
                hidden_gems=["Via di Borgo medieval passageways", "Local sagra food festivals", "Traditional puppet theater"],
                practical_info="Ideal day trip from Lucca (30 mins) or overnight stay. Limited parking near old town, short walk to center.",
                why_visit_reason="Discover Italy's most unexpected cultural fusion in a perfectly preserved medieval setting.",
                photo_keywords=["hilltop town", "medieval streets", "valley views", "romanesque cathedral"]
            ),
            
            'mantua': CityDescription(
                city_name="Mantua",
                short_description="A Renaissance jewel surrounded by pristine lakes, where ducal palaces and UNESCO heritage create an atmosphere of timeless elegance.",
                detailed_description="Rising from three artificial lakes like a fairy-tale vision, Mantua stands as one of Italy's most perfectly preserved Renaissance cities. This UNESCO World Heritage site was the seat of the powerful Gonzaga family for four centuries, who transformed it into a court of unparalleled artistic refinement. The vast Ducal Palace complex contains 500 rooms of frescoed chambers, including Mantegna's masterful Camera degli Sposi. The city's compact historic center reveals architectural treasures at every turn: the imposing Palazzo Te with its playful Mannerist frescoes, the romantic Basilica of Sant'Andrea designed by Alberti, and charming piazzas that have remained unchanged for centuries. Beyond the monuments, Mantua offers an intimate Italian experience – morning markets, traditional osterie serving regional specialties like tortelli di zucca, and evening strolls along the lakefront promenades.",
                highlights=["Ducal Palace with Mantegna frescoes", "Palazzo Te Renaissance villa", "Three surrounding lakes", "UNESCO historic center"],
                best_for=["Renaissance art lovers", "Architecture enthusiasts", "Romantic travelers", "Cultural immersion seekers"],
                hidden_gems=["Rotonda di San Lorenzo circular church", "Casa del Rigoletto", "Local tortelli di zucca pasta"],
                practical_info="Perfect overnight stop between Venice and Tuscany. 2 hours from Venice, excellent local restaurants.",
                why_visit_reason="Experience Renaissance splendor in an intimate lakeside setting away from tourist crowds.",
                photo_keywords=["renaissance palace", "lake reflections", "frescoed chambers", "historic squares"]
            ),
            
            'moustiers_sainte_marie': CityDescription(
                city_name="Moustiers-Sainte-Marie",
                short_description="A mystical Provençal village clinging to dramatic cliffs, famous for its pottery tradition and the legendary golden star suspended between rocks.",
                detailed_description="Cascading down limestone cliffs at the entrance to the spectacular Verdon Gorge, Moustiers-Sainte-Marie appears almost supernatural in its beauty. The village's most famous landmark is the mysterious golden star suspended on a chain between two rocky peaks – a tradition dating back to a Crusader's vow. Below this celestial guardian, narrow cobblestone streets wind past pottery workshops that have made Moustiers famous throughout Europe since the 17th century. The distinctive blue and white faience ceramics, adorned with hunting scenes and mythological figures, continue to be crafted using traditional techniques passed down through generations. A steep climb leads to the Notre-Dame-de-Beauvoir chapel, rewarding visitors with breathtaking views over the village's red-tiled roofs to the turquoise waters of Lac de Sainte-Croix beyond.",
                highlights=["Legendary golden star", "Traditional pottery workshops", "Notre-Dame-de-Beauvoir chapel", "Gorges du Verdon gateway"],
                best_for=["Pottery enthusiasts", "Dramatic scenery lovers", "Photography specialists", "Provence culture seekers"],
                hidden_gems=["Ancient pottery kilns", "Hidden village fountains", "Sunset star viewing spot"],
                practical_info="Essential stop before Gorges du Verdon. Limited parking, arrive early. Perfect for 2-3 hour visit.",
                why_visit_reason="Witness the magical intersection of artisan tradition and natural drama in deepest Provence.",
                photo_keywords=["cliff village", "golden star", "pottery workshops", "provencal rooftops"]
            ),
            
            'sisteron': CityDescription(
                city_name="Sisteron",
                short_description="The 'Gateway to Provence' commanded by an imposing citadel, where dramatic limestone cliffs meet lavender-scented valleys.",
                detailed_description="Guarding the narrow passage through the Alpes-de-Haute-Provence, Sisteron has earned its title as the 'Pearl of Haute-Provence' through centuries of strategic importance. The town's magnificent citadel, perched 400 meters above the Durance valley, offers some of the most spectacular views in southern France. This fortress, continuously reinforced from the 11th to 16th centuries, tells the story of France's tumultuous history through its ramparts and dungeons. Below the citadel, the old town's narrow streets reveal Gothic and Renaissance architecture, including the remarkable Notre-Dame-des-Pommiers cathedral with its distinctive Lombard bell tower. The surrounding landscape epitomizes Provence – rolling hills dotted with lavender fields, ancient olive groves, and the ever-present scent of wild herbs carried on the mistral wind.",
                highlights=["Medieval citadel with panoramic views", "Notre-Dame-des-Pommiers cathedral", "Historic ramparts and dungeons", "Lavender fields nearby"],
                best_for=["History enthusiasts", "Fortress explorers", "Scenic drive lovers", "Provence discoverers"],
                hidden_gems=["Underground citadel chambers", "Traditional Sunday markets", "Roman archaeological remains"],
                practical_info="Strategic stop between Alps and Mediterranean. Citadel visit takes 2 hours. Good restaurants in old town.",
                why_visit_reason="Command spectacular views from a fortress that has guarded Provence for a millennium.",
                photo_keywords=["mountain fortress", "limestone cliffs", "provencal landscape", "medieval ramparts"]
            ),
            
            'forte_dei_marmi': CityDescription(
                city_name="Forte dei Marmi",
                short_description="An exclusive Tuscan beach resort where marble heritage meets sophisticated seaside elegance and designer boutiques.",
                detailed_description="Named after the 18th-century fortress built to oversee marble shipments, Forte dei Marmi has evolved into one of Italy's most prestigious seaside destinations. This sophisticated resort town perfectly balances its industrial heritage with luxurious leisure – the same marble quarries that supplied Michelangelo now backdrop elegant beach clubs and designer villas. The town center revolves around the weekly market, a glamorous affair where high fashion meets local produce under the shadow of the historic fortress. Miles of pristine sandy beaches are divided into exclusive stabilimenti, each offering its own interpretation of Italian beach culture. Behind the shore, pine-shaded streets lead to designer boutiques, art galleries, and restaurants where Italian celebrities and international visitors mingle over exceptional Tuscan cuisine.",
                highlights=["Historic marble fortress", "Designer beach clubs", "Weekly luxury market", "Pine-shaded shopping streets"],
                best_for=["Luxury travelers", "Beach sophisticates", "Fashion enthusiasts", "Elegant leisure seekers"],
                hidden_gems=["Traditional marble workshops", "Art galleries in villa settings", "Aperitivo spots with sea views"],
                practical_info="Perfect beach break between Cinque Terre and Florence. Best May-September. Reserve beach club in advance.",
                why_visit_reason="Experience Italian beach culture at its most refined, where marble mountains meet Mediterranean elegance.",
                photo_keywords=["luxury beach", "marble fortress", "designer boutiques", "pine trees seaside"]
            ),
            
            'entrevaux': CityDescription(
                city_name="Entrevaux",
                short_description="A perfectly preserved medieval fortress town where Vauban's military architecture creates an impregnable citadel in the Alpine foothills.",
                detailed_description="Entrevaux stands as one of France's most complete examples of military architecture, a testament to the genius of Vauban, Louis XIV's master fortress designer. This remarkable walled town, built on a rocky spur above the Var River, has remained virtually unchanged since the 17th century. Massive ramparts encircle the entire settlement, while a dramatic zigzag path climbs 156 meters to the citadel perched on the summit. Within the walls, time seems suspended – ancient houses with their original facades line narrow streets that lead to the cathedral, built directly into the rock face. The town's strategic position on the former border between France and Savoy explains its formidable defenses, designed to withstand the longest sieges. Today, this living museum offers visitors the rare chance to experience authentic medieval military architecture in its pristine mountain setting.",
                highlights=["Complete Vauban fortifications", "Dramatic citadel climb", "Cathedral built into rock", "Original medieval streets"],
                best_for=["Military history fans", "Architecture enthusiasts", "Medieval atmosphere seekers", "Mountain fortress explorers"],
                hidden_gems=["Underground tunnels system", "Original defensive mechanisms", "Panoramic mountain views from ramparts"],
                practical_info="Steep citadel climb requires good fitness. 2-3 hours for full visit. Limited parking outside walls.",
                why_visit_reason="Walk through the most complete example of 17th-century military genius in an Alpine setting.",
                photo_keywords=["fortress walls", "mountain citadel", "medieval architecture", "defensive ramparts"]
            ),
            
            'volterra': CityDescription(
                city_name="Volterra",
                short_description="An ancient Etruscan hilltop city where alabaster artisans continue millennia-old traditions amid medieval towers and Roman ruins.",
                detailed_description="Perched on a dramatic plateau overlooking the Val di Cecina, Volterra guards 3,000 years of continuous history within its perfectly preserved medieval walls. This was once Velathri, one of the most important cities in the Etruscan confederation, and today's visitors can still explore the remarkably intact Roman theater and Etruscan necropolis. The city's fame as the alabaster capital of the world continues undiminished – workshops throughout the historic center showcase artisans sculpting the translucent stone using techniques passed down through countless generations. Volterra's brooding medieval atmosphere inspired Stephenie Meyer to set pivotal scenes of her Twilight saga here, but the city's real magic lies in its authentic Tuscan character. Narrow streets lead to stunning viewpoints over the surrounding countryside, while traditional restaurants serve wild boar and other regional specialties.",
                highlights=["Ancient Etruscan museum", "Working alabaster workshops", "Roman theater ruins", "Medieval towers and palazzi"],
                best_for=["Ancient history enthusiasts", "Craft art lovers", "Twilight saga fans", "Authentic Tuscany seekers"],
                hidden_gems=["Underground Etruscan cisterns", "Traditional alabaster carving techniques", "Sunset views from city walls"],
                practical_info="Perfect day trip from San Gimignano (30 mins) or Siena (1 hour). Park outside walls, walk to center.",
                why_visit_reason="Journey through 3,000 years of history while watching ancient crafts practiced in medieval workshops.",
                photo_keywords=["etruscan ruins", "alabaster workshop", "hilltop city", "medieval towers"]
            )
        }
    
    async def get_city_description(
        self, 
        city: City, 
        route_type: str = None, 
        trip_request: TripRequest = None
    ) -> CityDescription:
        """Get comprehensive description for a city, generating with AI if needed."""
        
        cache_key = f"{city.name.lower()}_{route_type or 'general'}"
        
        # Check cache first
        if cache_key in self.description_cache:
            return self.description_cache[cache_key]
        
        # Check predefined descriptions
        city_key = city.name.lower().replace(' ', '_').replace('-', '_')
        if city_key in self.predefined_descriptions:
            description = self.predefined_descriptions[city_key]
            self.description_cache[cache_key] = description
            return description
        
        # Generate with AI if API key is available
        if self.anthropic_api_key:
            try:
                description = await self._generate_ai_description(city, route_type, trip_request)
                self.description_cache[cache_key] = description
                return description
            except Exception as e:
                logger.warning(f"AI description generation failed: {e}")
        
        # Fallback to basic description
        description = self._generate_basic_description(city, route_type)
        self.description_cache[cache_key] = description
        return description
    
    async def _generate_ai_description(
        self, 
        city: City, 
        route_type: str = None, 
        trip_request: TripRequest = None
    ) -> CityDescription:
        """Generate rich description using Anthropic's Claude API."""
        
        # Create context-aware prompt
        prompt = f"""Create a rich, engaging description for {city.name} ({city.country}) as an intermediate stop on a European road trip.

City Context:
- Name: {city.name}
- Country: {city.country}
- Types/Characteristics: {', '.join(city.types) if city.types else 'charming destination'}
- Route Type: {route_type or 'scenic'} route

Please provide a JSON response with:
1. short_description: 1-2 compelling sentences capturing the city's essence
2. detailed_description: 2-3 paragraphs with rich detail, history, atmosphere, and what makes it special
3. highlights: Array of 4-5 top attractions or features
4. best_for: Array of 3-4 types of travelers who would love this place
5. hidden_gems: Array of 2-3 local secrets or lesser-known spots
6. practical_info: Brief practical travel advice (timing, parking, etc.)
7. why_visit_reason: One compelling sentence about why this city is perfect for this route
8. photo_keywords: Array of 4-5 keywords for finding representative photos

Focus on authentic experiences, local culture, and what makes this destination special for road trip travelers. Avoid generic tourist descriptions."""

        try:
            import anthropic
            
            client = anthropic.Anthropic(api_key=self.anthropic_api_key)
            
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parse the JSON response with error handling
            response_text = response.content[0].text
            
            # Clean the response text of any control characters
            import re
            cleaned_text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', response_text)
            
            # Try to extract JSON if it's wrapped in markdown code blocks
            if '```json' in cleaned_text:
                start = cleaned_text.find('```json') + 7
                end = cleaned_text.find('```', start)
                if end != -1:
                    cleaned_text = cleaned_text[start:end].strip()
            elif '```' in cleaned_text:
                start = cleaned_text.find('```') + 3
                end = cleaned_text.find('```', start)
                if end != -1:
                    cleaned_text = cleaned_text[start:end].strip()
            
            description_data = json.loads(cleaned_text)
            
            return CityDescription(
                city_name=city.name,
                short_description=description_data['short_description'],
                detailed_description=description_data['detailed_description'],
                highlights=description_data['highlights'],
                best_for=description_data['best_for'],
                hidden_gems=description_data['hidden_gems'],
                practical_info=description_data['practical_info'],
                why_visit_reason=description_data['why_visit_reason'],
                photo_keywords=description_data['photo_keywords']
            )
            
        except Exception as e:
            logger.error(f"AI description generation failed: {e}")
            raise
    
    def _generate_basic_description(self, city: City, route_type: str = None) -> CityDescription:
        """Generate basic description when AI is not available."""
        
        # Create basic description based on city types
        city_types = city.types or ['charming']
        
        # Generate basic content based on types
        if 'authentic' in city_types or 'hidden_gems' in city_types:
            short_desc = f"A hidden gem in {city.country} offering authentic local experiences away from tourist crowds."
            why_visit = f"Experience the authentic charm of {city.country} in this lesser-known destination."
        elif 'cultural' in city_types or 'historic' in city_types:
            short_desc = f"A culturally rich destination in {city.country} with significant historical heritage."
            why_visit = f"Immerse yourself in the cultural heritage of {city.country}."
        elif 'scenic' in city_types or 'alpine' in city_types:
            short_desc = f"A picturesque destination in {city.country} offering stunning natural beauty."
            why_visit = f"Enjoy breathtaking scenery in one of {city.country}'s most beautiful locations."
        else:
            short_desc = f"A charming destination in {city.country} perfect for road trip exploration."
            why_visit = f"Discover the unique character of {city.name} on your journey through {city.country}."
        
        detailed_desc = f"{city.name} represents the essence of {city.country} with its {', '.join(city_types[:3])} character. " \
                       f"This destination offers travelers an opportunity to experience local culture and traditions. " \
                       f"The area is known for its welcoming atmosphere and provides an excellent stopping point for road trip travelers."
        
        return CityDescription(
            city_name=city.name,
            short_description=short_desc,
            detailed_description=detailed_desc,
            highlights=[f"{city.name} historic center", "Local cultural sites", "Traditional architecture"],
            best_for=["Cultural travelers", "Authentic experience seekers", "Road trip adventurers"],
            hidden_gems=["Local markets", "Traditional restaurants", "Scenic viewpoints"],
            practical_info=f"A pleasant stop in {city.country} with local amenities and parking available.",
            why_visit_reason=why_visit,
            photo_keywords=[city.name.lower(), city.country.lower(), "historic", "local culture"]
        )
    
    def enhance_cities_with_descriptions(
        self, 
        cities: List[City], 
        route_type: str = None, 
        trip_request: TripRequest = None
    ) -> List[Dict]:
        """Enhance a list of cities with rich descriptions."""
        
        async def process_cities():
            enhanced_cities = []
            for city in cities:
                try:
                    description = await self.get_city_description(city, route_type, trip_request)
                    enhanced_cities.append({
                        'city': city,
                        'description': description
                    })
                except Exception as e:
                    logger.warning(f"Failed to enhance {city.name}: {e}")
                    # Add basic city data without description
                    enhanced_cities.append({'city': city, 'description': None})
            
            return enhanced_cities
        
        # Run the async function
        try:
            # Check if we're already in an event loop
            try:
                loop = asyncio.get_running_loop()
                # We're in an event loop, can't use asyncio.run()
                logger.warning("Already in event loop, skipping async city enhancement")
                # Return basic city data without async processing
                return [{'city': city, 'description': None} for city in cities]
            except RuntimeError:
                # No event loop running, we can use asyncio.run()
                return asyncio.run(process_cities())
        except Exception as e:
            logger.error(f"Failed to enhance cities: {e}")
            # Return basic city data
            return [{'city': city, 'description': None} for city in cities]


# Global service instance
_city_description_service = None

def get_city_description_service() -> CityDescriptionService:
    """Get the global city description service instance."""
    global _city_description_service
    if _city_description_service is None:
        _city_description_service = CityDescriptionService()
    return _city_description_service