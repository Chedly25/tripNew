"""
Route Optimization Service

Advanced algorithms for optimizing intermediate city selection and sequencing.
Implements multiple optimization strategies for different travel scenarios.
"""
import math
import random
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import structlog

from ..core.models import City, Coordinates

logger = structlog.get_logger(__name__)


@dataclass
class RouteOptimizationConfig:
    """Configuration for route optimization algorithms."""
    max_detour_ratio: float = 0.3  # Max detour as ratio of direct distance
    min_stop_distance_km: float = 80  # Minimum distance between stops
    max_stop_distance_km: float = 200  # Maximum distance between stops
    prefer_even_spacing: bool = True
    optimize_for_driving_time: bool = True
    consider_attractions: bool = True
    balance_variety: bool = True
    
    # Algorithm-specific parameters
    genetic_population_size: int = 50
    genetic_generations: int = 100
    genetic_mutation_rate: float = 0.1
    
    simulated_annealing_initial_temp: float = 1000.0
    simulated_annealing_cooling_rate: float = 0.95
    simulated_annealing_min_temp: float = 1.0


@dataclass
class OptimizedRoute:
    """Result of route optimization."""
    cities: List[City]
    total_distance: float
    total_score: float
    optimization_method: str
    performance_metrics: Dict[str, float]
    routing_explanation: str


