#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文本层次聚类使用示例
演示如何使用text_hierarchical_clustering.py对PR评论进行聚类分析

作者: AI Assistant
创建时间: 2025-09-15
"""

import json
import os
from pathlib import Path
from text_hierarchical_clustering import TextHierarchicalClusterer, load_config

def example_basic_usage():
    """
    基本使用示例
    """
    print("=== 基本使用示例 ===")
    
    # 输入文件路径
    input_file = "output/all_suggestions_10592_Mon Sep 08 15:17:17 2025.json"
    
    # 检查文件是否存在
    if not Path(input_file).exists():
        print(f"错误：输入文件不存在: {input_file}")
        return
    
    # 使用默认配置
    config = {
        'model_name': 'all-MiniLM-L6-v2',
        'distance_threshold': 0.4,
        'linkage_method': 'average',
        'min_cluster_size': 2,
        'max_clusters': 20
    }
    
    # 创建聚类器
    clusterer = TextHierarchicalClusterer(config)
    
    # 运行聚类流水线
    output_dir = "clustering_output_example"
    clusterer.run_clustering_pipeline(input_file, output_dir)
    
    print(f"聚类结果已保存到: {output_dir}")

def example_custom_config():
    """
    自定义配置示例
    """
    print("\n=== 自定义配置示例 ===")
    
    # 输入文件路径
    input_file = "output/all_suggestions_10592_Mon Sep 08 15:17:17 2025.json"
    
    if not Path(input_file).exists():
        print(f"错误：输入文件不存在: {input_file}")
        return
    
    # 加载配置文件
    config = load_config("clustering_config.yaml")
    
    # 自定义部分参数
    config.update({
        'distance_threshold': 0.3,  # 更小的阈值，生成更多细分的簇
        'linkage_method': 'ward',   # 使用Ward方法
        'min_cluster_size': 3       # 最小簇大小为3
    })
    
    print(f"使用配置: {config}")
    
    # 创建聚类器
    clusterer = TextHierarchicalClusterer(config)
    
    # 运行聚类流水线
    output_dir = "clustering_output_custom"
    clusterer.run_clustering_pipeline(input_file, output_dir)
    
    print(f"聚类结果已保存到: {output_dir}")

def example_step_by_step():
    """
    分步执行示例
    """
    print("\n=== 分步执行示例 ===")
    
    input_file = "output/all_suggestions_10592_Mon Sep 08 15:17:17 2025.json"
    
    if not Path(input_file).exists():
        print(f"错误：输入文件不存在: {input_file}")
        return
    
    # 创建聚类器
    config = {
        'model_name': 'all-MiniLM-L6-v2',
        'distance_threshold': 0.35,
        'linkage_method': 'average',
        'min_cluster_size': 2
    }
    
    clusterer = TextHierarchicalClusterer(config)
    
    try:
        # 步骤1: 加载数据
        print("步骤1: 加载数据...")
        clusterer.load_data(input_file)
        print(f"加载了 {len(clusterer.texts)} 个文本样本")
        
        # 步骤2: 预处理文本
        print("步骤2: 预处理文本...")
        clusterer.preprocess_texts()
        
        # 步骤3: 生成向量
        print("步骤3: 生成文本向量...")
        clusterer.generate_embeddings()
        print(f"生成了 {clusterer.embeddings.shape} 的向量矩阵")
        
        # 步骤4: 计算距离矩阵
        print("步骤4: 计算距离矩阵...")
        clusterer.calculate_distance_matrix()
        
        # 步骤5: 执行聚类
        print("步骤5: 执行层次聚类...")
        clusterer.perform_clustering()
        n_clusters = len(set(clusterer.cluster_labels))
        print(f"生成了 {n_clusters} 个簇")
        
        # 步骤6: 评估聚类质量
        print("步骤6: 评估聚类质量...")
        metrics = clusterer.evaluate_clustering()
        print(f"聚类评估指标: {metrics}")
        
        # 步骤7: 可视化和导出
        print("步骤7: 生成可视化和导出结果...")
        output_dir = Path("clustering_output_stepwise")
        output_dir.mkdir(exist_ok=True)
        
        # 生成树状图
        clusterer.visualize_dendrogram(str(output_dir / "dendrogram.png"))
        
        # 生成分布图
        clusterer.visualize_cluster_distribution(str(output_dir / "distribution.png"))
        
        # 导出结果
        clusterer.export_results(str(output_dir / "results.json"))
        
        print(f"所有结果已保存到: {output_dir}")
        
    except Exception as e:
        print(f"执行过程中出现错误: {e}")

def analyze_clustering_results(results_file: str):
    """
    分析聚类结果
    """
    print(f"\n=== 聚类结果分析: {results_file} ===")
    
    if not Path(results_file).exists():
        print(f"结果文件不存在: {results_file}")
        return
    
    with open(results_file, 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    # 基本信息
    info = results['clustering_info']
    print(f"聚类时间: {info['timestamp']}")
    print(f"样本数量: {info['n_samples']}")
    print(f"簇数量: {info['n_clusters']}")
    print(f"距离阈值: {info['distance_threshold']}")
    print(f"链接方法: {info['linkage_method']}")
    
    # 评估指标
    metrics = results['evaluation_metrics']
    print(f"\n评估指标:")
    for metric, value in metrics.items():
        print(f"  {metric}: {value:.4f}" if isinstance(value, float) else f"  {metric}: {value}")
    
    # 簇分析
    print(f"\n簇详细信息:")
    clusters = results['clusters']
    for cluster_name, cluster_data in clusters.items():
        print(f"  {cluster_name}: {cluster_data['size']} 个样本")
        
        # 显示前几个样本的主题
        if cluster_data['items']:
            print(f"    示例主题:")
            for i, item in enumerate(cluster_data['items'][:3]):
                problem = item['metadata'].get('problem', '')[:50]
                suggestion = item['metadata'].get('suggestion', '')[:50]
                print(f"      {i+1}. 问题: {problem}...")
                print(f"         建议: {suggestion}...")
            if len(cluster_data['items']) > 3:
                print(f"      ... 还有 {len(cluster_data['items']) - 3} 个样本")
    
    print()

def main():
    """
    主函数 - 运行所有示例
    """
    print("文本层次聚类使用示例")
    print("=" * 50)
    
    # 检查必要的文件
    input_file = "output/all_suggestions_10592_Mon Sep 08 15:17:17 2025.json"
    if not Path(input_file).exists():
        print(f"警告：示例数据文件不存在: {input_file}")
        print("请确保您有正确的输入文件，或修改示例中的文件路径")
        return
    
    try:
        # 运行基本示例
        example_basic_usage()
        
        # 运行自定义配置示例
        example_custom_config()
        
        # 运行分步执行示例
        example_step_by_step()
        
        # 分析结果（如果存在）
        results_files = [
            "clustering_output_example/clustering_results_*.json",
            "clustering_output_custom/clustering_results_*.json", 
            "clustering_output_stepwise/results.json"
        ]
        
        import glob
        for pattern in results_files:
            files = glob.glob(pattern)
            for file in files:
                analyze_clustering_results(file)
        
        print("\n所有示例执行完成！")
        print("请查看生成的输出目录以了解详细结果。")
        
    except Exception as e:
        print(f"示例执行过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
