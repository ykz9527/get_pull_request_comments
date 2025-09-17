# 文本层次聚类工具

专门用于对GitHub Pull Request评论中的设计建议进行语义聚类分析的工具，旨在帮助生成结构化的设计决策知识图谱。

## 功能特性

### 核心功能
- **语义聚类**：基于预训练的sentence-transformer模型进行深度语义理解
- **层次聚类**：采用科学的层次聚类算法，生成树状聚类结构
- **智能参数**：提供多种聚类参数配置，适应不同的分析需求
- **质量评估**：内置聚类质量评估指标，确保结果可靠性
- **可视化输出**：生成直观的树状图和分布图
- **结构化导出**：输出JSON格式的结构化聚类结果

### 技术特点
- **高精度**：使用state-of-the-art的语言模型进行文本向量化
- **可配置**：支持YAML配置文件，灵活调整算法参数
- **高性能**：优化的批处理和并行计算
- **可扩展**：模块化设计，易于扩展和定制

## 安装依赖

### 基础安装
```bash
# 安装Python依赖包
pip install -r clustering_requirements.txt
```

### 可选：GPU加速
如果您有NVIDIA GPU，可以安装CUDA版本的PyTorch以加速计算：
```bash
# 根据您的CUDA版本选择合适的PyTorch版本
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

## 快速开始

### 基本使用
```bash
# 使用默认参数对JSON文件进行聚类
python text_hierarchical_clustering.py output/all_suggestions_10592_Mon\ Sep\ 08\ 15:17:17\ 2025.json
```

### 自定义参数
```bash
# 指定输出目录和聚类参数
python text_hierarchical_clustering.py input.json \
  --output-dir results \
  --threshold 0.3 \
  --linkage ward \
  --min-cluster-size 3
```

### 使用配置文件
```bash
# 使用YAML配置文件
python text_hierarchical_clustering.py input.json --config clustering_config.yaml
```

## 配置说明

### 核心参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `distance_threshold` | 0.4 | 距离阈值，值越小簇越多 |
| `linkage_method` | "average" | 链接方法：average, ward, complete, single |
| `min_cluster_size` | 2 | 最小簇大小 |
| `model_name` | "all-MiniLM-L6-v2" | sentence-transformer模型 |

### 推荐模型

| 模型 | 特点 | 适用场景 |
|------|------|----------|
| `all-MiniLM-L6-v2` | 轻量快速 | 一般聚类任务 |
| `all-mpnet-base-v2` | 高精度 | 对准确性要求高的场景 |
| `paraphrase-multilingual-MiniLM-L12-v2` | 多语言 | 包含多语言文本 |

### 链接方法选择

| 方法 | 特点 | 适用场景 |
|------|------|----------|
| `average` | 平衡性好 | 一般推荐 |
| `ward` | 生成紧密簇 | 希望簇内相似度高 |
| `complete` | 保证簇内最大距离最小 | 对簇的一致性要求高 |
| `single` | 容易产生链式簇 | 发现延伸型模式 |

## 输入数据格式

脚本支持包含以下结构的JSON文件：

```json
{
  "reviewThreadSuggestions": [
    {
      "reviewThreadId": "thread_123",
      "opinions": [
        {
          "problem": "问题描述",
          "suggestion": "建议内容",
          "reasons": ["理由1", "理由2"],
          "contexts": ["上下文1"],
          "type": "performance optimization",
          "cardId": "CARD-xxx"
        }
      ]
    }
  ],
  "commentSuggestions": [
    {
      "commentId": "comment_456",
      "opinions": [
        {
          "problem": "问题描述",
          "suggestion": "建议内容",
          "reasons": ["理由1"],
          "contexts": [],
          "type": "code style",
          "cardId": "CARD-yyy"
        }
      ]
    }
  ]
}
```

## 输出结果

### 文件结构
```
clustering_output/
├── clustering_results_20250915_143022.json  # 详细聚类结果
├── dendrogram_20250915_143022.png           # 层次聚类树状图
├── cluster_distribution_20250915_143022.png # 簇分布可视化
└── clustering_20250915_143022.log           # 执行日志
```

### 结果JSON结构
```json
{
  "clustering_info": {
    "timestamp": "2025-09-15T14:30:22.123456",
    "model_name": "all-MiniLM-L6-v2",
    "distance_threshold": 0.4,
    "linkage_method": "average",
    "n_samples": 45,
    "n_clusters": 8
  },
  "evaluation_metrics": {
    "silhouette_score": 0.654,
    "calinski_harabasz_score": 123.45,
    "n_clusters": 8,
    "min_cluster_size": 2,
    "max_cluster_size": 12,
    "avg_cluster_size": 5.625
  },
  "clusters": {
    "cluster_1": {
      "cluster_id": 1,
      "size": 5,
      "items": [
        {
          "index": 0,
          "text": "问题: ... 建议: ...",
          "metadata": {
            "problem": "具体问题描述",
            "suggestion": "具体建议内容",
            "type": "performance optimization",
            "source": "reviewThread"
          }
        }
      ]
    }
  }
}
```

## 使用示例

### Python脚本示例
```python
from text_hierarchical_clustering import TextHierarchicalClusterer

