import fetch_each_part_in_pr_util as githubutil
from datetime import datetime
import util.ai.llm_client as llm_client
import util.ai.prompt as prompt
import json
import time
from util.logging import default_logger
import hashlib
import tqdm
import uuid
from typing import List, Dict, Optional, Tuple

class DesignKnowledgeClusterer:
    """
    基于LLM的设计知识聚类器，用于将相似的设计观点卡片归类到同一个子图中
    """
    
    def __init__(self, llm_model="deepseek-chat", similarity_threshold=0.7):
        self.llm_client = llm_client.get_llm_client(llm_model)
        self.similarity_threshold = similarity_threshold
        self.existing_clusters = []
        
    def classify_opinion_cards(self, opinion_cards: List[Dict]) -> List[Dict]:
        """
        对观点卡片进行分类聚合
        
        Args:
            opinion_cards: 观点卡片列表
            
        Returns:
            聚合后的子图列表
        """
        default_logger.info(f"开始对 {len(opinion_cards)} 个观点卡片进行分类")
        
        for card in tqdm.tqdm(opinion_cards, desc="分类观点卡片"):
            self._classify_single_card(card)
            
        # 补全每个子图的关系和决策信息
        completed_clusters = []
        for cluster in self.existing_clusters:
            completed_cluster = self._complete_cluster_structure(cluster)
            completed_clusters.append(completed_cluster)
            
        default_logger.info(f"分类完成，共生成 {len(completed_clusters)} 个子图")
        return completed_clusters
    
    def _classify_single_card(self, card: Dict) -> None:
        """
        对单个卡片进行分类
        """
        if not self.existing_clusters:
            # 创建第一个类别
            new_cluster = self._create_new_cluster(card)
            self.existing_clusters.append(new_cluster)
            return
            
        # 计算与现有类别的相似度
        best_match, similarity_score = self._find_best_matching_cluster(card)
        
        if similarity_score >= self.similarity_threshold:
            # 加入现有类别
            self._add_card_to_cluster(card, best_match)
            default_logger.debug(f"卡片加入现有类别，相似度: {similarity_score:.3f}")
        else:
            # 创建新类别
            new_cluster = self._create_new_cluster(card)
            self.existing_clusters.append(new_cluster)
            default_logger.debug(f"创建新类别，最高相似度: {similarity_score:.3f}")
    
    def _find_best_matching_cluster(self, card: Dict) -> Tuple[Dict, float]:
        """
        找到与卡片最匹配的现有类别
        
        Returns:
            (最佳匹配的类别, 相似度分数)
        """
        best_cluster = None
        best_score = 0.0
        
        for cluster in self.existing_clusters:
            similarity_score = self._calculate_similarity_with_llm(card, cluster)
            if similarity_score > best_score:
                best_score = similarity_score
                best_cluster = cluster
                
        return best_cluster, best_score
    
    def _calculate_similarity_with_llm(self, card: Dict, cluster: Dict) -> float:
        """
        使用LLM计算卡片与类别的相似度
        """
        prompt_messages = self._build_similarity_prompt(card, cluster)
        
        try:
            response = self.llm_client.generate_text(
                prompt_messages,
                {"temperature": 0.1}
            )
            default_logger.debug(f"LLM相似度计算响应: {response}")
            # 解析LLM响应，提取相似度分数
            similarity_data = self._parse_similarity_response(response)
            return similarity_data.get("similarity_score", 0.0)
            
        except Exception as e:
            default_logger.error(f"LLM相似度计算失败: {e}")
            return 0.0
    
    def _build_similarity_prompt(self, card: Dict, cluster: Dict) -> List[Dict]:
        """
        构建相似度判断的prompt
        """
        cluster_summary = {
            "title": cluster.get("title", ""),
            "goal": cluster.get("goal", ""),
            "existing_cards_count": len(cluster.get("opinion_cards", [])),
            "sample_subjects": [c.get("subject", "") for c in cluster.get("opinion_cards", [])[:3]]
        }
        
        prompt_content = f"""
你是一个设计知识分类专家。请判断给定的观点卡片是否应该归类到现有的设计知识类别中。

现有类别信息：
- 标题: {cluster_summary['title']}
- 目标: {cluster_summary['goal']}
- 已有卡片数量: {cluster_summary['existing_cards_count']}
- 示例主题: {', '.join(cluster_summary['sample_subjects'])}

待分类的观点卡片：
- 主题: {card.get('subject', '')}
- 观点: {card.get('opinion', '')}
- 论据: {', '.join(card.get('arguments', []))}

请分析这个观点卡片是否与现有类别在以下方面相似：
1. 技术领域和问题域
2. 设计理念和方法论
3. 解决方案的本质特征

请以JSON格式回复，包含以下字段：
{{
  "similarity_score": 0.0-1.0之间的相似度分数,
  "reasoning": "判断理由",
  "key_similarities": ["相似点列表"],
  "key_differences": ["差异点列表"]
}}
"""
        
        return [{"role": "user", "content": prompt_content}]
    
    def _parse_similarity_response(self, response: str) -> Dict:
        """
        解析LLM的相似度判断响应
        """
        try:
            # 尝试提取JSON部分
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start != -1 and json_end != -1:
                json_str = response[json_start:json_end]
                return json.loads(json_str)
        except Exception as e:
            default_logger.error(f"解析相似度响应失败: {e}")
            
        return {"similarity_score": 0.0, "reasoning": "解析失败"}
    
    def _create_new_cluster(self, card: Dict) -> Dict:
        """
        基于卡片创建新的类别
        """
        cluster_id = f"DD-{hashlib.md5(str(card).encode()).hexdigest()[:8].upper()}"
        card_id = f"CARD-{uuid.uuid4().hex[:6]}"
        
        # 为卡片添加ID
        card_with_id = dict(card)
        card_with_id["cardId"] = card_id
        
        # 使用LLM生成类别的标题和目标
        title, goal = self._generate_cluster_metadata(card)
        
        return {
            "id": cluster_id,
            "title": title,
            "goal": goal,
            "opinion_cards": [card_with_id],
            "relationships": [],
            "options": [],
            "final_decision": None
        }
    
    def _add_card_to_cluster(self, card: Dict, cluster: Dict) -> None:
        """
        将卡片添加到现有类别中
        """
        card_id = f"CARD-{uuid.uuid4().hex[:6]}"
        card_with_id = dict(card)
        card_with_id["cardId"] = card_id
        
        cluster["opinion_cards"].append(card_with_id)
        
        # 可能需要更新类别的标题和目标
        self._update_cluster_metadata(cluster)
    
    def _generate_cluster_metadata(self, card: Dict) -> Tuple[str, str]:
        """
        基于卡片内容生成类别的标题和目标
        """
        prompt_content = f"""
基于以下观点卡片，生成一个设计知识类别的标题和目标描述：

观点卡片：
- 主题: {card.get('subject', '')}
- 观点: {card.get('opinion', '')}
- 论据: {', '.join(card.get('arguments', []))}
- 条件: {', '.join(card.get('condition', []))}

请生成：
1. 一个简洁的类别标题（10-20字）
2. 一个清晰的目标描述（30-50字）

以JSON格式回复：
{{
  "title": "类别标题",
  "goal": "目标描述"
}}
"""
        
        try:
            response = self.llm_client.generate_text(
                [{"role": "user", "content": prompt_content}],
                {"temperature": 0.3}
            )
            
            metadata = self._parse_similarity_response(response)
            return metadata.get("title", "未命名类别"), metadata.get("goal", "待定义目标")
            
        except Exception as e:
            default_logger.error(f"生成类别元数据失败: {e}")
            return "未命名类别", "待定义目标"
    
    def _update_cluster_metadata(self, cluster: Dict) -> None:
        """
        基于所有卡片更新类别的标题和目标
        """
        # 简化实现：仅在卡片数量达到特定阈值时更新
        if len(cluster["opinion_cards"]) % 3 == 0:  # 每3个卡片更新一次
            cards_summary = self._summarize_cards_in_cluster(cluster)
            new_title, new_goal = self._generate_updated_metadata(cards_summary)
            cluster["title"] = new_title
            cluster["goal"] = new_goal
    
    def _complete_cluster_structure(self, cluster: Dict) -> Dict:
        """
        补全类别的关系、选项和最终决策
        """
        # 分析卡片间关系
        relationships = self._analyze_card_relationships(cluster["opinion_cards"])
        cluster["relationships"] = relationships
        
        # 生成选项
        options = self._generate_options(cluster["opinion_cards"])
        cluster["options"] = options
        
        # 生成最终决策
        final_decision = self._generate_final_decision(cluster["opinion_cards"], options)
        cluster["final_decision"] = final_decision
        
        return cluster
    
    def _analyze_card_relationships(self, cards: List[Dict]) -> List[Dict]:
        """
        分析卡片间的关系
        """
        if len(cards) < 2:
            return []
            
        prompt_content = f"""
你是一个设计知识关系分析专家。请分析以下观点卡片之间的关系，识别它们属于以下5种关系类型之一：

**关系类型定义：**
1. **互斥关系 (alternative)**: 建议A和B无法同时采纳，选择其一必须放弃另一个
2. **互补关系 (complementary)**: 多个建议可以且应该同时实施，共同构成更完整的解决方案
3. **层级关系 (partOf)**: 一个建议是高层设计思想（宏观），另一个是其具体实现细节（微观）
4. **依赖关系 (prerequisite)**: 建议B的实施必须以建议A完成为前提
5. **正交关系 (independent)**: 两个建议针对同一问题的不同方面，彼此无影响，可独立实施

**观点卡片：**
"""
        
        for i, card in enumerate(cards):
            prompt_content += f"""
卡片{i+1} (ID: {card.get('cardId', '')}):
- 主题: {card.get('subject', '')}
- 观点: {card.get('opinion', '')}
- 论据: {', '.join(card.get('arguments', []))}

"""
        
        prompt_content += """
**分析要求：**
- 仔细分析每对卡片之间的关系
- 只有当关系明确且有意义时才建立关系
- 如果两个建议没有明显关系，可以不建立关系
- 优先识别互斥和依赖关系，这些对决策最重要

请以JSON格式返回关系列表：
{
  "relationships": [
    {
      "source": "源卡片ID",
      "target": "目标卡片ID",
      "type": "关系类型(alternative/complementary/partOf/prerequisite/independent)",
      "description": "详细的关系描述，说明为什么是这种关系"
    }
  ]
}
"""
        
        try:
            response = self.llm_client.generate_text(
                [{"role": "user", "content": prompt_content}],
                {"temperature": 0.2}
            )
            
            result = self._parse_similarity_response(response)
            return result.get("relationships", [])
            
        except Exception as e:
            default_logger.error(f"分析卡片关系失败: {e}")
            return []
    
    def _generate_options(self, cards: List[Dict]) -> List[Dict]:
        """
        使用LLM生成智能化的选项方案
        """
        if not cards:
            return []
            
        try:
            prompt_content = f"""
你是一个软件架构专家，需要基于多个设计知识卡片生成合理的解决方案选项。

## 设计知识卡片
{json.dumps(cards, ensure_ascii=False, indent=2)}

## 任务要求
请分析这些卡片，生成几个不同的解决方案选项。每个选项应该：
1. 整合相关的卡片内容
2. 提供清晰的标题和摘要
3. 说明实施条件和支持论据
4. 确保选项之间有明显差异

## 输出格式
请严格按照以下JSON数组格式输出：
[
  {{
    "optionId": "OPTION-1",
    "title": "方案标题",
    "summary": "方案摘要说明",
    "based_on_cards": ["相关卡片ID列表"],
    "conditions": ["实施条件列表"],
    "arguments": ["支持论据列表"]
  }}
]

注意：
- 每个选项的based_on_cards应包含支撑该方案的卡片ID
- 条件和论据应该从原始卡片中提取和整合
- 标题要简洁有力，摘要要清晰易懂
"""
            
            response = self.llm_client.generate_text(
                [{"role": "user", "content": prompt_content}],
                {"temperature": 0.3}
            )
            
            options = json.loads(response)
            return options if isinstance(options, list) else []
            
        except Exception as e:
            default_logger.error(f"生成选项失败: {e}")
            # 降级到简化实现
            options = []
            for i, card in enumerate(cards):
                option = {
                    "optionId": f"OPTION-{i+1}",
                    "title": f"方案{i+1}: {card.get('subject', '')}",
                    "summary": card.get('opinion', ''),
                    "based_on_cards": [card.get('cardId', '')],
                    "conditions": card.get('condition', []),
                    "arguments": card.get('arguments', [])
                }
                options.append(option)
            return options
    
    def _generate_final_decision(self, cards: List[Dict], options: List[Dict]) -> Dict:
        """
        使用LLM生成最终决策
        """
        if not options:
            return None
            
        try:
            prompt_content = f"""
你是一个软件架构专家，需要基于多个设计方案选择最优的综合解决方案。

## 可选方案
{json.dumps(options, ensure_ascii=False, indent=2)}

## 原始设计卡片
{json.dumps(cards, ensure_ascii=False, indent=2)}

## 任务要求
请分析所有方案的优缺点，选择最合适的方案组合，并提供详细的决策理由。

## 输出格式
请严格按照以下JSON格式输出：
{{
    "summary": "决策总结",
    "chosen_suggestion_ids": ["选中的卡片ID列表"],
    "conditions": ["实施条件列表"],
    "justification": "详细的决策理由和分析过程"
}}
"""
            
            response = self.llm_client.generate_text(
                [{"role": "user", "content": prompt_content}],
                {"temperature": 0.3}
            )
            
            decision_data = json.loads(response)
            return decision_data
            
        except Exception as e:
            default_logger.error(f"生成最终决策失败: {e}")
            # 降级到简化实现
            chosen_cards = [card.get('cardId', '') for card in cards[:len(options)//2 + 1]]
            return {
                "summary": f"基于分析，采纳了 {len(chosen_cards)} 个核心观点的综合方案。",
                "chosen_suggestion_ids": chosen_cards,
                "conditions": [],
                "justification": "通过综合考虑各方观点，选择了最具可行性和一致性的解决方案。"
            }
    
    def _summarize_cards_in_cluster(self, cluster: Dict) -> str:
        """
        使用LLM总结类别中的卡片
        """
        cards = cluster.get("opinion_cards", [])
        if not cards:
            return "空集群"
            
        try:
            prompt_content = f"""
你是一个技术文档专家，需要为一组相关的设计知识卡片生成简洁的摘要。

## 设计知识卡片
{json.dumps(cards, ensure_ascii=False, indent=2)}

## 任务要求
请分析这些卡片的共同主题和核心内容，生成一个简洁明了的摘要（不超过100字）。
摘要应该：
1. 概括主要的设计思想或技术要点
2. 突出共同的关注点或解决的问题
3. 使用专业但易懂的语言

## 输出格式
直接输出摘要文本，不需要JSON格式。
"""
            
            response = self.llm_client.generate_text(
                [{"role": "user", "content": prompt_content}],
                {"temperature": 0.2}
            )
            
            return response.strip()
            
        except Exception as e:
            default_logger.error(f"生成集群摘要失败: {e}")
            # 降级到简化实现
            subjects = [card.get("subject", "") for card in cards]
            return "; ".join(subjects)
    
    def _generate_updated_metadata(self, cards_summary: str) -> Tuple[str, str]:
        """
        使用LLM基于卡片摘要生成更新的元数据
        """
        try:
            prompt_content = f"""
你是一个产品经理，需要为一个设计方案集群生成合适的标题和目标描述。

## 集群摘要
{cards_summary}

## 任务要求
基于提供的摘要，生成：
1. 一个简洁有力的标题（不超过30字）
2. 一个清晰的目标描述（不超过50字）

标题应该体现方案的核心价值，目标描述应该说明要解决的问题或达成的效果。

## 输出格式
请严格按照以下JSON格式输出：
{{
    "title": "方案标题",
    "goal": "目标描述"
}}
"""
            
            response = self.llm_client.generate_text(
                [{"role": "user", "content": prompt_content}],
                {"temperature": 0.2}
            )
            
            metadata = json.loads(response)
            return metadata.get("title", f"综合设计方案 - {cards_summary}"), metadata.get("goal", "整合多个设计观点的综合解决方案")
            
        except Exception as e:
            default_logger.error(f"生成元数据失败: {e}")
            # 降级到简化实现
            return f"综合设计方案 - {cards_summary}", "整合多个设计观点的综合解决方案"

def extract_opinion_graph(opinion_list):
    """
    提取 opinion 之间的相互关系，返回结构化的 json 表示多个子图
    
    Args:
        opinion_list (list): list of opinions

    Returns:
        list: list of subgraphs
    """
    
    default_logger.info("开始提取观点图谱")
    
    # 使用新的聚类器进行分类
    clusterer = DesignKnowledgeClusterer(
        llm_model="gpt-4o-mini",
        similarity_threshold=0.7
    )
    
    subgraphs = clusterer.classify_opinion_cards(opinion_list)
    
    default_logger.info(f"观点图谱提取完成，生成 {len(subgraphs)} 个子图")
    return subgraphs

def main():
    with open("output/all_suggestions_10592_Thu Sep  4 14:56:42 2025.json","r") as f:
        all_suggestions = json.load(f)

    opinion_list = []
    for opinions in all_suggestions["reviewThreadSuggestions"]:
        for opinion_card in opinions["opinions"]:
            opinion_list.append(opinion_card)
    
    for opinions in all_suggestions["commentSuggestions"]:
        for opinion_card in opinions["opinions"]:
            opinion_list.append(opinion_card)

    opinion_graph = extract_opinion_graph(opinion_list)

    with open(f"output/opinion_graph_10592_{time.ctime()}.json","w") as f:
        json.dump(opinion_graph,f,indent=4,ensure_ascii=False)


if __name__ == "__main__":
    main()