"""随机抽样核心逻辑：支持基本、智能和高级三种模式。

三种模式的职责：
  - 基本模式：纯随机抽样；
  - 智能模式：按近期抽取历史自动降权，可叠加用户自定义权重；
  - 高级模式：放回/不放回、抽取优化、多次取最值、加权等完整策略。

实现约定：
  - 单次抽取内结果互不相同（不带重复样本），需要重复样本请用不放回式的多轮抽取；
  - 权重只是相对倍数，0 权重样本不会被抽中，全 0 权重退化为等概率。
"""
from random import choices, randrange, sample, shuffle, uniform
from collections import Counter, defaultdict


def _normalize_weights(weights):
    """把权重列表归一化为和为 1 的概率列表

    - 负数权重按 0 处理（random.choices 要求非负）；
    - 全部为 0 时返回 None，由调用方决定退化为等概率还是随机选取。
    """
    safe = [w if w > 0 else 0.0 for w in weights]
    total = sum(safe)
    if total <= 0:
        return None
    return [w / total for w in safe]


def _as_int(value, default):
    """宽松取整：配置值异常时退回默认值"""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value, default):
    """宽松取浮点：配置值异常时退回默认值"""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _remaining_items(population, picked):
    """population 中未被 picked 取走的部分（按重数扣除，允许重复项）"""
    left = Counter(picked)
    remaining = []
    for item in population:
        if left[item] > 0:
            left[item] -= 1
        else:
            remaining.append(item)
    return remaining


