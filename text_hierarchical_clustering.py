#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文本层次聚类算法脚本
用于对GitHub PR评论中的suggestion和problem进行语义聚类，生成设计决策知识图谱

作者: AI Assistant
创建时间: 2025-09-15
"""

import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sentence_transformers import SentenceTransformer
from scipy.cluster.hierarchy import dendrogram, linkage, fcluster, to_tree
from scipy.spatial.distance import pdist, squareform
from sklearn.metrics import silhouette_score, calinski_harabasz_score
import argparse
from pathlib import Path
from datetime import datetime
import warnings
from typing import List, Dict, Tuple, Optional, Any
import re
from collections import defaultdict
import yaml
from util.logging import default_logger
import matplotlib.font_manager as fm


class NumpyEncoder(json.JSONEncoder):
    """
    自定义JSON编码器，用于处理numpy数据类型
    """
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NumpyEncoder, self).default(obj)


def setup_default_fonts() -> str:
    """
    设置matplotlib的默认字体支持
    
    Returns:
        使用的字体名称
    """
    # 使用默认英文字体配置
    plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Liberation Sans', 'sans-serif']
    plt.rcParams['axes.unicode_minus'] = False
    
    return "DejaVu Sans"


# 设置matplotlib默认字体支持
current_font = setup_default_fonts()

# 忽略警告信息
warnings.filterwarnings('ignore')

class TextHierarchicalClusterer:
    """
    文本层次聚类器
    
    专门针对设计决策文本进行语义聚类，支持多种聚类参数配置和结果分析
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化聚类器
        
        Args:
            config: 配置字典，包含模型名称、聚类参数等
        """
        self.config = config
        
        # 初始化sentence transformer模型
        model_name = config.get('model_name', 'all-MiniLM-L6-v2')
        default_logger.info(f"正在加载文本向量化模型: {model_name}")
        self.model = SentenceTransformer(model_name)
        
        # 聚类参数
        self.distance_threshold = config.get('distance_threshold', 0.4)
        self.linkage_method = config.get('linkage_method', 'average')
        self.min_cluster_size = config.get('min_cluster_size', 2)
        self.max_clusters = config.get('max_clusters', 20)
        
        # 数据存储
        self.texts = []
        self.metadata = []
        self.embeddings = None
        self.distance_matrix = None
        self.linkage_matrix = None
        self.cluster_labels = None
        
        # 记录字体配置信息
        default_logger.info(f"Current font configuration: {current_font}")
        default_logger.info("文本层次聚类器初始化完成")
    
    def load_data(self, json_file_path: str) -> None:
        """
        从JSON文件加载数据
        
        Args:
            json_file_path: JSON文件路径
        """
        default_logger.info(f"正在加载数据文件: {json_file_path}")
        
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 提取文本数据
            self.texts = []
            self.metadata = []
            
            # 处理reviewThreadSuggestions
            if 'reviewThreadSuggestions' in data:
                for thread in data['reviewThreadSuggestions']:
                    thread_id = thread.get('reviewThreadId', '')
                    for opinion in thread.get('opinions', []):
                        # 合并problem和suggestion作为聚类文本
                        problem = opinion.get('problem', '').strip()
                        suggestion = opinion.get('suggestion', '').strip()
                        
                        if problem and suggestion:
                            # 创建组合文本用于聚类
                            combined_text = f"Problem: {problem} Suggestion: {suggestion}"
                            self.texts.append(combined_text)
                            
                            # 保存元数据
                            metadata = {
                                'thread_id': thread_id,
                                'problem': problem,
                                'suggestion': suggestion,
                                'reasons': opinion.get('reasons', []),
                                'contexts': opinion.get('contexts', []),
                                'type': opinion.get('type', ''),
                                'card_id': opinion.get('cardId', ''),
                                'source': 'reviewThread'
                            }
                            self.metadata.append(metadata)
            
            # 处理commentSuggestions
            if 'commentSuggestions' in data:
                for comment in data['commentSuggestions']:
                    comment_id = comment.get('commentId', '')
                    for opinion in comment.get('opinions', []):
                        problem = opinion.get('problem', '').strip()
                        suggestion = opinion.get('suggestion', '').strip()
                        
                        if problem and suggestion:
                            combined_text = f"Problem: {problem} Suggestion: {suggestion}"
                            self.texts.append(combined_text)
                            
                            metadata = {
                                'comment_id': comment_id,
                                'problem': problem,
                                'suggestion': suggestion,
                                'reasons': opinion.get('reasons', []),
                                'contexts': opinion.get('contexts', []),
                                'type': opinion.get('type', ''),
                                'card_id': opinion.get('cardId', ''),
                                'source': 'comment'
                            }
                            self.metadata.append(metadata)
            
            default_logger.info(f"成功加载 {len(self.texts)} 个文本样本")
            
        except Exception as e:
            default_logger.error(f"加载数据失败: {e}")
            raise
    
    def preprocess_texts(self) -> None:
        """
        预处理文本数据
        """
        default_logger.info("开始预处理文本数据")
        
        processed_texts = []
        for text in self.texts:
            # 基本清理
            cleaned_text = re.sub(r'\s+', ' ', text)  # 标准化空白字符
            cleaned_text = cleaned_text.strip()
            processed_texts.append(cleaned_text)
        
        self.texts = processed_texts
        default_logger.info("文本预处理完成")
    
    def generate_embeddings(self) -> None:
        """
        生成文本向量
        """
        default_logger.info("开始生成文本向量...")
        
        try:
            self.embeddings = self.model.encode(
                self.texts,
                convert_to_numpy=True,
                show_progress_bar=True,
                batch_size=32
            )
            
            default_logger.info(f"成功生成 {self.embeddings.shape[0]} x {self.embeddings.shape[1]} 的向量矩阵")
            
        except Exception as e:
            default_logger.error(f"生成文本向量失败: {e}")
            raise
    
    def calculate_distance_matrix(self) -> None:
        """
        计算距离矩阵
        """
        default_logger.info("计算文本相似度矩阵...")
        
        # 使用余弦距离
        distances = pdist(self.embeddings, metric='cosine')
        self.distance_matrix = squareform(distances)
        
        default_logger.info(f"距离矩阵计算完成，维度: {self.distance_matrix.shape}")
    
    def perform_clustering(self) -> None:
        """
        执行层次聚类
        """
        default_logger.info(f"开始层次聚类，链接方法: {self.linkage_method}")
        
        # 计算链接矩阵
        distances = pdist(self.embeddings, metric='cosine')
        self.linkage_matrix = linkage(distances, method=self.linkage_method)
        
        # 根据距离阈值生成聚类标签
        self.cluster_labels = fcluster(
            self.linkage_matrix, 
            self.distance_threshold, 
            criterion='distance'
        )
        
        n_clusters = len(set(self.cluster_labels))
        default_logger.info(f"聚类完成，生成 {n_clusters} 个簇")
        
        # 过滤小簇并重新分配
        # self._filter_small_clusters()
    
    def _filter_small_clusters(self) -> None:
        """
        过滤掉太小的簇，将小簇中的样本重新分配到最近的大簇
        """
        cluster_counts = defaultdict(int)
        for label in self.cluster_labels:
            cluster_counts[label] += 1
        
        # 找出需要重新分配的小簇
        small_clusters = [label for label, count in cluster_counts.items() 
                         if count < self.min_cluster_size]
        
        if small_clusters:
            default_logger.info(f"发现 {len(small_clusters)} 个小簇，将重新分配")
            
            # 将小簇中的样本分配到最近的大簇
            for i, label in enumerate(self.cluster_labels):
                if label in small_clusters:
                    # 找到最近的大簇
                    min_distance = float('inf')
                    best_cluster = label
                    
                    for j, other_label in enumerate(self.cluster_labels):
                        if (other_label not in small_clusters and 
                            cluster_counts[other_label] >= self.min_cluster_size):
                            distance = self.distance_matrix[i][j]
                            if distance < min_distance:
                                min_distance = distance
                                best_cluster = other_label
                    
                    # 重新分配到最近的大簇
                    self.cluster_labels[i] = best_cluster
            
            final_clusters = len(set(self.cluster_labels))
            default_logger.info(f"小簇重新分配完成，最终簇数量: {final_clusters}")
    
    def evaluate_clustering(self) -> Dict[str, float]:
        """
        评估聚类质量
        
        Returns:
            包含评估指标的字典
        """
        default_logger.info("评估聚类质量...")
        
        metrics = {}
        
        try:
            # 轮廓系数
            silhouette = silhouette_score(self.embeddings, self.cluster_labels)
            metrics['silhouette_score'] = float(silhouette)
            
            # Calinski-Harabasz指数
            ch_score = calinski_harabasz_score(self.embeddings, self.cluster_labels)
            metrics['calinski_harabasz_score'] = float(ch_score)
            
            # 簇的数量和分布
            unique_labels = set(self.cluster_labels)
            metrics['n_clusters'] = len(unique_labels)
            
            cluster_sizes = [list(self.cluster_labels).count(label) for label in unique_labels]
            metrics['min_cluster_size'] = int(min(cluster_sizes))
            metrics['max_cluster_size'] = int(max(cluster_sizes))
            metrics['avg_cluster_size'] = float(np.mean(cluster_sizes))
            
            default_logger.info(f"聚类评估完成 - 轮廓系数: {silhouette:.3f}, CH指数: {ch_score:.3f}")
            
        except Exception as e:
            default_logger.error(f"聚类评估失败: {e}")
            
        return metrics
    
    def visualize_dendrogram(self, output_path: str = None) -> None:
        """
        可视化树状图
        
        Args:
            output_path: 输出文件路径
        """
        default_logger.info("生成层次聚类树状图...")
        
        plt.figure(figsize=(15, 8))
        
        # 创建树状图
        dendrogram(
            self.linkage_matrix,
            leaf_rotation=90,
            leaf_font_size=8,
            show_leaf_counts=True
        )
        
        plt.title('Hierarchical Clustering Dendrogram', fontsize=16, fontweight='bold')
        plt.xlabel('Sample Index', fontsize=12)
        plt.ylabel('Distance', fontsize=12)
        
        # 添加距离阈值线
        plt.axhline(y=self.distance_threshold, color='red', linestyle='--', 
                   label=f'Distance Threshold: {self.distance_threshold}')
        plt.legend()
        
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            default_logger.info(f"树状图已保存到: {output_path}")
        else:
            plt.show()
        
        plt.close()
    
    def export_dendrogram_json(self, output_path: str) -> None:
        """
        导出树状图的JSON格式树形结构
        
        Args:
            output_path: 输出JSON文件路径
        """
        default_logger.info(f"导出树形结构JSON到: {output_path}")
        
        try:
            def build_tree_structure(node, node_id_counter=[0]):
                """
                递归构建树形结构
                
                Args:
                    node: ClusterNode对象
                    node_id_counter: 节点ID计数器（使用列表实现引用传递）
                
                Returns:
                    树形结构字典
                """
                current_id = node_id_counter[0]
                node_id_counter[0] += 1
                
                if node.is_leaf():
                    # 叶子节点 - 包含原始样本信息
                    sample_index = node.id
                    return {
                        "id": current_id,
                        "type": "leaf",
                        "sample_index": int(sample_index),
                        "text": self.texts[sample_index] if sample_index < len(self.texts) else "",
                        "metadata": self.metadata[sample_index] if sample_index < len(self.metadata) else {},
                        "cluster_label": int(self.cluster_labels[sample_index]) if self.cluster_labels is not None else None,
                        "distance": 0.0,
                        "count": 1
                    }
                else:
                    # 内部节点 - 包含子节点
                    left_child = build_tree_structure(node.get_left(), node_id_counter)
                    right_child = build_tree_structure(node.get_right(), node_id_counter)
                    
                    return {
                        "id": current_id,
                        "type": "internal",
                        "distance": float(node.dist),
                        "count": int(node.count),
                        "children": [left_child, right_child]
                    }
            
            # 将linkage matrix转换为树结构
            root_node = to_tree(self.linkage_matrix)
            
            # 构建JSON树形结构
            tree_structure = {
                "dendrogram_info": {
                    "timestamp": datetime.now().isoformat(),
                    "model_name": self.config.get('model_name', 'all-MiniLM-L6-v2'),
                    "distance_threshold": self.distance_threshold,
                    "linkage_method": self.linkage_method,
                    "n_samples": len(self.texts),
                    "n_clusters": len(set(self.cluster_labels)) if self.cluster_labels is not None else 0,
                    "max_distance": float(np.max(self.linkage_matrix[:, 2])) if self.linkage_matrix is not None else 0.0
                },
                "tree": build_tree_structure(root_node)
            }
            
            # 保存JSON文件
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(tree_structure, f, indent=2, ensure_ascii=False, cls=NumpyEncoder)
            
            default_logger.info(f"树形结构JSON导出完成")
            
        except Exception as e:
            default_logger.error(f"导出树形结构JSON失败: {e}")
            raise
    
    def visualize_cluster_distribution(self, output_path: str = None) -> None:
        """
        可视化簇分布
        
        Args:
            output_path: 输出文件路径
        """
        default_logger.info("生成簇分布可视化...")
        
        # 统计每个簇的大小
        cluster_counts = defaultdict(int)
        for label in self.cluster_labels:
            cluster_counts[label] += 1
        
        clusters = list(cluster_counts.keys())
        sizes = list(cluster_counts.values())
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # 簇大小柱状图
        ax1.bar(range(len(clusters)), sizes, alpha=0.7)
        ax1.set_xlabel('Cluster ID', fontsize=12)
        ax1.set_ylabel('Number of Samples', fontsize=12)
        ax1.set_title('Sample Count Distribution by Cluster', fontsize=14, fontweight='bold')
        ax1.set_xticks(range(len(clusters)))
        ax1.set_xticklabels(clusters)
        
        # 簇大小饼图
        ax2.pie(sizes, labels=[f'Cluster {c}' for c in clusters], autopct='%1.1f%%', startangle=90)
        ax2.set_title('Sample Proportion Distribution by Cluster', fontsize=14, fontweight='bold')
        
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            default_logger.info(f"簇分布图已保存到: {output_path}")
        else:
            plt.show()
        
        plt.close()
    
    def export_results(self, output_path: str) -> None:
        """
        导出聚类结果
        
        Args:
            output_path: 输出文件路径
        """
        default_logger.info(f"导出聚类结果到: {output_path}")
        
        # 获取cluster ID统计信息
        cluster_ids = list(set(self.cluster_labels))
        cluster_ids.sort()
        
        default_logger.info(f"Cluster ID列表: {cluster_ids}")
        
        # 构建结果数据
        results = {
            'clustering_info': {
                'timestamp': datetime.now().isoformat(),
                'model_name': self.config.get('model_name', 'all-MiniLM-L6-v2'),
                'distance_threshold': self.distance_threshold,
                'linkage_method': self.linkage_method,
                'min_cluster_size': self.min_cluster_size,
                'n_samples': len(self.texts),
                'n_clusters': len(set(self.cluster_labels)),
                'cluster_ids': cluster_ids
            },
            'evaluation_metrics': self.evaluate_clustering(),
            'clusters': {}
        }
        
        # 按簇组织数据
        for i, (text, metadata, cluster_label) in enumerate(zip(self.texts, self.metadata, self.cluster_labels)):
            cluster_id = int(cluster_label)
            cluster_key = f"cluster_{cluster_id}"
            
            if cluster_key not in results['clusters']:
                results['clusters'][cluster_key] = {
                    'cluster_id': cluster_id,
                    'size': 0,
                    'items': []
                }
            
            results['clusters'][cluster_key]['size'] += 1
            item_data = {
                'index': i,
                'text': text,
                'metadata': metadata
            }
            
            results['clusters'][cluster_key]['items'].append(item_data)
        
        # 保存结果
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, cls=NumpyEncoder)
        
        clusters_count = len(results['clusters'])
        default_logger.info(f"聚类结果导出完成，共 {clusters_count} 个簇")
    
    def run_clustering_pipeline(self, input_file: str, output_dir: str) -> None:
        """
        运行完整的聚类流水线
        
        Args:
            input_file: 输入JSON文件路径
            output_dir: 输出目录路径
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        default_logger.info("开始执行文本层次聚类流水线")
        
        try:
            # 1. 加载数据
            self.load_data(input_file)
            
            # 2. 预处理文本
            self.preprocess_texts()
            
            # 3. 生成向量
            self.generate_embeddings()
            
            # 4. 计算距离矩阵
            self.calculate_distance_matrix()
            
            # 5. 执行聚类
            self.perform_clustering()
            
            # 6. 生成可视化
            dendrogram_path = output_dir / f"dendrogram_{timestamp}.png"
            self.visualize_dendrogram(str(dendrogram_path))
            
            distribution_path = output_dir / f"cluster_distribution_{timestamp}.png"
            self.visualize_cluster_distribution(str(distribution_path))
            
            # 7. 导出树形结构JSON
            dendrogram_json_path = output_dir / f"dendrogram_tree_{timestamp}.json"
            self.export_dendrogram_json(str(dendrogram_json_path))
            
            # 8. 导出聚类结果
            results_path = output_dir / f"clustering_results_{timestamp}.json"
            self.export_results(str(results_path))
            
            default_logger.info("聚类流水线执行完成")
            
        except Exception as e:
            default_logger.error(f"聚类流水线执行失败: {e}")
            raise


