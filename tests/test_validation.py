"""
Comprehensive tests for validation service.
"""
import pytest
from src.services.validation_service import ValidationService
from src.core.models import Season


class TestValidationService:
    """Test validation service with security focus."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.validator = ValidationService()
    
    def test_valid_trip_request(self):
        """Test valid trip request validation."""
        form_data = {
            'start_city': 'Paris',
            'end_city': 'Rome',
            'travel_days': '5',
            'nights_at_destination': '2',
            'season': 'summer'
        }
        
        result = self.validator.validate_trip_request(form_data)
        assert result.success
        assert result.data.start_city == 'Paris'
        assert result.data.travel_days == 5
        assert result.data.season == Season.SUMMER
    
    def test_invalid_city_names(self):
        """Test validation of malicious city names."""
        malicious_inputs = [
            '<script>alert("xss")</script>',
            'javascript:alert(1)',
            'Paris<script>',
            'Rome" onload="alert(1)"',
            'A' * 200,  # Too long
            '',  # Empty
            123,  # Not a string
        ]
        
        for malicious_input in malicious_inputs:
            form_data = {
                'start_city': malicious_input,
                'end_city': 'Rome',
                'travel_days': '5',
                'nights_at_destination': '2',
                'season': 'summer'
            }
            
            result = self.validator.validate_trip_request(form_data)
            assert not result.success, f"Should reject: {malicious_input}"
    
    def test_travel_days_validation(self):
        """Test travel days validation."""
        invalid_days = [-1, 0, 31, 'abc', None, '']
        
        for invalid_day in invalid_days:
            form_data = {
                'start_city': 'Paris',
                'end_city': 'Rome',
                'travel_days': invalid_day,
                'nights_at_destination': '2',
                'season': 'summer'
            }
            
            result = self.validator.validate_trip_request(form_data)
            assert not result.success, f"Should reject days: {invalid_day}"
    
    def test_api_key_validation(self):
        """Test API key format validation."""
        valid_keys = [
            '',  # Empty is allowed
            'sk-ant-' + 'a' * 50,  # Valid format
            'test-key-123456789012345678901234567890'
        ]
        
        for key in valid_keys:
            assert self.validator._validate_api_key(key), f"Should accept: {key[:20]}..."
        
        invalid_keys = [
            'short',  # Too short
            'A' * 201,  # Too long
            'key with spaces',  # Invalid characters
            'key<script>',  # XSS attempt
            123,  # Not a string
        ]
        
        for key in invalid_keys:
            assert not self.validator._validate_api_key(key), f"Should reject: {str(key)[:20]}..."
    
    def test_coordinate_validation(self):
        """Test coordinate validation."""
        valid_coords = [
            (0, 0),
            (45.4408, 12.3155),  # Venice
            (-90, -180),  # Extremes
            (90, 180)
        ]
        
        for lat, lon in valid_coords:
            assert self.validator.validate_coordinates(lat, lon)
        
        invalid_coords = [
            (91, 0),  # Invalid latitude
            (-91, 0),
            (0, 181),  # Invalid longitude
            (0, -181),
            ('invalid', 0),  # Non-numeric
            (None, None)
        ]
        
        for lat, lon in invalid_coords:
            assert not self.validator.validate_coordinates(lat, lon)
    
    def test_output_sanitization(self):
        """Test XSS prevention in output sanitization."""
        malicious_data = {
            'city': '<script>alert("xss")</script>',
            'description': 'Safe text with "quotes" and \'apostrophes\'',
            'nested': {
                'attack': '<img src=x onerror=alert(1)>',
                'list': ['<script>', 'safe text', '<b>bold</b>']
            }
        }
        
        sanitized = self.validator.sanitize_output(malicious_data)
        
        assert '&lt;script&gt;' in sanitized['city']
        assert 'alert' not in sanitized['city'] or '&quot;' in sanitized['city']
        assert '&lt;script&gt;' in sanitized['nested']['list'][0]
        assert '&lt;b&gt;bold&lt;/b&gt;' in sanitized['nested']['list'][2]
    
    def test_season_validation(self):
        """Test season parameter validation."""
        valid_seasons = ['spring', 'summer', 'autumn', 'winter', 'SUMMER', ' winter ']
        
        for season in valid_seasons:
            assert self.validator._validate_season(season) is not None
        
        invalid_seasons = ['invalid', '', None, 123, 'fall']
        
        for season in invalid_seasons:
            assert self.validator._validate_season(season) is None