class SmartSampler:
    """三档抽样器：基础随机、智能加权和高级策略。"""

    MODE_BASIC = 0
    MODE_SMART = 1
    MODE_ADVANCED = 2

    MODE_NAMES = {0: "基本抽样", 1: "智能抽样", 2: "高级抽样"}

    # 高级模式：不放回调整方法
    NO_REPLACE_METHOD_CONTINUOUS = 0   # 连续循环样本
    NO_REPLACE_METHOD_DIVISIBLE = 1    # 整除式重载
    NO_REPLACE_METHOD_RATIO = 2        # 比率式调整

    NO_REPLACE_METHOD_NAMES = {
        0: "连续循环样本",
        1: "整除式重载",
        2: "比率式调整",
    }

    # 智能降权：记忆窗口内每被抽中一次扣减的权重，以及权重下限
    SMART_DECAY = 0.35
    SMART_MIN_WEIGHT = 0.1

    def __init__(self, mode=MODE_BASIC, smart_window=3):
        """
        Args:
            mode: 抽样模式 (MODE_BASIC / MODE_SMART / MODE_ADVANCED)
            smart_window: 智能模式下追踪的历史抽取次数
        """
        self.mode = mode
        self.smart_window = smart_window

        # 智能模式：最近几次抽取记录（list of set，最新在前）
        self._recent_history = []

        # 智能模式：是否使用固定权重（用户自定义权重）
        self.use_fixed_weights = False

        # 权重字典 {item: float}（智能模式固定权重 + 高级模式自定义权重共用）
        self.weights = {}

        # 统计
        self.selection_history = defaultdict(int)
        self.total_selections = 0

        # ── 高级模式配置 ──
        self.advanced_config = {
            # 抽取方式
            "with_replacement": True,        # True=放回式, False=不放回式
            "no_replace_method": self.NO_REPLACE_METHOD_CONTINUOUS,  # 不放回调整方法
            "no_replace_ratio": 0.5,         # 比率式调整的阈值 (0.10~0.50)

            # 抽取优化
            "shuffle_before": False,         # 抽取前打乱
            "shuffle_count": 1,              # 打乱次数 (1~10)
            "shuffle_frequency": "each",     # "each"=每次, "once"=仅启动时

            "pre_draw_balance": False,       # 预抽取平衡
            "pre_draw_count": 1,             # 预抽取次数 (1~10)
            "pre_draw_frequency": "each",    # "each"=每次, "once"=仅启动时

            "multi_draw_best": False,        # 多次取最值
            "multi_draw_count": 3,           # 后台抽取次数 (2+)

            "random_weights": False,         # 随机定权重
            "random_weight_min": 0.10,       # 随机权重最小值
            "random_weight_max": 2.00,       # 随机权重最大值

            "progressive_draw": False,       # 递进式抽取

            # 加权抽取
            "smart_reduce_weight": True,     # 智能降权/配权
            "smart_memory_count": 5,         # 记忆次数
            "custom_weights": False,         # 自定义权重
        }

        # 高级模式：不放回状态跟踪
        self._remaining_pool = []           # 当前剩余可抽取池
        self._shuffle_done_once = False     # "仅启动时"打乱是否已执行
        self._pre_draw_done_once = False    # "仅启动时"预抽取是否已执行

    # ══════════════════════════════════════════════════════
    #  模式切换
    # ══════════════════════════════════════════════════════

    def set_mode(self, mode):
        if mode in (self.MODE_BASIC, self.MODE_SMART, self.MODE_ADVANCED):
            self.mode = mode
            # 切换到高级模式时，重置不放回状态
            if mode == self.MODE_ADVANCED:
                self.reset_no_replace_pool()

    # ══════════════════════════════════════════════════════
    #  权重设置
    # ══════════════════════════════════════════════════════

    def set_weight(self, item, weight):
        """设置单个样本的权重（智能模式固定权重 / 高级模式自定义权重）"""
        self.weights[item] = max(0.0, _as_float(weight, 1.0))

    def set_weights_batch(self, items_with_weights):
        """批量设置权重 items_with_weights: [(item, weight), ...]"""
        for item, w in items_with_weights:
            self.set_weight(item, w)

    def get_weight(self, item):
        """获取单个样本的权重，未设置时默认为 1.0"""
        return self.weights.get(item, 1.0)

    def reset_weights(self):
        """重置所有权重"""
        self.weights.clear()

    # ══════════════════════════════════════════════════════
    #  智能权重
    # ══════════════════════════════════════════════════════

    def _recent_counts(self):
        """统计智能记忆窗口内各样本被抽中的次数（每次抽取只统计一遍）"""
        counts = Counter()
        for hist_set in self._recent_history:
            counts.update(hist_set)
        return counts

    def _smart_weight(self, counts, item):
        """由近期次数推算智能权重：被抽中越频繁，权重越低"""
        if not counts:
            return 1.0
        return max(self.SMART_MIN_WEIGHT,
                   1.0 - counts.get(item, 0) * self.SMART_DECAY)

    def get_smart_effective_weight(self, item):
        """获取智能模式下某样本的有效权重（即智能算法计算出的动态权重）"""
        return self._smart_weight(self._recent_counts(), item)

    def _combine_weights(self, population, custom=None, smart=True):
        """组合权重：智能降权 × 用户自定义权重

        Args:
            population: 候选总体
            custom: {item: weight} 字典；None 表示不使用自定义权重
            smart: 是否叠加智能降权

        Returns:
            与 population 等长的权重列表
        """
        counts = self._recent_counts() if smart else Counter()
        weights = []
        for item in population:
            w = self._smart_weight(counts, item)
            if custom is not None:
                w *= custom.get(item, 1.0)
            weights.append(w)
        return weights

    # ══════════════════════════════════════════════════════
    #  核心抽样入口
    # ══════════════════════════════════════════════════════

    def smart_sample(self, population, k):
        """执行抽样（根据当前模式自动选择算法）

        Args:
            population: 样本总体（列表或可迭代对象）
            k: 抽取数量

        Returns:
            抽取结果列表（数量不超过样本总数）
        """
        if k <= 0:
            return []
        pop = list(population)
        if not pop:
            return []

        # 抽取数量 >= 总数 → 打乱后全部返回
        if k >= len(pop):
            result = pop[:]
            shuffle(result)
            if (self.mode == self.MODE_ADVANCED
                    and not self.advanced_config.get("with_replacement", True)):
                # 不放回池已抽空，重置以便下一轮从完整样本重新开始
                self._remaining_pool = []
            self._update_history(result)
            return result

        if self.mode == self.MODE_BASIC:
            result = self._basic_sample(pop, k)
        elif self.mode == self.MODE_SMART:
            result = self._smart_sample(pop, k)
        else:  # MODE_ADVANCED
            result = self._advanced_sample(pop, k)

        self._update_history(result)
        return result

    # ══════════════════════════════════════════════════════
    #  基本 / 智能模式
    # ══════════════════════════════════════════════════════

    def _basic_sample(self, population, k):
        """模式 0：纯随机抽样"""
        return sample(population, k)

    def _smart_sample(self, population, k):
        """模式 1：智能抽样 — 根据近期历史调整权重，避免连续选中相同项；
        启用了固定权重时，在智能权重基础上叠加用户自定义权重。
        """
        custom = self.weights if (self.use_fixed_weights and self.weights) else None
        if custom is None and not self._recent_history:
            # 无历史、无自定义权重 → 纯随机
            return sample(population, k)
        return self._weighted_select(
            population, k, self._combine_weights(population, custom=custom))

    # ══════════════════════════════════════════════════════
    #  高级模式
    # ══════════════════════════════════════════════════════

    def _advanced_sample(self, population, k):
        """模式 2：高级抽样 — 按放回/不放回分发"""
        if not self.advanced_config.get("with_replacement", True):
            return self._advanced_no_replace(population, k)
        return self._advanced_replace(population, k)

    def _advanced_weights(self, population):
        """高级模式的权重列表；返回 None 表示本次按等概率抽取"""
        cfg = self.advanced_config
        use_custom = bool(cfg.get("custom_weights", False)) and bool(self.weights)
        smart_on = bool(cfg.get("smart_reduce_weight", True))
        if not use_custom and not smart_on:
            return None
        return self._combine_weights(
            population,
            custom=self.weights if use_custom else None,
            smart=smart_on,
        )

    def _advanced_replace(self, population, k):
        """放回式：每次都在完整样本中抽，可叠加抽取优化与加权"""
        cfg = self.advanced_config
        pop = list(population)

        # 1) 随机定权重（与自定义权重互斥，界面已保证）
        if cfg.get("random_weights"):
            w_min = _as_float(cfg.get("random_weight_min"), 0.10)
            w_max = _as_float(cfg.get("random_weight_max"), 2.00)
            if w_min > w_max:
                w_min, w_max = w_max, w_min
            return self._weighted_select(
                pop, k, [uniform(w_min, w_max) for _ in pop])

        # 2) 递进式抽取
        if cfg.get("progressive_draw"):
            return self._progressive_draw(pop, k)

        # 3) 抽取前打乱 / 4) 预抽取平衡
        self._apply_draw_optimizations(pop, k)

        # 5) 多次取最值
        weights = self._advanced_weights(pop)
        if cfg.get("multi_draw_best"):
            return self._multi_draw_best(pop, k, weights)

        # 6) 加权抽取（自定义权重 / 智能降权）
        if weights is not None:
            return self._weighted_select(pop, k, weights)

        # 默认：纯随机
        return sample(pop, k)

    def _advanced_no_replace(self, population, k):
        """不放回式：整池打乱后按顺序取，取空再重载

        三个调整方法只在“剩余样本不足 k 个”时才产生差别。
        """
        if not population:
            return []

        cfg = self.advanced_config
        method = cfg.get("no_replace_method", self.NO_REPLACE_METHOD_CONTINUOUS)

        if not self._remaining_pool:
            self._remaining_pool = self._fresh_pool(population)
        elif method == self.NO_REPLACE_METHOD_RATIO:
            ratio = min(0.50, max(0.10, _as_float(cfg.get("no_replace_ratio"), 0.5)))
            if len(self._remaining_pool) <= int(len(population) * ratio):
                # 剩余样本低于阈值 → 重载整池
                self._remaining_pool = self._fresh_pool(population)

        remaining = self._remaining_pool
        if k <= len(remaining):
            self._remaining_pool = remaining[k:]
            return remaining[:k]

        if method == self.NO_REPLACE_METHOD_CONTINUOUS:
            # 连续循环：先取剩余样本，再重载补足
            result = list(remaining)
            need = k - len(result)
            while need > 0:
                fresh = self._fresh_pool(population)
                take = min(need, len(fresh))
                result.extend(fresh[:take])
                self._remaining_pool = fresh[take:]
                need -= take
            return result

        # 整除式 / 比率式：直接重载整池进入下一轮
        fresh = self._fresh_pool(population)
        self._remaining_pool = fresh[k:]
        return fresh[:k]

    def _progressive_draw(self, population, k):
        """递进式抽取：每轮把候选池缩小一半，最后从最小的集合里抽取
        例：50→25→13→7→4→2→1
        """
        current = self._fresh_pool(population)
        while len(current) > max(k, 2):
            current = sample(current, max(1, len(current) // 2))
        if len(current) >= k:
            return sample(current, k)
        # 递进后不足 k 个：从剩余样本中补足
        remaining = _remaining_items(population, current)
        need = k - len(current)
        return current + sample(remaining, min(need, len(remaining)))

    def _multi_draw_best(self, population, k, weights=None):
        """多次取最值：后台抽若干次，取被抽中次数最多的前 k 个

        Args:
            weights: 与 population 等长的权重列表；None 表示等概率后台抽取
        """
        cfg = self.advanced_config
        times = max(2, min(len(population),
                           _as_int(cfg.get("multi_draw_count"), 3)))
        counter = Counter()
        for _ in range(times):
            drawn = (sample(population, k) if weights is None
                     else self._weighted_select(population, k, weights))
            counter.update(drawn)

        # 先打散再按次数排序：同次数的样本顺序随机，避免偏向名字靠前的样本
        ranked = list(counter.items())
        shuffle(ranked)
        ranked.sort(key=lambda pair: -pair[1])
        result = [item for item, _ in ranked[:k]]

        if len(result) < k:
            # 补足：从未被抽中的样本中随机选取
            remaining = _remaining_items(population, result)
            result.extend(sample(remaining, min(k - len(result), len(remaining))))
        return result

    # ── 抽取优化 ──────────────────────────────────────────

    def _apply_draw_optimizations(self, population, k):
        """抽取前打乱 / 预抽取平衡

        预抽取平衡为后台空抽（结果丢弃），只用于打散随机状态。
        """
        cfg = self.advanced_config

        if cfg.get("shuffle_before") and self._should_run(
                cfg.get("shuffle_frequency", "each"), "_shuffle_done_once"):
            count = max(1, min(10, _as_int(cfg.get("shuffle_count"), 1)))
            for _ in range(count):
                shuffle(population)

        if cfg.get("pre_draw_balance") and self._should_run(
                cfg.get("pre_draw_frequency", "each"), "_pre_draw_done_once"):
            count = max(1, min(10, _as_int(cfg.get("pre_draw_count"), 1)))
            for _ in range(count):
                sample(population, min(k, len(population)))

    def _should_run(self, frequency, done_flag):
        """按“每次 / 仅启动时”判断优化项是否执行

        done_flag 为记录“已执行过”的属性名，仅 "once" 时会被置位。
        """
        if frequency == "once":
            if getattr(self, done_flag):
                return False
            setattr(self, done_flag, True)
            return True
        return frequency == "each"

    @staticmethod
    def _fresh_pool(population):
        """复制并打乱一份新的样本池"""
        pool = list(population)
        shuffle(pool)
        return pool

    # ══════════════════════════════════════════════════════
    #  加权抽取
    # ══════════════════════════════════════════════════════

    def _weighted_select(self, population, k, weights, replace=False):
        """带权重的抽样（通用实现）

        Args:
            population: 候选总体
            k: 抽取数量
            weights: 与 population 等长的权重列表（0 权重不会被抽中）
            replace: True=有放回（同一项可被重复抽中）；
                     False=无放回（抽取结果互不相同，默认）

        无放回时逐次归一化并剔除已抽中的项，等价于按权重依次抽取。
        """
        if not population or k <= 0:
            return []

        pool = list(population)
        pool_w = [max(0.0, _as_float(w, 0.0)) for w in weights]

        # ── 有放回：按归一化权重独立抽取 k 次 ──
        if replace:
            norm = _normalize_weights(pool_w)
            if norm is None:  # 权重全为 0 → 退化为等概率
                norm = [1.0] * len(pool)
            return choices(pool, weights=norm, k=k)

        # ── 无放回：抽一个移除一个 ──
        result = []
        while pool and len(result) < k:
            norm = _normalize_weights(pool_w)
            if norm is None:
                # 权重全为 0 → 等概率随机取一个
                idx = randrange(len(pool))
            else:
                idx = choices(range(len(pool)), weights=norm, k=1)[0]
            result.append(pool.pop(idx))
            pool_w.pop(idx)
        return result

    # ══════════════════════════════════════════════════════
    #  状态重置 / 历史统计
    # ══════════════════════════════════════════════════════

    def reset_no_replace_pool(self):
        """重置不放回抽取池（切换样本或手动重置时调用）"""
        self._remaining_pool = []
        self._shuffle_done_once = False
        self._pre_draw_done_once = False

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
        """重置所有历史记录（智能模式的近期记录 + 统计计数 + 高级模式不放回状态）"""
        self._recent_history.clear()
        self.selection_history.clear()
        self.total_selections = 0
        self.reset_no_replace_pool()
