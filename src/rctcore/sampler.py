"""
底层随机抽取逻辑运算模块
（注：当前模块为半成品，后续更新）
"""
# 导入必要的基本库
from random import sample, shuffle, choices
from collections import defaultdict

class SmartSampler:
    """智能抽样器"""
    
    def __init__(self, use_weighted=False, shuffle_before=True):
        """
        初始化抽样器
        
        Args:
            use_weighted: 是否使用加权抽样
            shuffle_before: 是否在抽样前打乱
        """
        self.use_weighted = use_weighted
        self.shuffle_before = shuffle_before
        self.selection_history = defaultdict(int)  # 记录选中次数
        self.total_selections = 0  # 总抽取次数
        
    def smart_sample(self, population, k):
        """
        智能抽样
        
        Args:
            population: 总体列表
            k: 抽取数量
            
        Returns:
            抽取结果列表
        """
        if not population:
            return []
        
        # 如果k大于或等于总体数量，直接返回整个总体（打乱后）
        if k >= len(population):
            result = population.copy()
            shuffle(result)
            return result[:k] if k > len(population) else result
        
        if self.use_weighted:
            return self._weighted_sample(population, k)
        else:
            return self._simple_sample(population, k)
    
    def _simple_sample(self, population, k):
        """简单随机抽样（可先打乱）"""
        working_population = population.copy()
        
        if self.shuffle_before:
            shuffle(working_population)
        
        # 使用sample进行无放回抽样
        result = sample(working_population, k)
        
        # 更新历史记录
        self._update_history(result)
        
        return result
    
    def _weighted_sample(self, population, k):
        """加权随机抽样"""
        # 计算每个元素的权重：选中次数越少，权重越高
        weights = []
        for item in population:
            # 基础权重为1，每被选中一次减少0.1权重
            weight = 1.0 - (self.selection_history.get(item, 0) * 0.1)
            weight = max(0.1, weight)  # 最小权重为0.1
            weights.append(weight)
        
        # 使用加权抽样（无放回）
        result = []
        temp_population = population.copy()
        temp_weights = weights.copy()
        
        for _ in range(k):
            if not temp_population:
                break
                
            # 根据权重随机选择一个
            selected = choices(temp_population, weights=temp_weights, k=1)[0]
            result.append(selected)
            
            # 从临时列表中移除已选中的
            idx = temp_population.index(selected)
            temp_population.pop(idx)
            temp_weights.pop(idx)
        
        # 更新历史记录
        self._update_history(result)
        
        return result
    
    def _update_history(self, selected_items):
        """更新选中历史"""
        for item in selected_items:
            self.selection_history[item] += 1
        self.total_selections += 1
    
    def get_selection_stats(self):
        """获取选中统计"""
        return {
            'total_selections': self.total_selections,
            'selection_counts': dict(self.selection_history),
            'most_selected': max(self.selection_history.items(), key=lambda x: x[1]) if self.selection_history else None,
            'least_selected': min(self.selection_history.items(), key=lambda x: x[1]) if self.selection_history else None,
        }
    
    def reset_history(self):
        """重置历史记录"""
        self.selection_history.clear()
        self.total_selections = 0
