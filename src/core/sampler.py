"""
智能抽样器
"""
import logging
from collections import defaultdict
from random import sample, shuffle, choices

logger = logging.getLogger(__name__)


class SmartSampler:
    def __init__(self, use_weighted=False, shuffle_before=True):
        self.use_weighted = use_weighted
        self.shuffle_before = shuffle_before
        self.selection_history = defaultdict(int)
        self.total_selections = 0

    def smart_sample(self, population, k):
        if not population:
            return []
        if k >= len(population):
            result = population.copy()
            shuffle(result)
            return result[:k] if k > len(population) else result
        if self.use_weighted:
            return self._weighted_sample(population, k)
        else:
            return self._simple_sample(population, k)

    def _simple_sample(self, population, k):
        working_population = population.copy()
        if self.shuffle_before:
            shuffle(working_population)
        result = sample(working_population, k)
        self._update_history(result)
        return result

    def _weighted_sample(self, population, k):
        weights = []
        for item in population:
            weight = 1.0 - (self.selection_history.get(item, 0) * 0.1)
            weight = max(0.1, weight)
            weights.append(weight)

        result = []
        temp_population = population.copy()
        temp_weights = weights.copy()
        for _ in range(k):
            if not temp_population:
                break
            selected = choices(temp_population, weights=temp_weights, k=1)[0]
            result.append(selected)
            idx = temp_population.index(selected)
            temp_population.pop(idx)
            temp_weights.pop(idx)

        self._update_history(result)
        return result

    def _update_history(self, selected_items):
        for item in selected_items:
            self.selection_history[item] += 1
        self.total_selections += 1

    def get_selection_stats(self):
        most = max(self.selection_history.items(), key=lambda x: x[1]) if self.selection_history else None
        least = min(self.selection_history.items(), key=lambda x: x[1]) if self.selection_history else None
        return {
            'total_selections': self.total_selections,
            'selection_counts': dict(self.selection_history),
            'most_selected': most,
            'least_selected': least,
        }

    def reset_history(self):
        self.selection_history.clear()
        self.total_selections = 0