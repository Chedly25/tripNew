"""
Integration tests for service layer.
"""
import pytest
from unittest.mock import Mock, patch
from src.services.city_service import CityService
from src.services.route_service import ProductionRouteService
from src.services.travel_planner import TravelPlannerServiceImpl
from src.services.validation_service import ValidationService
from src.infrastructure.config import SecureConfigurationService
from src.core.models import TripRequest, Season, City, Coordinates


class TestCityService:
    """Test city service functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.mock_db = Mock()
        self.city_service = CityService(self.mock_db)
    
    def test_get_city_by_name(self):
        """Test city lookup by name."""
        # Test exact match
        city = self.city_service.get_city_by_name('Venice')
        assert city is not None
        assert city.name == 'Venice'
        assert city.country == 'Italy'
    
    def test_get_city_fuzzy_match(self):
        """Test fuzzy matching for city names."""
        # Test partial match
        city = self.city_service.get_city_by_name('venic')
        assert city is not None
        assert city.name == 'Venice'
    
    def test_find_cities_by_type(self):
        """Test finding cities by type."""
        cultural_cities = self.city_service.find_cities_by_type('cultural')
        assert len(cultural_cities) > 0
        
        # Verify all returned cities have the cultural type
        for city in cultural_cities:
            assert 'cultural' in [t.lower() for t in city.types]
    
    def test_find_cities_near_route(self):
        """Test finding cities near a route."""
        start = Coordinates(43.5297, 5.4474)  # Aix-en-Provence
        end = Coordinates(45.4408, 12.3155)   # Venice
        
        near_cities = self.city_service.find_cities_near_route(start, end, 100)
        assert len(near_cities) > 0
        
        # Cities should be sorted by distance from start
        distances = []
        for city in near_cities:
            from geopy.distance import geodesic
            dist = geodesic(
                (start.latitude, start.longitude),
                (city.coordinates.latitude, city.coordinates.longitude)
            ).kilometers
            distances.append(dist)
        
        assert distances == sorted(distances)


class TestRouteService:
    """Test route calculation service."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.mock_config = Mock(spec=SecureConfigurationService)
        self.mock_config.get_api_config.return_value = Mock(
            timeout=30, max_retries=3, rate_limit_per_minute=60
        )
        self.mock_config.get_api_key.return_value = None  # No API key
        self.route_service = ProductionRouteService(self.mock_config)
    
    def test_calculate_route_fallback(self):
        """Test route calculation with geometric fallback."""
        start = City('Paris', Coordinates(48.8566, 2.3522), 'France')
        end = City('Rome', Coordinates(41.9028, 12.4964), 'Italy')
        
        result = self.route_service.calculate_route(start, end)
        
        assert result.success
        assert result.data['distance_km'] > 0
        assert result.data['duration_hours'] > 0
        assert result.data['route_type'] == 'geometric_fallback'
    
    def test_optimize_multi_city_route(self):
        """Test multi-city route optimization."""
        cities = [
            City('Paris', Coordinates(48.8566, 2.3522), 'France'),
            City('Lyon', Coordinates(45.7640, 4.8357), 'France'),
            City('Milan', Coordinates(45.4642, 9.1900), 'Italy'),
            City('Venice', Coordinates(45.4408, 12.3155), 'Italy')
        ]
        
        result = self.route_service.optimize_multi_city_route(cities)
        
        assert result.success
        assert len(result.data['optimized_cities']) == 4
        assert result.data['total_distance_km'] > 0
        assert len(result.data['segments']) == 3  # n-1 segments for n cities


class TestTravelPlannerIntegration:
    """Integration tests for the main travel planner."""
    
    def setup_method(self):
        """Setup integrated services."""
        self.mock_db = Mock()
        self.city_service = CityService(self.mock_db)
        
        self.mock_config = Mock(spec=SecureConfigurationService)
        self.mock_config.get_api_config.return_value = Mock(
            timeout=30, max_retries=3, rate_limit_per_minute=60
        )
        self.mock_config.get_api_key.return_value = None
        self.route_service = ProductionRouteService(self.mock_config)
        
        self.validation_service = ValidationService()
        
        self.travel_planner = TravelPlannerServiceImpl(
            self.city_service, self.route_service, self.validation_service
        )
    
    def test_generate_routes_success(self):
        """Test successful route generation."""
        request = TripRequest(
            start_city='Aix-en-Provence',
            end_city='Venice',
            travel_days=7,
            nights_at_destination=3,
            season=Season.SUMMER
        )
        
        result = self.travel_planner.generate_routes(request)
        
        assert result.success
        assert 'routes' in result.data
        assert len(result.data['routes']) > 0
        
        # Check route structure
        first_route = result.data['routes'][0]
        assert 'route_type' in first_route
        assert 'total_distance_km' in first_route
        assert 'start_city' in first_route
        assert 'end_city' in first_route
    
    def test_generate_routes_invalid_cities(self):
        """Test route generation with invalid cities."""
        request = TripRequest(
            start_city='NonexistentCity',
            end_city='Venice',
            travel_days=7,
            nights_at_destination=3,
            season=Season.SUMMER
        )
        
        result = self.travel_planner.generate_routes(request)
        
        assert not result.success
        assert 'not found' in result.error_message.lower()
    
    def test_route_enrichment(self):
        """Test that routes are properly enriched with additional data."""
        request = TripRequest(
            start_city='Aix-en-Provence',
            end_city='Venice',
            travel_days=5,
            nights_at_destination=2,
            season=Season.WINTER
        )
        
        result = self.travel_planner.generate_routes(request)
        
        assert result.success
        first_route = result.data['routes'][0]
        
        # Check enriched data
        assert 'season_tips' in first_route
        assert 'estimated_cost' in first_route
        assert 'estimated_driving_time' in first_route
        
        # Winter-specific tips should be present
        tips = first_route['season_tips']
        assert any('winter' in tip.lower() for tip in tips)


class TestServiceErrorHandling:
    """Test error handling across services."""
    
    def test_database_connection_failure(self):
        """Test graceful handling of database failures."""
        # Mock database that raises exception
        mock_db = Mock()
        mock_db.health_check.side_effect = Exception("Database connection failed")
        
        # Service should handle this gracefully
        city_service = CityService(mock_db)
        # City service loads data in memory, so should still work
        city = city_service.get_city_by_name('Venice')
        assert city is not None
    
    def test_external_api_failure(self):
        """Test handling of external API failures."""
        mock_config = Mock(spec=SecureConfigurationService)
        mock_config.get_api_config.return_value = Mock(
            timeout=1, max_retries=1, rate_limit_per_minute=60
        )
        mock_config.get_api_key.return_value = 'test-key'
        
        route_service = ProductionRouteService(mock_config)
        
        # Should fall back to geometric calculation
        start = City('Paris', Coordinates(48.8566, 2.3522), 'France')
        end = City('Rome', Coordinates(41.9028, 12.4964), 'Italy')
        
        result = route_service.calculate_route(start, end)
        
        assert result.success
        assert result.data['route_type'] == 'geometric_fallback'