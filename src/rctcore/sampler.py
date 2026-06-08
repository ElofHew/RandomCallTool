"""
底层随机抽取逻辑 — 三档抽样模式
"""
from random import sample, shuffle, choices
from collections import defaultdict, Counter


class SmartSampler:
    """智能抽样器 — 三档抽样模式

    模式 0 - 基本抽样 (BASIC) : random.sample，简单随机
    模式 1 - 智能抽样 (SMART) : 跟踪近期抽取历史，自动降低刚被选中项的权重，避免连续抽到同一个人
    模式 2 - 加权抽样 (WEIGHTED) : 用户可自由为每个样本设置权重
    """

    MODE_BASIC = 0
    MODE_SMART = 1
    MODE_WEIGHTED = 2

    MODE_NAMES = {0: "基本抽样", 1: "智能抽样", 2: "加权抽样"}

    def __init__(self, mode=MODE_BASIC, smart_window=3):
        """
        Args:
            mode: 抽样模式 (MODE_BASIC / MODE_SMART / MODE_WEIGHTED)
            smart_window: 智能模式下追踪的历史抽取次数
        """
        self.mode = mode
        self.smart_window = smart_window

        # 智能模式：最近几次抽取记录（list of set，最新在前）
        self._recent_history = []

        # 加权模式：用户自定义权重 {item: float}
        self.weights = {}

        # 统计
        self.selection_history = defaultdict(int)
        self.total_selections = 0

    # ── 模式切换 ──────────────────────────────────────────

    def set_mode(self, mode):
        if mode in (self.MODE_BASIC, self.MODE_SMART, self.MODE_WEIGHTED):
            self.mode = mode

    # ── 权重设置 ──────────────────────────────────────────

    def set_weight(self, item, weight):
        """设置单个样本的权重（仅加权模式有效）"""
        self.weights[item] = max(0.0, float(weight))

    def get_weight(self, item):
        """获取单个样本的权重，未设置时默认为 1.0"""
        return self.weights.get(item, 1.0)

    def set_weights_batch(self, items_with_weights):
        """批量设置权重 items_with_weights: [(item, weight), ...]"""
        for item, w in items_with_weights:
            self.weights[item] = max(0.0, float(w))

    def reset_weights(self):
        """重置所有权重"""
        self.weights.clear()

    # ── 核心抽样入口 ──────────────────────────────────────

    def smart_sample(self, population, k):
        """
        执行抽样（根据当前模式自动选择算法）

        Args:
            population: 样本总体（列表或可迭代对象）
            k: 抽取数量

        Returns:
            抽取结果列表
        """
        if not population or k <= 0:
            return []

        pop_list = list(population)

        # 抽取数量 >= 总数 → 打乱后返回
        if k >= len(pop_list):
            result = pop_list.copy()
            shuffle(result)
            self._update_history(result)
            return result[:k] if k > len(pop_list) else result

        if self.mode == self.MODE_BASIC:
            result = self._basic_sample(pop_list, k)
        elif self.mode == self.MODE_SMART:
            result = self._smart_sample(pop_list, k)
        else:  # MODE_WEIGHTED
            result = self._weighted_sample(pop_list, k)

        self._update_history(result)
        return result

    # ── 各模式实现 ────────────────────────────────────────

    def _basic_sample(self, population, k):
        """模式 0：纯随机抽样"""
        return sample(population, k)

    def _smart_sample(self, population, k):
        """模式 1：智能抽样 — 根据近期历史调整权重，避免连续选中相同项"""
        if not self._recent_history:
            return sample(population, k)

        # 统计近期历史中每个项的出现次数
        recent_counts = Counter()
        for hist_set in self._recent_history:
            for item in hist_set:
                recent_counts[item] += 1

        weights = []
        for item in population:
            count = recent_counts.get(item, 0)
            # 每次出现降低 0.35 权重
            w = 1.0 - (count * 0.35)
            w = max(0.1, w)  # 最低保底权重 0.1
            weights.append(w)

        return self._weighted_select(population, k, weights)

    def _weighted_sample(self, population, k):
        """模式 2：用户自定义加权抽样"""
        weights = [self.weights.get(item, 1.0) for item in population]
        return self._weighted_select(population, k, weights)

    def _weighted_select(self, population, k, weights):
        """带权重的无放回抽样（通用实现）"""
        result = []
        temp_pop = population.copy()
        temp_w = weights.copy()

        for _ in range(k):
            if not temp_pop:
                break
            total = sum(temp_w)
            if total <= 0:
                selected = sample(temp_pop, 1)[0]
            else:
                norm = [w / total for w in temp_w]
                selected = choices(temp_pop, weights=norm, k=1)[0]

            result.append(selected)
            idx = temp_pop.index(selected)
            temp_pop.pop(idx)
            temp_w.pop(idx)

        return result

    # ── 历史与统计 ────────────────────────────────────────

    def _update_history(self, selected_items):
        """更新抽取历史（智能模式使用 + 统计计数）"""
        self._recent_history.insert(0, set(selected_items))
        if len(self._recent_history) > self.smart_window:
            self._recent_history.pop()

        for item in selected_items:
            self.selection_history[item] += 1
        self.total_selections += 1

    def get_selection_stats(self):
        """获取选中统计"""
        stats = {
            "total_selections": self.total_selections,
            "selection_counts": dict(self.selection_history),
        }
        if self.selection_history:
            items = list(self.selection_history.items())
            stats["most_selected"] = max(items, key=lambda x: x[1])
            stats["least_selected"] = min(items, key=lambda x: x[1])
        else:
            stats["most_selected"] = None
            stats["least_selected"] = None
        return stats

    def reset_history(self):
        """重置所有历史记录（智能模式的近期记录 + 统计计数）"""
        self._recent_history.clear()
        self.selection_history.clear()
        self.total_selections = 0