# 创建配置
config = {
    'model_name': 'all-MiniLM-L6-v2',
    'distance_threshold': 0.4,
    'linkage_method': 'average',
    'min_cluster_size': 2
}

# 创建聚类器
clusterer = TextHierarchicalClusterer(config)

# 运行聚类流水线
clusterer.run_clustering_pipeline('input.json', 'output_dir')
```

### 分步执行示例
```python
# 分步执行以获得更多控制
clusterer.load_data('input.json')
clusterer.preprocess_texts()
clusterer.generate_embeddings()
clusterer.calculate_distance_matrix()
clusterer.perform_clustering()

# 评估和可视化
metrics = clusterer.evaluate_clustering()
clusterer.visualize_dendrogram('dendrogram.png')
clusterer.export_results('results.json')
```

## 参数调优建议

### 距离阈值调优
- **0.2-0.3**：生成较多细分的簇，适合发现细微差异
- **0.4-0.5**：平衡的簇数量，适合一般分析
- **0.6-0.8**：生成较少的大簇，适合高层次概括

### 模型选择建议
- **小数据集（<100样本）**：使用all-MiniLM-L6-v2
- **大数据集（>500样本）**：考虑使用更大的模型如all-mpnet-base-v2
- **多语言数据**：使用paraphrase-multilingual-MiniLM-L12-v2

### 性能优化
- **批处理大小**：根据内存情况调整batch_size（默认32）
- **并行处理**：设置n_jobs=-1使用所有CPU核心
- **GPU加速**：安装CUDA版本的PyTorch

## 聚类质量评估

### 评估指标解释

| 指标 | 范围 | 说明 | 理想值 |
|------|------|------|--------|
| 轮廓系数 | [-1, 1] | 衡量簇内紧密度和簇间分离度 | 越接近1越好 |
| CH指数 | [0, ∞) | 衡量簇间差异与簇内差异的比值 | 越大越好 |

### 质量判断标准
- **轮廓系数 > 0.5**：聚类质量较好
- **轮廓系数 > 0.7**：聚类质量很好
- **轮廓系数 < 0.3**：可能需要调整参数

## 故障排除

### 常见问题

1. **内存不足**
   ```
   解决方案：减少batch_size，或使用更小的模型
   ```

2. **聚类结果过于分散**
   ```
   解决方案：增加distance_threshold值，或调整linkage_method
   ```

3. **聚类结果过于集中**
   ```
   解决方案：减少distance_threshold值，或使用更敏感的模型
   ```

4. **模型下载失败**
   ```
   解决方案：检查网络连接，或手动下载模型文件
   ```

### 调试模式
```bash
# 启用详细日志
python text_hierarchical_clustering.py input.json --verbose
```

## 高级用法

### 自定义预处理
可以修改`TextHierarchicalClusterer.preprocess_texts()`方法来实现自定义的文本预处理逻辑。

### 自定义相似度计算
可以继承`TextHierarchicalClusterer`类并重写`calculate_distance_matrix()`方法来使用自定义的相似度计算方法。

### 批量处理
```python
import glob

# 批量处理多个文件
for file_path in glob.glob("data/*.json"):
    clusterer = TextHierarchicalClusterer(config)
    output_dir = f"results/{Path(file_path).stem}"
    clusterer.run_clustering_pipeline(file_path, output_dir)
```

## 算法原理

### 文本向量化
1. 使用预训练的sentence-transformer模型将文本转换为高维向量
2. 模型基于大规模语料训练，能够捕捉深层语义信息

### 层次聚类
1. 计算所有文本向量对之间的余弦距离
2. 使用指定的链接方法（average/ward/complete/single）构建层次结构
3. 根据距离阈值切分层次树，生成最终簇

### 质量评估
1. 轮廓系数：评估每个样本与其所在簇的相似度
2. CH指数：评估簇间分离度与簇内紧密度的比值

## 贡献指南

欢迎提交Issue和Pull Request来改进这个工具！

### 开发环境设置
```bash
git clone <repository>
cd text-hierarchical-clustering
pip install -r clustering_requirements.txt
pip install -r dev-requirements.txt  # 开发依赖
```

### 测试
```bash
python -m pytest tests/
```

## 许可证

本项目采用MIT许可证。

## 更新日志

### v1.0.0 (2025-09-15)
- 初始版本发布
- 支持基于sentence-transformers的语义聚类
- 提供完整的可视化和评估功能
- 支持灵活的配置管理
