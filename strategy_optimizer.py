"""Strategy Optimization - Genetic Algorithm-based parameter tuning."""

import numpy as np
from typing import Dict, List, Tuple, Any, Callable
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class StrategyOptimizer:
    """Optimize trading strategy parameters using genetic algorithms."""
    
    def __init__(self, objective_function: Callable, 
                 param_bounds: Dict[str, Tuple[float, float]]):
        """
        Initialize optimizer.
        
        Args:
            objective_function: Function to maximize (Sharpe ratio, profit, etc)
            param_bounds: Dictionary of parameter bounds {param_name: (min, max)}
        """
        self.objective_function = objective_function
        self.param_bounds = param_bounds
        self.population = []
        self.best_fitness = None
        self.best_individual = None
        self.fitness_history = []
        
        try:
            from deap import base, creator, tools, algorithms
            self.deap_available = True
            self.creator = creator
            self.base = base
            self.tools = tools
            self.algorithms = algorithms
        except ImportError:
            logger.warning("DEAP not installed. Install: pip install deap")
            self.deap_available = False
    
    def setup_deap(self):
        """Setup DEAP framework."""
        if not self.deap_available:
            logger.error("DEAP not available")
            return False
        
        try:
            # Define fitness and individual
            self.creator.create("FitnessMax", self.base.Fitness, weights=(1.0,))
            self.creator.create("Individual", list, fitness=self.creator.FitnessMax)
            
            # Create toolbox
            self.toolbox = self.base.Toolbox()
            
            # Attribute generators
            param_names = list(self.param_bounds.keys())
            for i, param in enumerate(param_names):
                min_val, max_val = self.param_bounds[param]
                self.toolbox.register(
                    f"attr_{i}",
                    np.random.uniform,
                    min_val,
                    max_val
                )
            
            # Individual and population
            attributes = [getattr(self.toolbox, f"attr_{i}") for i in range(len(param_names))]
            self.toolbox.register("individual", self._create_individual, attributes)
            self.toolbox.register("population", self.tools.initRepeat, list, 
                                self.toolbox.individual)
            
            # Genetic operators
            self.toolbox.register("evaluate", self._evaluate)
            self.toolbox.register("mate", self.tools.cxBlend, alpha=0.5)
            self.toolbox.register("mutate", self.tools.mutGaussian, mu=0, sigma=0.2, indpb=0.2)
            self.toolbox.register("select", self.tools.selTournament, tournsize=3)
            
            # Bounds
            for i in range(len(param_names)):
                min_val, max_val = list(self.param_bounds.values())[i]
                self.toolbox.decorate("mate", self.tools.DeltaFitness)
                self.toolbox.decorate("mutate", 
                                     self.tools.DeltaFitness)
            
            logger.info("✅ DEAP framework setup complete")
            return True
        
        except Exception as e:
            logger.error(f"Error setting up DEAP: {e}")
            return False
    
    def _create_individual(self, attributes):
        """Create individual with attribute generators."""
        return self.creator.Individual([attr() for attr in attributes])
    
    def _evaluate(self, individual):
        """Evaluate individual fitness."""
        try:
            params = dict(zip(self.param_bounds.keys(), individual))
            fitness = self.objective_function(params)
            return (fitness,)
        except Exception as e:
            logger.error(f"Error evaluating individual: {e}")
            return (0,)
    
    def optimize(self, population_size: int = 50, generations: int = 20,
                cxpb: float = 0.7, mutpb: float = 0.3) -> Dict[str, Any]:
        """Run genetic algorithm optimization."""
        
        if not self.setup_deap():
            return {}
        
        logger.info(f"🧬 Starting optimization: {generations} generations, "
                   f"{population_size} population")
        
        start_time = datetime.now()
        
        # Create population
        population = self.toolbox.population(n=population_size)
        
        # Evaluate initial population
        fitnesses = map(self.toolbox.evaluate, population)
        for ind, fit in zip(population, fitnesses):
            ind.fitness.values = fit
        
        # Evolution loop
        for gen in range(generations):
            # Select next generation
            offspring = self.toolbox.select(population, len(population))
            offspring = [self.toolbox.clone(ind) for ind in offspring]
            
            # Crossover
            for child1, child2 in zip(offspring[::2], offspring[1::2]):
                if np.random.random() < cxpb:
                    self.toolbox.mate(child1, child2)
                    del child1.fitness.values
                    del child2.fitness.values
            
            # Mutation
            for mutant in offspring:
                if np.random.random() < mutpb:
                    self.toolbox.mutate(mutant)
                    del mutant.fitness.values
            
            # Evaluate individuals with invalid fitness
            invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
            fitnesses = map(self.toolbox.evaluate, invalid_ind)
            for ind, fit in zip(invalid_ind, fitnesses):
                ind.fitness.values = fit
            
            # Replace population
            population[:] = offspring
            
            # Track best
            best_ind = max(population, key=lambda x: x.fitness.values[0])
            self.fitness_history.append(best_ind.fitness.values[0])
            
            if gen % 5 == 0:
                logger.info(f"Generation {gen}: Best Fitness = {best_ind.fitness.values[0]:.4f}")
        
        # Final best
        best_ind = max(population, key=lambda x: x.fitness.values[0])
        self.best_individual = dict(zip(self.param_bounds.keys(), best_ind))
        self.best_fitness = best_ind.fitness.values[0]
        
        duration = (datetime.now() - start_time).total_seconds()
        
        return {
            'best_params': self.best_individual,
            'best_fitness': self.best_fitness,
            'generations': generations,
            'duration_seconds': duration,
            'fitness_history': self.fitness_history,
            'improvement': (self.fitness_history[-1] - self.fitness_history[0]) / abs(self.fitness_history[0])
        }

