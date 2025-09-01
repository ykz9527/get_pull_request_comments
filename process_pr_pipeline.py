#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PR处理Pipeline
直接调用现有模块获取PR数据并进行分析处理

使用方法:
python process_pr_pipeline.py <owner> <repo> <start_pr> <end_pr> [--output output_dir]

示例:
python process_pr_pipeline.py JabRef jabref 10590 10600
python process_pr_pipeline.py JabRef jabref 10590 10600 --output results/jabref_batch
"""

import argparse
import json
import os
import sys
import time
import glob
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# 导入现有模块
from get_pr_comments_py_github import GitHubPRCommentsFetcher
import extract_pipline_preliminary as extract_module
from util.logging import default_logger


def parse_pr_list(pr_args: List[str]) -> List[int]:
    """
    解析PR编号列表，支持单个数字和范围格式
    
    Args:
        pr_args: PR参数列表，每个元素可以是数字或范围（如 "10590-10600"）
        
    Returns:
        List[int]: 解析后的PR编号列表（去重并排序）
        
    Raises:
        ValueError: 当输入格式无效时
        
    Examples:
        parse_pr_list(["10590", "10595", "10600-10610"]) 
        # 返回 [10590, 10595, 10600, 10601, 10602, ..., 10610]
    """
    pr_numbers = set()
    
    for arg in pr_args:
        arg = arg.strip()
        
        if '-' in arg and not arg.startswith('-'):
            # 处理范围格式 "start-end"
            try:
                parts = arg.split('-')
                if len(parts) != 2:
                    raise ValueError(f"无效的范围格式: {arg}")
                
                start_pr = int(parts[0])
                end_pr = int(parts[1])
                
                if start_pr > end_pr:
                    raise ValueError(f"起始PR编号不能大于结束PR编号: {arg}")
                
                # 添加范围内的所有数字
                pr_numbers.update(range(start_pr, end_pr + 1))
                
            except ValueError as e:
                if "invalid literal for int()" in str(e):
                    raise ValueError(f"范围格式中包含无效数字: {arg}")
                else:
                    raise e
        else:
            # 处理单个数字
            try:
                pr_number = int(arg)
                if pr_number <= 0:
                    raise ValueError(f"PR编号必须为正整数: {arg}")
                pr_numbers.add(pr_number)
            except ValueError:
                raise ValueError(f"无效的PR编号: {arg}")
    
    if not pr_numbers:
        raise ValueError("未提供有效的PR编号")
    
    return sorted(list(pr_numbers))


class PRProcessor:
    def __init__(self, owner: str, repo: str, config_path: str = "config.yaml", token_path: str = "PAT.token"):
        """
        初始化PR处理器
        
        Args:
            owner: 仓库所有者
            repo: 仓库名称
            config_path: 配置文件路径
            token_path: GitHub PAT token文件路径
        """
        self.owner = owner
        self.repo = repo
        
        # 初始化GitHub fetcher
        self.fetcher = GitHubPRCommentsFetcher(config_path, token_path)
    
    def fetch_pr_data(self, pr_number: int) -> Optional[Dict]:
        """
        获取单个PR的数据 - 直接调用get_pr_comments_py_github
        
        Args:
            pr_number: PR编号
            
        Returns:
            Dict: PR数据，如果失败返回None
        """
        try:
            default_logger.info(f"开始获取PR #{pr_number}的数据")
            pr_data = self.fetcher.fetch_pr_data(self.owner, self.repo, pr_number, fetch_code_snippet=False)
            
            if isinstance(pr_data, dict) and "error" in pr_data:
                default_logger.error(f"PR #{pr_number} 获取失败: {pr_data['error']}")
                return None
            
            default_logger.info(f"PR #{pr_number} 数据获取成功")
            return pr_data
            
        except Exception as e:
            default_logger.error(f"PR #{pr_number} 获取异常: {str(e)}")
            return None
    
    def load_existing_pr_data(self, pr_data_file: Path) -> Optional[Dict]:
        """
        安全地读取已存在的PR数据文件
        
        Args:
            pr_data_file: PR数据文件路径
            
        Returns:
            Dict: 读取的PR数据，如果失败返回None
        """
        if not pr_data_file.exists():
            return None
            
        try:
            with open(pr_data_file, 'r', encoding='utf-8') as f:
                pr_data = json.load(f)
            default_logger.info(f"成功从缓存读取PR数据: {pr_data_file.name}")
            return pr_data
        except (json.JSONDecodeError, IOError) as e:
            default_logger.warning(f"读取PR数据文件失败，将重新获取: {pr_data_file.name}, 错误: {str(e)}")
            return None
    
    def check_suggestions_file_exists(self, output_path: Path, pr_number: int) -> Optional[Path]:
        """
        检查建议结果文件是否已存在
        
        Args:
            output_path: 输出目录路径
            pr_number: PR编号
            
        Returns:
            Path: 如果存在返回文件路径，否则返回None
        """
        # 查找所有匹配的建议文件（支持时间戳模式）
        pattern = f"all_suggestions_{pr_number}_*.json"
        suggestion_files = list(output_path.glob(pattern))
        
        if suggestion_files:
            # 返回最新的文件
            latest_file = max(suggestion_files, key=lambda p: p.stat().st_mtime)
            default_logger.info(f"发现已存在的建议文件: {latest_file.name}")
            return latest_file
        
        return None

    def extract_suggestions(self, pr_data: Dict, pr_number: int) -> Optional[Dict]:
        """
        从PR数据中提取建议 - 直接调用extract_pipline_preliminary
        
        Args:
            pr_data: PR数据
            pr_number: PR编号
            
        Returns:
            Dict: 提取的建议数据，如果失败返回None
        """
        try:
            default_logger.info(f"开始处理PR #{pr_number}的建议提取")
            
            # 准备PR信息
            pr_info = {
                "owner": self.owner,
                "repo": self.repo,
                "pr_number": pr_number,
            }
            
            # 获取必要的数据
            review_threads = pr_data.get("reviewThreads", [])
            commits = pr_data.get("commits", [])
            global_discussions = pr_data.get("globalDiscussions", [])
            
            # 直接调用现有的extract模块函数
            review_thread_suggestions = extract_module.extract_review_thread_pipeline(review_threads, global_discussions)
            comment_suggestions = extract_module.extract_comment_and_review_pipeline(global_discussions)
            
            # 按照现有格式组装结果
            all_suggestions = {
                "reviewThreadSuggestions": review_thread_suggestions,
                "commentSuggestions": comment_suggestions,
            }
            
            default_logger.info(f"PR #{pr_number} 建议提取完成")
            return all_suggestions
            
        except Exception as e:
            default_logger.error(f"PR #{pr_number} 建议提取异常: {str(e)}")
            return None
    
    def process_pr_list(self, pr_numbers: List[int], output_dir: str = "output") -> None:
        """
        处理PR列表，支持后续扩展其他处理环节
        
        Args:
            pr_numbers: PR编号列表
            output_dir: 输出目录
        """
        # 确保输出目录存在
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        print(f"开始处理 {self.owner}/{self.repo} 的 {len(pr_numbers)} 个PR: {pr_numbers}")
        
        for pr_number in pr_numbers:
            print(f"\n处理 PR #{pr_number}")
            
            # 首先检查建议结果文件是否已存在
            # existing_suggestions_file = self.check_suggestions_file_exists(output_path, pr_number)
            # if existing_suggestions_file:
            #     print(f"⚡ PR #{pr_number} 建议文件已存在，跳过处理: {existing_suggestions_file.name}")
            #     default_logger.info(f"PR #{pr_number} 跳过处理，建议文件已存在: {existing_suggestions_file}")
            #     continue
            
            # 步骤1: 获取PR数据 (检查缓存)
            pr_data_file = output_path / f"pr_data_py_github_{pr_number}.json"
            pr_data = self.load_existing_pr_data(pr_data_file)
            
            if pr_data is not None:
                print(f"📁 PR #{pr_number} 使用缓存数据")
            else:
                print(f"🔄 PR #{pr_number} 重新获取数据")
                pr_data = self.fetch_pr_data(pr_number)
                if pr_data is None:
                    print(f"✗ PR #{pr_number} 数据获取失败")
                    continue
                
                # 保存原始PR数据 (按照现有格式)
                try:
                    with open(pr_data_file, 'w', encoding='utf-8') as f:
                        json.dump(pr_data, f, indent=2, ensure_ascii=False)
                    default_logger.info(f"保存PR #{pr_number}原始数据成功: {pr_data_file}")
                except Exception as e:
                    default_logger.error(f"保存PR #{pr_number}原始数据失败: {str(e)}")
            
            # 步骤2: 提取建议
            print(f"🤖 PR #{pr_number} 开始建议提取")
            suggestions = self.extract_suggestions(pr_data, pr_number)
            if suggestions is None:
                print(f"✗ PR #{pr_number} 建议提取失败")
                continue
            
            # 保存建议结果 (按照现有格式)
            timestamp = datetime.now().strftime("%a %b %d %H:%M:%S %Y")
            suggestions_file = output_path / f"all_suggestions_{pr_number}_{timestamp}.json"
            try:
                with open(suggestions_file, 'w', encoding='utf-8') as f:
                    json.dump(suggestions, f, indent=2, ensure_ascii=False)
                print(f"✓ PR #{pr_number} 处理完成")
                default_logger.info(f"保存PR #{pr_number}建议成功: {suggestions_file}")
            except Exception as e:
                default_logger.error(f"保存PR #{pr_number}建议失败: {str(e)}")
            
            # 扩展点: 可在此处添加更多处理环节
            # 例如: self.additional_processing_step(pr_data, suggestions, pr_number)
        
        print(f"\n处理完成！")


def main():
    """
    主函数
    """
    parser = argparse.ArgumentParser(
        description="PR数据获取和建议提取Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 处理单个PR
  python process_pr_pipeline.py JabRef jabref --prs 10590
  
  # 处理多个不连续的PR
  python process_pr_pipeline.py JabRef jabref --prs 10590 10595 10600
  
  # 处理连续范围的PR
  python process_pr_pipeline.py JabRef jabref --prs 10590-10600
  
  # 混合使用（单个、范围、多个）
  python process_pr_pipeline.py JabRef jabref --prs 10590 10595 10600-10610 10615
  
  # 指定输出目录
  python process_pr_pipeline.py JabRef jabref --prs 10590-10600 --output results/jabref_batch
        """
    )
    
    parser.add_argument("owner", help="仓库所有者")
    parser.add_argument("repo", help="仓库名称")
    parser.add_argument(
        "--prs", 
        nargs='+', 
        required=True,
        help="PR编号列表，支持单个数字(10590)、范围(10590-10600)或混合使用"
    )
    parser.add_argument(
        "--output",
        default="output",
        help="输出目录路径 (默认: output)"
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="配置文件路径 (默认: config.yaml)"
    )
    parser.add_argument(
        "--token",
        default="PAT.token",
        help="GitHub Personal Access Token文件路径 (默认: PAT.token)"
    )
    
    args = parser.parse_args()
    
    # 检查配置文件
    if not os.path.exists(args.config):
        print(f"错误: 配置文件 {args.config} 不存在")
        sys.exit(1)
    
    # 检查token文件
    if not os.path.exists(args.token):
        print(f"错误: token文件 {args.token} 不存在")
        sys.exit(1)
    
    # 检查环境变量（用于LLM API调用）
    if not os.environ.get("DEEPSEEK_API_KEY"):
        print("警告: 未设置DEEPSEEK_API_KEY环境变量，建议提取功能可能无法正常工作")
        sys.exit(1)
    
    try:
        # 解析PR编号列表
        pr_numbers = parse_pr_list(args.prs)
        print(f"解析到 {len(pr_numbers)} 个PR编号: {pr_numbers}")
        
        # 创建处理器
        processor = PRProcessor(args.owner, args.repo, args.config, args.token)
        
        # 开始处理
        processor.process_pr_list(pr_numbers, args.output)
        
    except ValueError as e:
        print(f"PR编号解析错误: {str(e)}")
        print("请检查PR编号格式，支持的格式：")
        print("  - 单个数字: 10590")
        print("  - 范围格式: 10590-10600")
        print("  - 混合使用: 10590 10595 10600-10610")
        sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n\n用户中断处理")
        sys.exit(1)
    except Exception as e:
        print(f"处理过程中发生异常: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()