def load_config(config_path: str) -> Dict[str, Any]:
    """
    加载配置文件
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        配置字典
    """
    if Path(config_path).exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            if config_path.endswith('.yaml') or config_path.endswith('.yml'):
                return yaml.safe_load(f)
            else:
                return json.load(f)
    else:
        # 返回默认配置
        return {
            'model_name': 'all-MiniLM-L6-v2',
            'distance_threshold': 0.4,
            'linkage_method': 'average',
            'min_cluster_size': 2,
            'max_clusters': 20
        }


def main():
    """
    主函数
    """
    parser = argparse.ArgumentParser(
        description='文本层次聚类工具 - 用于分析GitHub PR评论中的设计建议',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python text_hierarchical_clustering.py input.json
  python text_hierarchical_clustering.py input.json --output-dir results
  python text_hierarchical_clustering.py input.json --config clustering_config.yaml
  python text_hierarchical_clustering.py input.json --threshold 0.3 --linkage ward
        """
    )
    
    parser.add_argument(
        'input_file',
        help='输入JSON文件路径'
    )
    
    parser.add_argument(
        '--output-dir',
        default='clustering_output',
        help='输出目录路径 (默认: clustering_output)'
    )
    
    parser.add_argument(
        '--config',
        help='配置文件路径 (YAML或JSON格式)'
    )
    
    parser.add_argument(
        '--model-name',
        default='all-MiniLM-L6-v2',
        help='sentence-transformers模型名称'
    )
    
    parser.add_argument(
        '--threshold',
        type=float,
        default=0.4,
        help='距离阈值 (默认: 0.4)'
    )
    
    parser.add_argument(
        '--linkage',
        choices=['average', 'ward', 'complete', 'single'],
        default='average',
        help='链接方法 (默认: average)'
    )
    
    parser.add_argument(
        '--min-cluster-size',
        type=int,
        default=2,
        help='最小簇大小 (默认: 2)'
    )
    
    
    args = parser.parse_args()
    
    # 加载配置
    if args.config:
        config = load_config(args.config)
    else:
        config = {}
    
    # 命令行参数覆盖配置文件
    config.update({
        'model_name': args.model_name,
        'distance_threshold': args.threshold,
        'linkage_method': args.linkage,
        'min_cluster_size': args.min_cluster_size
    })
    
    # 创建聚类器并运行
    clusterer = TextHierarchicalClusterer(config)
    clusterer.run_clustering_pipeline(args.input_file, args.output_dir)


if __name__ == '__main__':
    main()
