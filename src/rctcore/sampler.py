"""
底层随机抽取逻辑 — 三档抽样模式（基本/智能/高级）
"""
from random import sample, shuffle, choices, random, uniform
from collections import defaultdict, Counter
from core.logman import rctlog


class SmartSampler:
    """智能抽样器 — 三档抽样模式

    模式 0 - 基本抽样 (BASIC) : random.sample，简单随机
    模式 1 - 智能抽样 (SMART) : 跟踪近期抽取历史，自动降低刚被选中项的权重；
                               支持"使用固定权重"子选项，整合原加权功能
    模式 2 - 高级抽样 (ADVANCED) : 开放全部高级抽取选项（放回/不放回、抽取优化等）
    """

    MODE_BASIC = 0
    MODE_SMART = 1
    MODE_ADVANCED = 2

    MODE_NAMES = {0: "基本抽样", 1: "智能抽样", 2: "高级抽样"}

    # ── 高级模式：不放回调整方法 ──
    NO_REPLACE_METHOD_CONTINUOUS = 0   # 连续循环样本
    NO_REPLACE_METHOD_DIVISIBLE = 1    # 整除式重载
    NO_REPLACE_METHOD_RATIO = 2        # 比率式调整

    NO_REPLACE_METHOD_NAMES = {
        0: "连续循环样本",
        1: "整除式重载",
        2: "比率式调整",
    }

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
            "smart_memory_count": 3,         # 记忆次数
            "custom_weights": False,         # 自定义权重
        }

        # 高级模式：不放回状态跟踪
        self._remaining_pool = []           # 当前剩余可抽取池
        self._shuffle_done_once = False     # "仅启动时"打乱是否已执行
        self._pre_draw_done_once = False    # "仅启动时"预抽取是否已执行

    # ── 模式切换 ──────────────────────────────────────────

    def set_mode(self, mode):
        if mode in (self.MODE_BASIC, self.MODE_SMART, self.MODE_ADVANCED):
            self.mode = mode
            # 切换到高级模式时，重置不放回状态
            if mode == self.MODE_ADVANCED:
                self._remaining_pool = []
                self._shuffle_done_once = False
                self._pre_draw_done_once = False

    # ── 权重设置 ──────────────────────────────────────────

    def set_weight(self, item, weight):
        """设置单个样本的权重（智能模式固定权重 / 高级模式自定义权重）"""
        self.weights[item] = max(0.0, float(weight))

    def get_weight(self, item):
        """获取单个样本的权重，未设置时默认为 1.0"""
        return self.weights.get(item, 1.0)

    def get_smart_effective_weight(self, item):
        """获取智能模式下某样本的有效权重（即智能算法计算出的动态权重）"""
        if not self._recent_history:
            return 1.0
        recent_counts = Counter()
        for hist_set in self._recent_history:
            for i in hist_set:
                recent_counts[i] += 1
        count = recent_counts.get(item, 0)
        w = 1.0 - (count * 0.35)
        return max(0.1, w)

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
        else:  # MODE_ADVANCED
            result = self._advanced_sample(pop_list, k)

        self._update_history(result)
        return result

    # ── 各模式实现 ────────────────────────────────────────

    def _basic_sample(self, population, k):
        """模式 0：纯随机抽样"""
        return sample(population, k)

    def _smart_sample(self, population, k):
        """模式 1：智能抽样 — 根据近期历史调整权重，避免连续选中相同项；
        如果启用了固定权重，则在智能权重基础上叠加用户自定义权重。
        """
        # 计算智能动态权重
        smart_weights = []
        for item in population:
            smart_weights.append(self.get_smart_effective_weight(item))

        if self.use_fixed_weights and self.weights:
            # 叠加用户固定权重（乘积方式）
            final_weights = []
            for i, item in enumerate(population):
                user_w = self.weights.get(item, 1.0)
                final_weights.append(smart_weights[i] * user_w)
            return self._weighted_select(population, k, final_weights)

        # 仅智能权重（如无历史则纯随机）
        if not self._recent_history:
            return sample(population, k)
        return self._weighted_select(population, k, smart_weights)

    def _advanced_sample(self, population, k):
        """模式 2：高级抽样 — 支持放回/不放回、抽取优化、加权等"""
        cfg = self.advanced_config
        pop = population.copy()

        # ── 不放回模式 ──
        if not cfg["with_replacement"]:
            return self._advanced_no_replace(pop, k)

        # ── 放回模式：应用抽取优化 ──

        # 1) 随机定权重
        if cfg["random_weights"]:
            w_min = cfg.get("random_weight_min", 0.10)
            w_max = cfg.get("random_weight_max", 2.00)
            temp_weights = {item: uniform(w_min, w_max) for item in pop}
            return self._weighted_select(
                pop, k, [temp_weights.get(item, 1.0) for item in pop]
            )

        # 2) 递进式抽取
        if cfg["progressive_draw"]:
            return self._progressive_draw(pop, k)

        # 3) 抽取前打乱
        should_shuffle = False
        if cfg["shuffle_before"]:
            if cfg.get("shuffle_frequency", "each") == "each":
                should_shuffle = True
            elif cfg.get("shuffle_frequency") == "once" and not self._shuffle_done_once:
                should_shuffle = True
                self._shuffle_done_once = True

        if should_shuffle:
            sc = max(1, min(10, cfg.get("shuffle_count", 1)))
            for _ in range(sc):
                shuffle(pop)

        # 4) 预抽取平衡
        should_pre_draw = False
        if cfg["pre_draw_balance"]:
            if cfg.get("pre_draw_frequency", "each") == "each":
                should_pre_draw = True
            elif cfg.get("pre_draw_frequency") == "once" and not self._pre_draw_done_once:
                should_pre_draw = True
                self._pre_draw_done_once = True

        if should_pre_draw:
            pd_count = max(1, min(10, cfg.get("pre_draw_count", 1)))
            for _ in range(pd_count):
                # 后台静默预抽取
                sample(pop, min(k, len(pop)))

        # 5) 多次取最值
        if cfg["multi_draw_best"]:
            mc = max(2, min(len(pop), cfg.get("multi_draw_count", 3)))
            counter = Counter()
            for _ in range(mc):
                drawn = sample(pop, k)
                for item in drawn:
                    counter[item] += 1
            # 按被抽次数降序，取前k个
            sorted_items = sorted(counter.items(), key=lambda x: (-x[1], x[0]))
            result = [item for item, _ in sorted_items[:k]]
            if len(result) < k:
                # 补足：从未被抽到的样本中随机选取
                remaining = [item for item in pop if item not in result]
                result.extend(sample(remaining, k - len(result)))
            return result

        # 6) 加权模式（自定义权重 / 智能降权）
        if cfg.get("custom_weights") and self.weights:
            return self._weighted_select(
                pop, k, [self.weights.get(item, 1.0) for item in pop]
            )

        if cfg.get("smart_reduce_weight", True):
            # 智能降权
            smart_weights = [self.get_smart_effective_weight(item) for item in pop]
            if self.weights and cfg.get("custom_weights"):
                smart_weights = [
                    smart_weights[i] * self.weights.get(item, 1.0)
                    for i, item in enumerate(pop)
                ]
            return self._weighted_select(pop, k, smart_weights)

        # 默认：纯随机
        return sample(pop, k)

    def _advanced_no_replace(self, population, k):
        """不放回式抽取"""
        cfg = self.advanced_config

        # 初始化或检查剩余池
        if not self._remaining_pool:
            self._remaining_pool = population.copy()
            shuffle(self._remaining_pool)

        remaining = self._remaining_pool

        # 比率式调整
        if cfg.get("no_replace_method") == self.NO_REPLACE_METHOD_RATIO:
            ratio = max(0.10, min(0.50, cfg.get("no_replace_ratio", 0.5)))
            if len(remaining) <= int(len(population) * ratio):
                remaining = population.copy()
                shuffle(remaining)
                self._remaining_pool = remaining

        if k <= len(remaining):
            # 足够抽取
            result = remaining[:k]
            self._remaining_pool = remaining[k:]
            return result

        # 不够抽取，根据调整方法处理
        method = cfg.get("no_replace_method", self.NO_REPLACE_METHOD_CONTINUOUS)

        if method == self.NO_REPLACE_METHOD_CONTINUOUS:
            # 连续循环：先取剩余的，再重载补足
            result = list(remaining)
            need = k - len(result)
            new_pool = population.copy()
            shuffle(new_pool)
            result.extend(new_pool[:need])
            self._remaining_pool = new_pool[need:]
            return result

        elif method == self.NO_REPLACE_METHOD_DIVISIBLE:
            # 整除式重载：直接重载进入下一次循环
            new_pool = population.copy()
            shuffle(new_pool)
            result = new_pool[:k]
            self._remaining_pool = new_pool[k:]
            return result

        else:
            # 比率式（已在上方处理，这里作为fallback）
            new_pool = population.copy()
            shuffle(new_pool)
            result = new_pool[:k]
            self._remaining_pool = new_pool[k:]
            return result

    def _progressive_draw(self, population, k):
        """递进式抽取：样本中以一半数量层层递进式抽取
        例：50→25→13→7→4→2→1
        最终从最小的集合中随机取 k 个
        """
        current = population.copy()
        shuffle(current)
        while len(current) > max(k, 2):
            half = max(1, len(current) // 2)
            current = sample(current, half)
        if len(current) >= k:
            return sample(current, k)
        return current

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

    # ── 高级模式：重置不放回状态 ──────────────────────────

    def reset_no_replace_pool(self):
        """重置不放回抽取池（切换样本或手动重置时调用）"""
        self._remaining_pool = []
        self._shuffle_done_once = False
        self._pre_draw_done_once = False

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
        """重置所有历史记录（智能模式的近期记录 + 统计计数 + 高级模式不放回状态）"""
        self._recent_history.clear()
        self.selection_history.clear()
        self.total_selections = 0
        self._remaining_pool = []
        self._shuffle_done_once = False
        self._pre_draw_done_once = False
