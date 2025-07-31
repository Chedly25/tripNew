#!/usr/bin/env python3
"""
Create a fixed version of the results page with better debugging and error handling.
"""

def create_fixed_results_page():
    """Create a fixed version with better debugging."""
    
    # Add debug logging to the existing results template
    debug_js = """
    // Enhanced debugging for intermediate cities issue
    console.log('=== DEBUGGING INTERMEDIATE CITIES ===');
    
    function loadItineraries() {
        console.log('loadItineraries() called');
        
        const container = document.getElementById('itineraries-container');
        const routeSummary = document.getElementById('route-summary');
        
        // Try to get data from sessionStorage (from form submission)
        let itineraries = [];
        let dataSource = 'none';
        
        try {
            const storedData = sessionStorage.getItem('travelPlanResult');
            console.log('Raw stored data:', storedData);
            
            if (storedData) {
                const data = JSON.parse(storedData);
                console.log('Parsed stored data:', data);
                
                if (data && data.data && data.data.routes) {
                    itineraries = data.data.routes;
                    dataSource = 'sessionStorage';
                    console.log('SUCCESS: Using real API data from sessionStorage');
                    console.log('Number of routes:', itineraries.length);
                    
                    // Log intermediate cities for each route
                    itineraries.forEach((route, index) => {
                        const intermediates = route.intermediate_cities || [];
                        console.log(`Route ${index + 1} (${route.name}): ${intermediates.length} intermediate cities`);
                        intermediates.forEach((city, cityIndex) => {
                            console.log(`  ${cityIndex + 1}. ${city.name} at [${city.coordinates}]`);
                        });
                    });
                }
            }
        } catch (e) {
            console.error('Error loading stored data:', e);
        }
        
        // Use sample data if no real data available
        if (itineraries.length === 0) {
            console.log('FALLBACK: No real data found, using sample data');
            itineraries = sampleItineraries;
            dataSource = 'sample';
            
            // Log sample data intermediate cities
            itineraries.forEach((route, index) => {
                const intermediates = route.intermediate_cities || [];
                console.log(`Sample Route ${index + 1} (${route.name}): ${intermediates.length} intermediate cities`);
                intermediates.forEach((city, cityIndex) => {
                    console.log(`  ${cityIndex + 1}. ${city.name} at [${city.coordinates}]`);
                });
            });
        }
        
        console.log(`Data source: ${dataSource}`);
        console.log(`Total itineraries to render: ${itineraries.length}`);
        
        // Update summary
        routeSummary.textContent = `${itineraries.length} amazing itineraries crafted just for you (${dataSource} data)`;
        
        // Render each itinerary
        container.innerHTML = '';
        itineraries.forEach((itinerary, index) => {
            console.log(`Rendering itinerary ${index + 1}: ${itinerary.name}`);
            
            const itineraryHtml = createItineraryCard(itinerary, index);
            container.insertAdjacentHTML('beforeend', itineraryHtml);
            
            // Initialize map for this itinerary with error handling
            setTimeout(() => {
                try {
                    console.log(`Initializing map for itinerary ${index}: ${itinerary.name}`);
                    initializeMap(itinerary, index);
                    console.log(`Map initialized successfully for itinerary ${index}`);
                } catch (mapError) {
                    console.error(`Map initialization failed for itinerary ${index}:`, mapError);
                }
            }, 100 * (index + 1)); // Stagger the map initializations
        });
        
        console.log('=== DEBUGGING COMPLETE ===');
    }
    """
    
    print("Fixed debugging JavaScript created.")
    print("\nTo fix the intermediate cities issue:")
    print("1. Clear your browser cache and refresh the page")
    print("2. Try accessing the results page by submitting the form from the home page")
    print("3. Check the browser console for the debug messages")
    print("4. If using sample data, it SHOULD show intermediate cities (Annecy, Lake Como, Verona)")
    
    return debug_js

if __name__ == "__main__":
    create_fixed_results_page()