class RouteOptimizationService:
    """Advanced route optimization using multiple algorithms."""
    
    def __init__(self):
        self.config = RouteOptimizationConfig()
        self.distance_cache: Dict[Tuple[str, str], float] = {}
    
    def optimize_route(
        self,
        start_city: City,
        end_city: City,
        candidate_cities: List[City],
        max_cities: int,
        route_type: str,
        city_scores: Dict[str, float] = None
    ) -> OptimizedRoute:
        """
        Optimize route using the best available algorithm.
        
        Tries multiple optimization approaches and returns the best result.
        """
        
        if not candidate_cities:
            return OptimizedRoute(
                cities=[],
                total_distance=self._calculate_distance(start_city.coordinates, end_city.coordinates),
                total_score=0.0,
                optimization_method="no_candidates",
                performance_metrics={},
                routing_explanation="No candidate cities available"
            )
        
        if len(candidate_cities) <= max_cities:
            # If we have few enough candidates, use all and optimize order
            selected_cities = candidate_cities
            optimization_method = "simple_ordering"
        else:
            # Multiple algorithms for selection and optimization
            algorithms = [
                self._genetic_algorithm_optimization,
                self._simulated_annealing_optimization,
                self._greedy_optimization_with_local_search,
                self._dynamic_programming_optimization
            ]
            
            best_result = None
            best_score = -1
            
            for algorithm in algorithms:
                try:
                    result = algorithm(
                        start_city, end_city, candidate_cities, max_cities, 
                        route_type, city_scores or {}
                    )
                    
                    if result.total_score > best_score:
                        best_score = result.total_score
                        best_result = result
                        
                except Exception as e:
                    logger.warning(f"Optimization algorithm failed: {e}")
                    continue
            
            if best_result:
                return best_result
            
            # Fallback to simple greedy if all algorithms fail
            selected_cities = self._greedy_selection(
                start_city, end_city, candidate_cities, max_cities, city_scores or {}
            )
            optimization_method = "greedy_fallback"
        
        # Optimize the order of selected cities
        optimized_order = self._optimize_city_order(start_city, end_city, selected_cities)
        
        # Calculate final metrics
        total_distance = self._calculate_total_route_distance(
            [start_city] + optimized_order + [end_city]
        )
        
        total_score = self._calculate_route_score(
            start_city, end_city, optimized_order, route_type, city_scores or {}
        )
        
        return OptimizedRoute(
            cities=optimized_order,
            total_distance=total_distance,
            total_score=total_score,
            optimization_method=optimization_method,
            performance_metrics=self._calculate_performance_metrics(
                start_city, end_city, optimized_order
            ),
            routing_explanation=self._generate_routing_explanation(
                start_city, end_city, optimized_order, optimization_method
            )
        )
    
    def _genetic_algorithm_optimization(
        self,
        start_city: City,
        end_city: City,
        candidates: List[City],
        max_cities: int,
        route_type: str,
        city_scores: Dict[str, float]
    ) -> OptimizedRoute:
        """Genetic algorithm for route optimization."""
        
        logger.info("Using genetic algorithm for route optimization")
        
        # Initialize population
        population = []
        for _ in range(self.config.genetic_population_size):
            individual = random.sample(candidates, min(max_cities, len(candidates)))
            population.append(individual)
        
        best_individual = None
        best_fitness = -1
        
        for generation in range(self.config.genetic_generations):
            # Evaluate fitness for each individual
            fitness_scores = []
            for individual in population:
                fitness = self._calculate_route_score(
                    start_city, end_city, individual, route_type, city_scores
                )
                fitness_scores.append(fitness)
                
                if fitness > best_fitness:
                    best_fitness = fitness
                    best_individual = individual.copy()
            
            # Selection, crossover, and mutation
            new_population = []
            
            # Keep best individuals (elitism)
            sorted_population = sorted(
                zip(population, fitness_scores), 
                key=lambda x: x[1], 
                reverse=True
            )
            
            elite_size = self.config.genetic_population_size // 5
            for i in range(elite_size):
                new_population.append(sorted_population[i][0])
            
            # Generate offspring
            while len(new_population) < self.config.genetic_population_size:
                parent1 = self._tournament_selection(population, fitness_scores)
                parent2 = self._tournament_selection(population, fitness_scores)
                
                offspring = self._crossover(parent1, parent2, max_cities)
                offspring = self._mutate(offspring, candidates, max_cities)
                
                new_population.append(offspring)
            
            population = new_population
        
        # Optimize order of best individual
        optimized_order = self._optimize_city_order(start_city, end_city, best_individual)
        
        total_distance = self._calculate_total_route_distance(
            [start_city] + optimized_order + [end_city]
        )
        
        return OptimizedRoute(
            cities=optimized_order,
            total_distance=total_distance,
            total_score=best_fitness,
            optimization_method="genetic_algorithm",
            performance_metrics=self._calculate_performance_metrics(
                start_city, end_city, optimized_order
            ),
            routing_explanation="Optimized using genetic algorithm for best combination of cities"
        )
    
    def _simulated_annealing_optimization(
        self,
        start_city: City,
        end_city: City,
        candidates: List[City],
        max_cities: int,
        route_type: str,
        city_scores: Dict[str, float]
    ) -> OptimizedRoute:
        """Simulated annealing optimization."""
        
        logger.info("Using simulated annealing for route optimization")
        
        # Initial solution
        current_solution = random.sample(candidates, min(max_cities, len(candidates)))
        current_score = self._calculate_route_score(
            start_city, end_city, current_solution, route_type, city_scores
        )
        
        best_solution = current_solution.copy()
        best_score = current_score
        
        temperature = self.config.simulated_annealing_initial_temp
        
        while temperature > self.config.simulated_annealing_min_temp:
            # Generate neighbor solution
            neighbor = self._generate_neighbor_solution(
                current_solution, candidates, max_cities
            )
            
            neighbor_score = self._calculate_route_score(
                start_city, end_city, neighbor, route_type, city_scores
            )
            
            # Accept or reject the neighbor
            if neighbor_score > current_score:
                # Better solution, always accept
                current_solution = neighbor
                current_score = neighbor_score
                
                if neighbor_score > best_score:
                    best_solution = neighbor.copy()
                    best_score = neighbor_score
            else:
                # Worse solution, accept with probability
                probability = math.exp((neighbor_score - current_score) / temperature)
                if random.random() < probability:
                    current_solution = neighbor
                    current_score = neighbor_score
            
            # Cool down
            temperature *= self.config.simulated_annealing_cooling_rate
        
        # Optimize order
        optimized_order = self._optimize_city_order(start_city, end_city, best_solution)
        
        total_distance = self._calculate_total_route_distance(
            [start_city] + optimized_order + [end_city]
        )
        
        return OptimizedRoute(
            cities=optimized_order,
            total_distance=total_distance,
            total_score=best_score,
            optimization_method="simulated_annealing",
            performance_metrics=self._calculate_performance_metrics(
                start_city, end_city, optimized_order
            ),
            routing_explanation="Optimized using simulated annealing for balanced exploration"
        )
    
    def _greedy_optimization_with_local_search(
        self,
        start_city: City,
        end_city: City,
        candidates: List[City],
        max_cities: int,
        route_type: str,
        city_scores: Dict[str, float]
    ) -> OptimizedRoute:
        """Greedy optimization with local search improvement."""
        
        logger.info("Using greedy optimization with local search")
        
        # Initial greedy selection
        selected = self._greedy_selection(
            start_city, end_city, candidates, max_cities, city_scores
        )
        
        # Local search improvement
        improved = self._local_search_improvement(
            start_city, end_city, selected, candidates, route_type, city_scores
        )
        
        # Optimize order
        optimized_order = self._optimize_city_order(start_city, end_city, improved)
        
        total_distance = self._calculate_total_route_distance(
            [start_city] + optimized_order + [end_city]
        )
        
        total_score = self._calculate_route_score(
            start_city, end_city, optimized_order, route_type, city_scores
        )
        
        return OptimizedRoute(
            cities=optimized_order,
            total_distance=total_distance,
            total_score=total_score,
            optimization_method="greedy_with_local_search",
            performance_metrics=self._calculate_performance_metrics(
                start_city, end_city, optimized_order
            ),
            routing_explanation="Greedy selection with local search refinement"
        )
    
    def _dynamic_programming_optimization(
        self,
        start_city: City,
        end_city: City,
        candidates: List[City],
        max_cities: int,
        route_type: str,
        city_scores: Dict[str, float]
    ) -> OptimizedRoute:
        """Dynamic programming optimization for smaller problems."""
        
        if len(candidates) > 15:  # DP is exponential, limit size
            raise ValueError("Too many candidates for dynamic programming")
        
        logger.info("Using dynamic programming for route optimization")
        
        # This is a simplified DP approach for the TSP-like problem
        # For production, you'd want a more sophisticated implementation
        
        best_combination = None
        best_score = -1
        
        # Try all combinations of cities up to max_cities
        from itertools import combinations
        
        for r in range(1, min(max_cities + 1, len(candidates) + 1)):
            for combination in combinations(candidates, r):
                cities_list = list(combination)
                score = self._calculate_route_score(
                    start_city, end_city, cities_list, route_type, city_scores
                )
                
                if score > best_score:
                    best_score = score
                    best_combination = cities_list
        
        if not best_combination:
            best_combination = []
        
        # Optimize order
        optimized_order = self._optimize_city_order(start_city, end_city, best_combination)
        
        total_distance = self._calculate_total_route_distance(
            [start_city] + optimized_order + [end_city]
        )
        
        return OptimizedRoute(
            cities=optimized_order,
            total_distance=total_distance,
            total_score=best_score,
            optimization_method="dynamic_programming",
            performance_metrics=self._calculate_performance_metrics(
                start_city, end_city, optimized_order
            ),
            routing_explanation="Optimal solution using dynamic programming"
        )
    
    def _greedy_selection(
        self,
        start_city: City,
        end_city: City,
        candidates: List[City],
        max_cities: int,
        city_scores: Dict[str, float]
    ) -> List[City]:
        """Greedy selection of cities."""
        
        selected = []
        remaining = candidates.copy()
        
        while len(selected) < max_cities and remaining:
            best_candidate = None
            best_score = -1
            
            for candidate in remaining:
                # Calculate composite score
                city_score = city_scores.get(candidate.name, 0.5)
                spacing_score = self._calculate_spacing_score(
                    candidate, selected, start_city, end_city
                )
                detour_score = self._calculate_detour_score(
                    candidate, start_city, end_city
                )
                
                composite_score = (
                    city_score * 0.5 + 
                    spacing_score * 0.3 + 
                    detour_score * 0.2
                )
                
                if composite_score > best_score:
                    best_score = composite_score
                    best_candidate = candidate
            
            if best_candidate:
                selected.append(best_candidate)
                remaining.remove(best_candidate)
            else:
                break
        
        return selected
    
    def _optimize_city_order(
        self, start_city: City, end_city: City, cities: List[City]
    ) -> List[City]:
        """Optimize the order of cities along the route."""
        
        if len(cities) <= 1:
            return cities
        
        # Use nearest neighbor heuristic for ordering
        ordered_cities = []
        remaining = cities.copy()
        current_position = start_city.coordinates
        
        while remaining:
            nearest_city = min(
                remaining,
                key=lambda city: self._calculate_distance(current_position, city.coordinates)
            )
            
            ordered_cities.append(nearest_city)
            remaining.remove(nearest_city)
            current_position = nearest_city.coordinates
        
        # Try to improve with 2-opt optimization
        improved_order = self._two_opt_optimization(start_city, end_city, ordered_cities)
        
        return improved_order
    
    def _two_opt_optimization(
        self, start_city: City, end_city: City, cities: List[City]
    ) -> List[City]:
        """2-opt optimization for city ordering."""
        
        if len(cities) < 3:
            return cities
        
        route = [start_city] + cities + [end_city]
        improved = True
        
        while improved:
            improved = False
            
            for i in range(1, len(route) - 2):
                for j in range(i + 1, len(route) - 1):
                    # Try swapping edges
                    new_route = route.copy()
                    new_route[i:j+1] = reversed(new_route[i:j+1])
                    
                    if self._calculate_total_route_distance(new_route) < self._calculate_total_route_distance(route):
                        route = new_route
                        improved = True
        
        # Return without start and end cities
        return route[1:-1]
    
    def _calculate_route_score(
        self,
        start_city: City,
        end_city: City,
        cities: List[City],
        route_type: str,
        city_scores: Dict[str, float]
    ) -> float:
        """Calculate overall score for a route."""
        
        if not cities:
            return 0.0
        
        # City quality score
        quality_score = sum(city_scores.get(city.name, 0.5) for city in cities) / len(cities)
        
        # Distance efficiency score
        direct_distance = self._calculate_distance(start_city.coordinates, end_city.coordinates)
        route_distance = self._calculate_total_route_distance([start_city] + cities + [end_city])
        
        detour_ratio = route_distance / direct_distance if direct_distance > 0 else 1.0
        distance_score = max(0.0, 1.0 - (detour_ratio - 1.0) / self.config.max_detour_ratio)
        
        # Spacing score
        spacing_score = self._calculate_overall_spacing_score(start_city, end_city, cities)
        
        # Variety score
        variety_score = self._calculate_variety_score(cities)
        
        # Combine scores
        total_score = (
            quality_score * 0.4 +
            distance_score * 0.3 +
            spacing_score * 0.2 +
            variety_score * 0.1
        )
        
        return total_score
    
    def _calculate_distance(self, coord1: Coordinates, coord2: Coordinates) -> float:
        """Calculate distance between two coordinates."""
        
        # Create cache key
        key = (f"{coord1.latitude},{coord1.longitude}", f"{coord2.latitude},{coord2.longitude}")
        
        if key in self.distance_cache:
            return self.distance_cache[key]
        
        # Haversine formula
        R = 6371  # Earth's radius in km
        
        lat1, lon1 = math.radians(coord1.latitude), math.radians(coord1.longitude)
        lat2, lon2 = math.radians(coord2.latitude), math.radians(coord2.longitude)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        distance = R * c
        
        # Cache the result
        self.distance_cache[key] = distance
        return distance
    
    def _calculate_total_route_distance(self, cities: List[City]) -> float:
        """Calculate total distance for a route."""
        
        if len(cities) < 2:
            return 0.0
        
        total_distance = 0.0
        for i in range(len(cities) - 1):
            total_distance += self._calculate_distance(
                cities[i].coordinates, cities[i + 1].coordinates
            )
        
        return total_distance
    
    def _calculate_spacing_score(
        self, candidate: City, selected: List[City], start_city: City, end_city: City
    ) -> float:
        """Calculate spacing score for a candidate city."""
        
        if not selected:
            return 0.8
        
        total_distance = self._calculate_distance(start_city.coordinates, end_city.coordinates)
        ideal_spacing = total_distance / (len(selected) + 2)
        
        min_distance = float('inf')
        for selected_city in selected:
            distance = self._calculate_distance(candidate.coordinates, selected_city.coordinates)
            min_distance = min(min_distance, distance)
        
        if min_distance == float('inf'):
            return 0.8
        
        spacing_ratio = min_distance / ideal_spacing
        
        if 0.5 <= spacing_ratio <= 1.5:
            return 1.0
        elif 0.3 <= spacing_ratio <= 2.0:
            return 0.7
        else:
            return 0.3
    
    def _calculate_detour_score(self, city: City, start_city: City, end_city: City) -> float:
        """Calculate detour score (lower penalty for less detour)."""
        
        direct_distance = self._calculate_distance(start_city.coordinates, end_city.coordinates)
        detour_distance = (
            self._calculate_distance(start_city.coordinates, city.coordinates) +
            self._calculate_distance(city.coordinates, end_city.coordinates)
        )
        
        detour_ratio = detour_distance / direct_distance if direct_distance > 0 else 1.0
        
        if detour_ratio <= 1.2:
            return 1.0  # Minimal detour
        elif detour_ratio <= 1.5:
            return 0.8  # Acceptable detour
        elif detour_ratio <= 2.0:
            return 0.5  # Significant detour
        else:
            return 0.2  # Large detour
    
    def _calculate_overall_spacing_score(
        self, start_city: City, end_city: City, cities: List[City]
    ) -> float:
        """Calculate overall spacing score for the route."""
        
        if not cities:
            return 1.0
        
        all_cities = [start_city] + cities + [end_city]
        distances = []
        
        for i in range(len(all_cities) - 1):
            distance = self._calculate_distance(
                all_cities[i].coordinates, all_cities[i + 1].coordinates
            )
            distances.append(distance)
        
        if not distances:
            return 1.0
        
        mean_distance = sum(distances) / len(distances)
        variance = sum((d - mean_distance) ** 2 for d in distances) / len(distances)
        
        # Lower variance means more even spacing
        spacing_score = 1.0 / (1.0 + variance / (mean_distance ** 2))
        
        return spacing_score
    
    def _calculate_variety_score(self, cities: List[City]) -> float:
        """Calculate variety score based on city types."""
        
        if not cities:
            return 0.0
        
        all_types = set()
        for city in cities:
            if hasattr(city, 'types') and city.types:
                all_types.update(city.types)
        
        # More unique types means more variety
        variety_score = min(len(all_types) / 10.0, 1.0)  # Normalize to max 10 types
        
        return variety_score
    
    def _calculate_performance_metrics(
        self, start_city: City, end_city: City, cities: List[City]
    ) -> Dict[str, float]:
        """Calculate performance metrics for the route."""
        
        direct_distance = self._calculate_distance(start_city.coordinates, end_city.coordinates)
        route_distance = self._calculate_total_route_distance([start_city] + cities + [end_city])
        
        return {
            'detour_ratio': route_distance / direct_distance if direct_distance > 0 else 1.0,
            'avg_stop_distance': route_distance / (len(cities) + 1) if cities else 0.0,
            'spacing_efficiency': self._calculate_overall_spacing_score(start_city, end_city, cities),
            'variety_score': self._calculate_variety_score(cities),
            'total_cities': len(cities)
        }
    
    def _generate_routing_explanation(
        self, start_city: City, end_city: City, cities: List[City], method: str
    ) -> str:
        """Generate human-readable explanation of the routing."""
        
        if not cities:
            return "Direct route with no intermediate stops."
        
        explanations = {
            'genetic_algorithm': "Selected using genetic algorithm to find optimal combination of cities that balances quality, distance, and variety.",
            'simulated_annealing': "Optimized using simulated annealing to explore different city combinations while avoiding local optima.",
            'greedy_with_local_search': "Greedy selection refined with local search to improve spacing and reduce unnecessary detours.",
            'dynamic_programming': "Mathematically optimal selection considering all possible combinations.",
            'simple_ordering': "Direct ordering of available cities for optimal routing."
        }
        
        base_explanation = explanations.get(method, "Optimized using advanced routing algorithms.")
        
        # Add specific details
        performance = self._calculate_performance_metrics(start_city, end_city, cities)
        
        details = []
        if performance['detour_ratio'] < 1.3:
            details.append("efficient routing")
        if performance['spacing_efficiency'] > 0.7:
            details.append("well-spaced stops")
        if performance['variety_score'] > 0.6:
            details.append("diverse city types")
        
        if details:
            base_explanation += f" Features: {', '.join(details)}."
        
        return base_explanation
    
    # Helper methods for genetic algorithm
    
    def _tournament_selection(self, population: List[List[City]], fitness_scores: List[float]) -> List[City]:
        """Tournament selection for genetic algorithm."""
        tournament_size = 3
        tournament_indices = random.sample(range(len(population)), min(tournament_size, len(population)))
        
        best_index = max(tournament_indices, key=lambda i: fitness_scores[i])
        return population[best_index]
    
    def _crossover(self, parent1: List[City], parent2: List[City], max_cities: int) -> List[City]:
        """Crossover operation for genetic algorithm."""
        # Simple uniform crossover
        all_cities = list(set(parent1 + parent2))
        
        offspring = []
        for city in all_cities:
            if len(offspring) >= max_cities:
                break
            
            # Include city if it's in both parents or randomly from one parent
            if city in parent1 and city in parent2:
                offspring.append(city)
            elif city in parent1 and random.random() < 0.5:
                offspring.append(city)
            elif city in parent2 and random.random() < 0.5:
                offspring.append(city)
        
        return offspring
    
    def _mutate(self, individual: List[City], candidates: List[City], max_cities: int) -> List[City]:
        """Mutation operation for genetic algorithm."""
        if random.random() > self.config.genetic_mutation_rate:
            return individual
        
        # Random mutation: add, remove, or replace a city
        mutation_type = random.choice(['add', 'remove', 'replace'])
        
        if mutation_type == 'add' and len(individual) < max_cities:
            available = [city for city in candidates if city not in individual]
            if available:
                individual.append(random.choice(available))
        
        elif mutation_type == 'remove' and individual:
            individual.remove(random.choice(individual))
        
        elif mutation_type == 'replace' and individual:
            available = [city for city in candidates if city not in individual]
            if available:
                old_city = random.choice(individual)
                new_city = random.choice(available)
                individual[individual.index(old_city)] = new_city
        
        return individual
    
    def _generate_neighbor_solution(
        self, current: List[City], candidates: List[City], max_cities: int
    ) -> List[City]:
        """Generate neighbor solution for simulated annealing."""
        neighbor = current.copy()
        
        # Random neighborhood operation
        operation = random.choice(['swap', 'add', 'remove', 'replace'])
        
        if operation == 'swap' and len(neighbor) >= 2:
            i, j = random.sample(range(len(neighbor)), 2)
            neighbor[i], neighbor[j] = neighbor[j], neighbor[i]
        
        elif operation == 'add' and len(neighbor) < max_cities:
            available = [city for city in candidates if city not in neighbor]
            if available:
                neighbor.append(random.choice(available))
        
        elif operation == 'remove' and neighbor:
            neighbor.remove(random.choice(neighbor))
        
        elif operation == 'replace' and neighbor:
            available = [city for city in candidates if city not in neighbor]
            if available:
                old_city = random.choice(neighbor)
                new_city = random.choice(available)
                neighbor[neighbor.index(old_city)] = new_city
        
        return neighbor
    
    def _local_search_improvement(
        self,
        start_city: City,
        end_city: City,
        selected: List[City],
        candidates: List[City],
        route_type: str,
        city_scores: Dict[str, float]
    ) -> List[City]:
        """Local search improvement for greedy algorithm."""
        
        current_solution = selected.copy()
        improved = True
        
        while improved:
            improved = False
            current_score = self._calculate_route_score(
                start_city, end_city, current_solution, route_type, city_scores
            )
            
            # Try replacing each city with an available alternative
            for i, city in enumerate(current_solution):
                available = [c for c in candidates if c not in current_solution]
                
                for replacement in available:
                    test_solution = current_solution.copy()
                    test_solution[i] = replacement
                    
                    test_score = self._calculate_route_score(
                        start_city, end_city, test_solution, route_type, city_scores
                    )
                    
                    if test_score > current_score:
                        current_solution = test_solution
                        current_score = test_score
                        improved = True
                        break
                
                if improved:
                    break
        
        return current_solution


# Global service instance
_route_optimization_service = None

def get_route_optimization_service() -> RouteOptimizationService:
    """Get the global route optimization service instance."""
    global _route_optimization_service
    if _route_optimization_service is None:
        _route_optimization_service = RouteOptimizationService()
    return _route_optimization_service