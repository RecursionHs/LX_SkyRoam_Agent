"""
AI Agent核心服务
负责数据收集、处理、方案生成
"""

import asyncio
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
import json
from datetime import datetime

from app.core.config import settings
from app.models.travel_plan import TravelPlan
from app.services.data_collector import DataCollector
from app.services.data_processor import DataProcessor
from app.services.plan_generator import PlanGenerator
from app.services.plan_scorer import PlanScorer
from app.tools.mcp_client import MCPClient
from app.tools.openai_client import openai_client


class AgentService:
    """AI Agent服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.data_collector = DataCollector()
        self.data_processor = DataProcessor()
        self.plan_generator = PlanGenerator()
        self.plan_scorer = PlanScorer()
        self.mcp_client = MCPClient()
        self.openai_client = openai_client
    
    async def generate_travel_plans(
        self, 
        plan_id: int, 
        preferences: Optional[Dict[str, Any]] = None,
        requirements: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        生成旅行方案的主流程
        
        Args:
            plan_id: 旅行计划ID
            preferences: 用户偏好
            requirements: 特殊要求
            
        Returns:
            bool: 是否成功生成
        """
        try:
            logger.info(f"开始生成旅行方案，计划ID: {plan_id}")
            
            # 1. 获取旅行计划信息
            plan = await self._get_travel_plan(plan_id)
            if not plan:
                logger.error(f"旅行计划不存在: {plan_id}")
                return False
            
            # 2. 更新状态为生成中
            await self._update_plan_status(plan_id, "generating")
            
            # 3. 数据收集阶段
            logger.info("开始数据收集...")
            raw_data = await self._collect_data(plan, preferences, requirements)
            
            # 4. 数据清洗和评分
            logger.info("开始数据清洗和评分...")
            processed_data = await self._process_data(raw_data, plan)
            
            # 5. 生成多个方案
            logger.info("开始生成旅行方案...")
            generated_plans = await self._generate_plans(processed_data, plan, preferences)
            
            # 6. 方案评分和排序
            logger.info("开始方案评分和排序...")
            scored_plans = await self._score_plans(generated_plans, plan, preferences)
            
            # 7. 保存结果
            await self._save_generated_plans(plan_id, scored_plans)
            
            # 8. 更新状态为完成
            await self._update_plan_status(plan_id, "completed")
            
            logger.info(f"旅行方案生成完成，计划ID: {plan_id}")
            return True
            
        except Exception as e:
            logger.error(f"生成旅行方案失败: {e}")
            await self._update_plan_status(plan_id, "failed")
            return False
    
    async def _get_travel_plan(self, plan_id: int) -> Optional[TravelPlan]:
        """获取旅行计划"""
        from sqlalchemy import select
        from app.models.travel_plan import TravelPlan
        
        result = await self.db.execute(select(TravelPlan).where(TravelPlan.id == plan_id))
        return result.scalar_one_or_none()
    
    async def _update_plan_status(self, plan_id: int, status: str):
        """更新计划状态"""
        from sqlalchemy import update
        from app.models.travel_plan import TravelPlan
        
        await self.db.execute(
            update(TravelPlan)
            .where(TravelPlan.id == plan_id)
            .values(status=status)
        )
        await self.db.commit()
    
    async def _collect_data(
        self, 
        plan: TravelPlan, 
        preferences: Optional[Dict[str, Any]] = None,
        requirements: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """数据收集阶段"""
        
        # 并行收集各类数据
        tasks = [
            self.data_collector.collect_flight_data(plan.destination, plan.start_date, plan.end_date),
            self.data_collector.collect_hotel_data(plan.destination, plan.start_date, plan.end_date),
            self.data_collector.collect_attraction_data(plan.destination),
            self.data_collector.collect_weather_data(plan.destination, plan.start_date, plan.end_date),
            self.data_collector.collect_restaurant_data(plan.destination),
            self.data_collector.collect_transportation_data(plan.destination)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            "flights": results[0] if not isinstance(results[0], Exception) else [],
            "hotels": results[1] if not isinstance(results[1], Exception) else [],
            "attractions": results[2] if not isinstance(results[2], Exception) else [],
            "weather": results[3] if not isinstance(results[3], Exception) else {},
            "restaurants": results[4] if not isinstance(results[4], Exception) else [],
            "transportation": results[5] if not isinstance(results[5], Exception) else []
        }
    
    async def _process_data(
        self, 
        raw_data: Dict[str, Any], 
        plan: TravelPlan
    ) -> Dict[str, Any]:
        """数据清洗和评分"""
        
        processed_data = {}
        
        for data_type, data in raw_data.items():
            if data_type == "weather":
                # 天气数据不需要清洗
                processed_data[data_type] = data
            else:
                # 其他数据需要清洗和评分
                processed_data[data_type] = await self.data_processor.process_data(
                    data, data_type, plan
                )
        
        return processed_data
    
    async def _enhance_data_with_llm(
        self,
        processed_data: Dict[str, Any],
        plan: TravelPlan,
        preferences: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """使用LLM增强数据"""
        try:
            # 构建数据增强提示
            system_prompt = """你是一个专业的旅行数据分析师，擅长分析和优化旅行相关数据。
请分析提供的旅行数据，并提供优化建议和补充信息。

你需要：
1. 分析现有数据的质量和完整性
2. 识别缺失或不足的信息
3. 提供数据优化建议
4. 补充合理的推荐信息

请以JSON格式返回增强后的数据。"""
            
            user_prompt = f"""
请分析以下旅行数据并增强：

目的地：{plan.destination}
旅行天数：{plan.duration_days}天
预算：{plan.budget}元
用户偏好：{preferences or '无特殊偏好'}

现有数据：
- 航班：{len(processed_data.get('flights', []))}个选项
- 酒店：{len(processed_data.get('hotels', []))}个选项  
- 景点：{len(processed_data.get('attractions', []))}个选项
- 餐厅：{len(processed_data.get('restaurants', []))}个选项
- 交通：{len(processed_data.get('transportation', []))}个选项
- 天气：{processed_data.get('weather', {})}

请分析这些数据，识别需要补充的信息，并提供优化建议。
"""
            
            # 调用LLM分析数据
            analysis_response = await self.openai_client.generate_text(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=2000,
                temperature=0.5
            )
            
            # 尝试解析分析结果
            try:
                # 清理markdown格式
                cleaned_response = self._clean_llm_response(analysis_response)
                analysis_result = json.loads(cleaned_response)
                logger.info("LLM数据增强成功")
                
                # 将分析结果合并到原始数据
                enhanced_data = processed_data.copy()
                enhanced_data['llm_analysis'] = analysis_result
                enhanced_data['enhanced_at'] = datetime.utcnow().isoformat()
                
                return enhanced_data
                
            except json.JSONDecodeError as e:
                logger.warning(f"LLM分析结果不是有效JSON: {e}")
                logger.debug(f"清理后的响应: {cleaned_response}")
                return processed_data
                
        except Exception as e:
            logger.error(f"LLM数据增强失败: {e}")
            return processed_data
    
    def _clean_llm_response(self, response: str) -> str:
        """清理LLM响应，移除markdown标记等"""
        import re
        
        # 移除markdown代码块标记
        cleaned = re.sub(r'```json\s*', '', response)
        cleaned = re.sub(r'```\s*$', '', cleaned)
        cleaned = re.sub(r'```\s*', '', cleaned)  # 移除单独的```
        
        # 移除前后的空白字符
        cleaned = cleaned.strip()
        
        return cleaned
    
    async def _generate_plans(
        self, 
        processed_data: Dict[str, Any], 
        plan: TravelPlan,
        preferences: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """生成多个旅行方案"""
        
        # 使用LLM增强的方案生成
        try:
            # 首先尝试使用LLM分析数据并生成方案
            if self.openai_client.api_key:
                import asyncio
                enhanced_data = await asyncio.wait_for(
                    self._enhance_data_with_llm(processed_data, plan, preferences),
                    timeout=300.0  # 300秒超时
                )
                return await self.plan_generator.generate_plans(
                    enhanced_data, plan, preferences
                )
            else:
                logger.info("OpenAI API密钥未配置，直接使用原始数据")
                return await self.plan_generator.generate_plans(
                    processed_data, plan, preferences
                )
        except asyncio.TimeoutError:
            logger.warning("LLM数据增强超时，使用原始数据")
            return await self.plan_generator.generate_plans(
                processed_data, plan, preferences
            )
        except Exception as e:
            logger.warning(f"LLM增强数据失败，使用原始数据: {e}")
            return await self.plan_generator.generate_plans(
                processed_data, plan, preferences
            )
    
    async def _score_plans(
        self, 
        plans: List[Dict[str, Any]], 
        plan: TravelPlan,
        preferences: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """方案评分和排序"""
        
        scored_plans = []
        
        for plan_data in plans:
            score = await self.plan_scorer.score_plan(plan_data, plan, preferences)
            plan_data["score"] = score
            scored_plans.append(plan_data)
        
        # 按评分排序
        scored_plans.sort(key=lambda x: x["score"], reverse=True)
        
        return scored_plans
    
    async def _save_generated_plans(
        self, 
        plan_id: int, 
        plans: List[Dict[str, Any]]
    ):
        """保存生成的方案"""
        from sqlalchemy import update
        from app.models.travel_plan import TravelPlan
        
        await self.db.execute(
            update(TravelPlan)
            .where(TravelPlan.id == plan_id)
            .values(generated_plans=plans)
        )
        await self.db.commit()
    
    async def refine_plan(
        self, 
        plan_id: int, 
        plan_index: int,
        refinements: Dict[str, Any]
    ) -> bool:
        """细化旅行方案"""
        try:
            # 获取当前方案
            plan = await self._get_travel_plan(plan_id)
            if not plan or not plan.generated_plans:
                return False
            
            current_plan = plan.generated_plans[plan_index]
            
            # 应用细化
            refined_plan = await self.plan_generator.refine_plan(
                current_plan, refinements
            )
            
            # 更新方案
            plan.generated_plans[plan_index] = refined_plan
            await self._save_generated_plans(plan_id, plan.generated_plans)
            
            return True
            
        except Exception as e:
            logger.error(f"细化方案失败: {e}")
            return False
    
    async def get_plan_recommendations(
        self, 
        plan_id: int
    ) -> List[Dict[str, Any]]:
        """获取方案推荐"""
        try:
            plan = await self._get_travel_plan(plan_id)
            if not plan:
                return []
            
            # 基于用户偏好和历史数据生成推荐
            recommendations = await self.plan_generator.generate_recommendations(plan)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"获取推荐失败: {e}")
            return []
