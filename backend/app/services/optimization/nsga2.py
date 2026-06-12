"""NSGA-II solver (DEAP) for multi-objective feed formulation.

Implements the algorithm configured in proposal Table 3.2: real-coded
individuals, Simulated Binary Crossover (SBX, eta=20), polynomial mutation
(eta=20, p=1/n), tournament selection by dominance + crowding distance, and
NSGA-II environmental selection. After every variation operator the individual
is repaired back onto the bounded simplex (sum of proportions = 1).

Returns the first (non-dominated) Pareto front, filtered to feasible solutions.
"""

from __future__ import annotations

import random

import numpy as np
from deap import base, creator, tools

from app.services.optimization.problem import FeedFormulationProblem
from app.services.optimization.solution import Solution

# DEAP uses module-level creator classes; define once and reuse.
if not hasattr(creator, "FeedFitnessMulti"):
    creator.create("FeedFitnessMulti", base.Fitness, weights=(-1.0, -1.0))
if not hasattr(creator, "FeedIndividual"):
    creator.create("FeedIndividual", list, fitness=creator.FeedFitnessMulti)


def _round_to_multiple_of_four(n: int) -> int:
    # selTournamentDCD requires the population size to be a multiple of 4.
    return max(4, ((n + 3) // 4) * 4)


def run_nsga2(
    problem: FeedFormulationProblem,
    population_size: int = 150,
    max_generations: int = 500,
    crossover_prob: float = 0.9,
    sbx_eta: float = 20.0,
    mutation_eta: float = 20.0,
    seed: int | None = None,
) -> list[Solution]:
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    pop_size = _round_to_multiple_of_four(population_size)
    low = problem.lower_bounds.tolist()
    up = problem.upper_bounds.tolist()
    n = problem.n
    mut_indpb = 1.0 / n

    toolbox = base.Toolbox()

    def make_individual() -> "creator.FeedIndividual":
        x = np.random.uniform(problem.lower_bounds, problem.upper_bounds)
        x = problem.repair(x)
        return creator.FeedIndividual(x.tolist())

    def evaluate(ind: list) -> tuple[float, float]:
        return problem.evaluate(np.asarray(ind))

    def repair_in_place(ind: list) -> None:
        ind[:] = problem.repair(np.asarray(ind)).tolist()

    toolbox.register("individual", make_individual)
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)
    toolbox.register("evaluate", evaluate)
    toolbox.register(
        "mate", tools.cxSimulatedBinaryBounded, low=low, up=up, eta=sbx_eta
    )
    toolbox.register(
        "mutate",
        tools.mutPolynomialBounded,
        low=low,
        up=up,
        eta=mutation_eta,
        indpb=mut_indpb,
    )
    toolbox.register("select", tools.selNSGA2)

    pop = toolbox.population(n=pop_size)
    for ind, fit in zip(pop, map(toolbox.evaluate, pop)):
        ind.fitness.values = fit
    # Assign crowding distance via an initial environmental selection.
    pop = toolbox.select(pop, pop_size)

    for _ in range(max_generations):
        offspring = tools.selTournamentDCD(pop, pop_size)
        offspring = [toolbox.clone(ind) for ind in offspring]

        for c1, c2 in zip(offspring[::2], offspring[1::2]):
            if random.random() <= crossover_prob:
                toolbox.mate(c1, c2)
            toolbox.mutate(c1)
            toolbox.mutate(c2)
            repair_in_place(c1)
            repair_in_place(c2)
            del c1.fitness.values
            del c2.fitness.values

        invalid = [ind for ind in offspring if not ind.fitness.valid]
        for ind, fit in zip(invalid, map(toolbox.evaluate, invalid)):
            ind.fitness.values = fit

        pop = toolbox.select(pop + offspring, pop_size)

    front = tools.sortNondominated(pop, len(pop), first_front_only=True)[0]

    # Convert to feasible Solutions, recomputing clean (un-penalised) objectives.
    solutions: list[Solution] = []
    seen: set[tuple[int, ...]] = set()
    for ind in front:
        x = problem.repair(np.asarray(ind))
        if not problem.is_feasible(x):
            continue
        rounded = tuple(int(v) for v in np.round(x * 1e5))
        if rounded in seen:
            continue
        seen.add(rounded)
        solutions.append(
            Solution(
                proportions=x,
                cost=problem.cost(x),
                dtsi=problem.dtsi(x),
                feasible=True,
            )
        )

    solutions.sort(key=lambda s: s.cost)
    return solutions
