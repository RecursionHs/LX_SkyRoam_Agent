"""
预算计算相关功能
"""
import re
from typing import Any, Optional, Dict, Union, List
from loguru import logger


class BudgetCalculator:
    """预算计算器"""
    
    @staticmethod
    def get_per_day_budget(plan: Any) -> Optional[float]:
        """
        计算每日可变预算（用于餐饮、景点、交通）
        
        将总预算分为两部分：
        1. 固定支出（航班+酒店）：占总预算的30-35%
        2. 每日可变支出（餐饮+景点+交通）：占总预算的65-70%，按天均分
        
        这样可以避免每个模块都使用总预算/天数，导致预算被重复使用的问题。
        """
        total_budget = getattr(plan, "budget", None)
        total_days = getattr(plan, "duration_days", None)
        if not total_budget or not total_days:
            return None
        try:
            total_budget = float(total_budget)
            total_days = int(total_days)
            if total_days <= 0:
                return None
            
            # 固定支出（航班+酒店）占30-35%，每日可变支出占65-70%
            # 根据预算规模调整比例：预算越大，固定支出比例可以稍高
            if total_budget >= 10000:
                fixed_ratio = 0.35  # 高预算时，固定支出占35%
            elif total_budget >= 5000:
                fixed_ratio = 0.33  # 中等预算时，固定支出占33%
            else:
                fixed_ratio = 0.30  # 低预算时，固定支出占30%
            
            variable_budget = total_budget * (1 - fixed_ratio)
            per_day_budget = variable_budget / total_days
            
            logger.debug(
                f"预算分配：总预算={total_budget:.0f}元，"
                f"固定支出（航班+酒店）={total_budget * fixed_ratio:.0f}元，"
                f"每日可变预算={per_day_budget:.0f}元/天"
            )
            
            return max(per_day_budget, 0)
        except (TypeError, ValueError):
            return None
    
    @staticmethod
    def get_fixed_budget(plan: Any) -> Optional[float]:
        """
        计算固定支出预算（用于航班+酒店）
        
        固定支出占总预算的30-35%，根据总预算规模调整比例。
        """
        total_budget = getattr(plan, "budget", None)
        if not total_budget:
            return None
        try:
            total_budget = float(total_budget)
            
            # 根据预算规模调整比例
            if total_budget >= 10000:
                fixed_ratio = 0.35
            elif total_budget >= 5000:
                fixed_ratio = 0.33
            else:
                fixed_ratio = 0.30
            
            return max(total_budget * fixed_ratio, 0)
        except (TypeError, ValueError):
            return None
    
    @staticmethod
    def safe_number(value: Any) -> float:
        """将带有货币符号/中文单位的字符串安全转为数字，失败返回0"""
        if isinstance(value, (int, float)):
            try:
                return float(value)
            except (TypeError, ValueError):
                return 0.0
        if isinstance(value, str):
            match = re.search(r"(-?\d+(?:\.\d+)?)", value)
            if match:
                try:
                    return float(match.group(1))
                except (TypeError, ValueError):
                    return 0.0
        return 0.0
    
    @staticmethod
    def coerce_number(value: Any, default: float = 0.0) -> float:
        """Best-effort conversion to float, flattening dict/list containers."""
        if value is None:
            return default
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except (ValueError, TypeError):
                return default
        if isinstance(value, dict):
            if "total" in value:
                return BudgetCalculator.coerce_number(value.get("total"), default)
            subtotal = 0.0
            for sub in value.values():
                subtotal += BudgetCalculator.coerce_number(sub, 0.0)
            return subtotal if subtotal else default
        if isinstance(value, (list, tuple)):
            total = 0.0
            for item in value:
                total += BudgetCalculator.coerce_number(item, 0.0)
            return total if total else default
        return default
    
    @staticmethod
    def calculate_total_cost(
        accommodation: Dict[str, Any], 
        daily_itineraries: List[Dict[str, Any]], 
        duration_days: int
    ) -> Dict[str, Any]:
        """计算总费用"""
        cost_summary = accommodation.get("total_accommodation_cost", {}) or {}
        flight_cost = BudgetCalculator.coerce_number(cost_summary.get("flight", 0))
        hotel_cost = BudgetCalculator.coerce_number(cost_summary.get("hotel", 0))

        attractions_cost = 0.0
        for day in daily_itineraries:
            attractions_cost += BudgetCalculator.coerce_number(day.get("estimated_cost", 0))

        meals_cost = 0.0
        for day in daily_itineraries:
            for meal in day.get("meals", []):
                meals_cost += BudgetCalculator.coerce_number(meal.get("estimated_cost", 0))

        transportation_cost = 100 * duration_days  # 估算每日交通费用

        total = flight_cost + hotel_cost + attractions_cost + meals_cost + transportation_cost
        
        return {
            "flight": flight_cost,
            "hotel": hotel_cost,
            "attractions": attractions_cost,
            "meals": meals_cost,
            "transportation": transportation_cost,
            "total": total
        }