class ParticleSwarmOptimizer:
    """Particle Swarm Optimization for parameter tuning."""
    
    def __init__(self, objective_function: Callable,
                 param_bounds: Dict[str, Tuple[float, float]]):
        self.objective_function = objective_function
        self.param_bounds = param_bounds
        self.particles = []
        self.best_global = None
        self.best_global_fitness = -np.inf
    
    def optimize(self, num_particles: int = 30, num_iterations: int = 50,
                w: float = 0.7, c1: float = 1.5, c2: float = 1.5) -> Dict[str, Any]:
        """Run particle swarm optimization."""
        
        logger.info(f"🐝 Starting PSO: {num_iterations} iterations, {num_particles} particles")
        
        start_time = datetime.now()
        
        # Initialize particles
        param_names = list(self.param_bounds.keys())
        
        particles = []
        velocities = []
        fitness_history = []
        
        for _ in range(num_particles):
            position = {
                param: np.random.uniform(bounds[0], bounds[1])
                for param, bounds in self.param_bounds.items()
            }
            velocity = {
                param: np.random.uniform(-0.1, 0.1)
                for param in param_names
            }
            
            particles.append({'position': position, 'best_position': position.copy()})
            velocities.append(velocity)
            
            # Evaluate
            fitness = self.objective_function(position)
            particles[-1]['fitness'] = fitness
            particles[-1]['best_fitness'] = fitness
            
            # Update global best
            if fitness > self.best_global_fitness:
                self.best_global_fitness = fitness
                self.best_global = position.copy()
        
        # PSO iterations
        for iteration in range(num_iterations):
            for i, particle in enumerate(particles):
                # Update velocity and position
                for param in param_names:
                    r1, r2 = np.random.random(), np.random.random()
                    
                    velocities[i][param] = (
                        w * velocities[i][param] +
                        c1 * r1 * (particle['best_position'][param] - particle['position'][param]) +
                        c2 * r2 * (self.best_global[param] - particle['position'][param])
                    )
                    
                    # Update position
                    new_value = particle['position'][param] + velocities[i][param]
                    bounds = self.param_bounds[param]
                    particle['position'][param] = np.clip(new_value, bounds[0], bounds[1])
                
                # Evaluate
                fitness = self.objective_function(particle['position'])
                particle['fitness'] = fitness
                
                # Update personal best
                if fitness > particle['best_fitness']:
                    particle['best_fitness'] = fitness
                    particle['best_position'] = particle['position'].copy()
                
                # Update global best
                if fitness > self.best_global_fitness:
                    self.best_global_fitness = fitness
                    self.best_global = particle['position'].copy()
            
            fitness_history.append(self.best_global_fitness)
            
            if (iteration + 1) % 10 == 0:
                logger.info(f"Iteration {iteration + 1}: Best Fitness = {self.best_global_fitness:.4f}")
        
        duration = (datetime.now() - start_time).total_seconds()
        
        return {
            'best_params': self.best_global,
            'best_fitness': self.best_global_fitness,
            'iterations': num_iterations,
            'duration_seconds': duration,
            'fitness_history': fitness_history,
            'improvement': (fitness_history[-1] - fitness_history[0]) / abs(fitness_history[0])
        }

# Example usage
def example_optimization():
    """Example strategy optimization."""
    
    # Define strategy parameter bounds
    param_bounds = {
        'fast_ma': (5, 50),
        'slow_ma': (50, 200),
        'rsi_lower': (20, 40),
        'rsi_upper': (60, 80),
        'stop_loss': (0.01, 0.05)
    }
    
    # Mock objective function (Sharpe ratio)
    def evaluate_strategy(params):
        # Simulate strategy evaluation
        score = (
            100 * np.exp(-(params['fast_ma'] - 20) ** 2 / 100) +
            50 * np.exp(-(params['slow_ma'] - 100) ** 2 / 1000) +
            30 * np.sin(params['rsi_lower'] / 50) +
            20 * np.cos(params['stop_loss'] * 100)
        )
        return score
    
    # Genetic Algorithm
    print("🧬 Genetic Algorithm Optimization:")
    ga_optimizer = StrategyOptimizer(evaluate_strategy, param_bounds)
    
    # Note: Only run if DEAP is installed
    try:
        ga_results = ga_optimizer.optimize(population_size=30, generations=20)
        print(f"✅ Best Fitness: {ga_results.get('best_fitness', 'N/A')}")
    except:
        print("⚠️ DEAP not available for GA (install: pip install deap)")
    
    # Particle Swarm Optimization
    print("\n🐝 Particle Swarm Optimization:")
    pso_optimizer = ParticleSwarmOptimizer(evaluate_strategy, param_bounds)
    pso_results = pso_optimizer.optimize(num_particles=20, num_iterations=30)
    
    print(f"✅ Best Fitness: {pso_results['best_fitness']:.4f}")
    print(f"✅ Best Parameters: {pso_results['best_params']}")
    print(f"✅ Duration: {pso_results['duration_seconds']:.1f}s")
    print(f"✅ Improvement: {pso_results['improvement']*100:.1f}%")

if __name__ == "__main__":
    example_optimization()
