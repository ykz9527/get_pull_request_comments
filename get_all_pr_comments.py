#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GitHub Pull Request Comments Fetcher

这个脚本用于获取指定仓库中所有符合状态条件的PR的详细信息，包括评论、审查等。
它首先通过GitHubPRIDsFetcher获取所有符合条件的PR ID，
然后通过GitHubPRCommentsFetcher获取每个PR的详细信息。

使用方法:
    python get_all_pr_comments.py <owner> <repo> [--states <state1> <state2> ...] [--output <output_file>]

示例:
    python get_all_pr_comments.py JabRef jabref --states OPEN CLOSED
    python get_all_pr_comments.py JabRef jabref --states MERGED --output jabref_merged_prs.json
"""

import argparse
import json
import sys
import os
from typing import List, Dict, Any
from get_all_pr_brief import GitHubPRIDsFetcher
from get_pr_comments import GitHubPRCommentsFetcher


class GitHubAllPRDetailsFetcher:
    def __init__(self, config_path: str = "config.yaml", token_path: str = "PAT.token"):
        """
        初始化PR详细信息获取器
        
        Args:
            config_path: 配置文件路径
            token_path: GitHub PAT token文件路径
        """
        self.pr_ids_fetcher = GitHubPRIDsFetcher(config_path, token_path)
        self.pr_comments_fetcher = GitHubPRCommentsFetcher(config_path, token_path)
    
    def get_all_pr_details(self, owner: str, repo: str, states: List[str] = None) -> List[Dict[str, Any]]:
        """
        获取所有符合条件的PR的详细信息
        
        Args:
            owner: 仓库所有者
            repo: 仓库名称
            states: PR状态过滤列表，可选值：OPEN, CLOSED, MERGED
            
        Returns:
            List[Dict[str, Any]]: 包含所有PR详细信息的列表，每个字典都包含prID字段
        """
        print(f"正在获取 {owner}/{repo} 仓库中状态为 {states or 'ALL'} 的PR ID列表...")
        
        # 获取所有符合条件的PR ID
        pr_ids = self.pr_ids_fetcher.get_all_pr_ids(owner, repo, states)
        
        if not pr_ids:
            print("未找到符合条件的PR")
            return []
        
        print(f"找到 {len(pr_ids)} 个符合条件的PR，开始获取详细信息...")
        
        all_pr_details = []
        
        for i, pr_id in enumerate(pr_ids, 1):
            print(f"正在处理第 {i}/{len(pr_ids)} 个PR (ID: {pr_id})...")
            
            try:
                # 获取单个PR的详细信息
                pr_details = self.pr_comments_fetcher.get_pr_comments(owner, repo, pr_id)
                
                # 添加prID字段
                pr_details['prID'] = pr_id
                
                all_pr_details.append(pr_details)
                
            except Exception as e:
                print(f"获取PR {pr_id} 的详细信息时出错: {e}")
                # 继续处理下一个PR，不中断整个流程
                continue
        
        print(f"成功获取了 {len(all_pr_details)} 个PR的详细信息")
        return all_pr_details
    
    def save_to_file(self, data: List[Dict[str, Any]], output_file: str):
        """
        将数据保存到JSON文件
        
        Args:
            data: 要保存的数据
            output_file: 输出文件路径
        """
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            print(f"数据已保存到: {output_file}")
        except Exception as e:
            print(f"保存文件时出错: {e}")
    
    def get_all_pr_details_by_line(self, owner: str, repo: str, output_file: str, states: List[str] = None) -> int:
        """
        获取所有符合条件的PR的详细信息，并逐行写入文件以防止内存溢出
        
        Args:
            owner: 仓库所有者
            repo: 仓库名称
            output_file: 输出文件路径
            states: PR状态过滤列表，可选值：OPEN, CLOSED, MERGED
            
        Returns:
            int: 成功处理的PR数量
        """
        print(f"正在获取 {owner}/{repo} 仓库中状态为 {states or 'ALL'} 的PR ID列表...")
        
        # 获取所有符合条件的PR ID
        pr_ids = self.pr_ids_fetcher.get_all_pr_ids(owner, repo, states)
        
        if not pr_ids:
            print("未找到符合条件的PR")
            return 0
        
        print(f"找到 {len(pr_ids)} 个符合条件的PR，开始获取详细信息并逐行写入文件...")
        
        success_count = 0
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                for i, pr_id in enumerate(pr_ids, 1):
                    print(f"正在处理第 {i}/{len(pr_ids)} 个PR (ID: {pr_id})...")
                    
                    try:
                        # 获取单个PR的详细信息
                        pr_details = self.pr_comments_fetcher.get_pr_comments(owner, repo, pr_id)
                        
                        # 添加prID字段
                        pr_details['prID'] = pr_id
                        
                        # 将PR详细信息写入文件（每行一个JSON对象）
                        json_line = json.dumps(pr_details, ensure_ascii=False)
                        f.write(json_line + '\n')
                        f.flush()  # 确保数据立即写入磁盘
                        
                        success_count += 1
                        
                    except Exception as e:
                        print(f"获取PR {pr_id} 的详细信息时出错: {e}")
                        # 继续处理下一个PR，不中断整个流程
                        continue
            
            print(f"数据已逐行保存到: {output_file}")
            
        except Exception as e:
            print(f"写入文件时出错: {e}")
            return success_count
        
        print(f"成功获取了 {success_count} 个PR的详细信息")
        return success_count


def main():
    parser = argparse.ArgumentParser(
        description='获取GitHub仓库中所有符合条件的PR的详细信息',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python get_all_pr_comments.py JabRef jabref --states OPEN CLOSED
  python get_all_pr_comments.py JabRef jabref --states MERGED --output jabref_merged_prs.json
  python get_all_pr_comments.py JabRef jabref --output jabref_all_prs.json
  python get_all_pr_comments.py JabRef jabref --output jabref_all_prs.jsonl --store-by-line
        """
    )
    
    parser.add_argument('owner', help='仓库所有者')
    parser.add_argument('repo', help='仓库名称')
    parser.add_argument(
        '--states', 
        nargs='*', 
        choices=['OPEN', 'CLOSED', 'MERGED'],
        help='PR状态过滤（可选多个）：OPEN, CLOSED, MERGED。不指定则获取所有状态的PR'
    )
    parser.add_argument(
        '--output', 
        default='all_pr_details.json',
        help='输出文件名（默认：all_pr_details.json）'
    )
    parser.add_argument(
        '--config',
        default='config.yaml',
        help='配置文件路径（默认：config.yaml）'
    )
    parser.add_argument(
        '--token',
        default='PAT.token',
        help='GitHub Personal Access Token文件路径（默认：PAT.token）'
    )
    parser.add_argument(
        '--store-by-line',
        action='store_true',
        help='逐行写入JSON数据以防止内存溢出（仅在指定输出文件时可用）'
    )
    
    args = parser.parse_args()
    
    # 检查 store_by_line 选项的使用条件
    if args.store_by_line:
        # 检查是否明确指定了输出文件（通过检查命令行参数）
        if '--output' not in sys.argv:
            print("错误: --store-by-line 选项只能在明确指定 --output 输出文件时使用")
            sys.exit(1)
    
    # 检查配置文件是否存在
    if not os.path.exists(args.config):
        print(f"错误: 配置文件 {args.config} 不存在")
        sys.exit(1)
    
    try:
        # 创建获取器实例
        fetcher = GitHubAllPRDetailsFetcher(args.config, args.token)
        
        # 根据 store_by_line 选项选择不同的处理方式
        if args.store_by_line:
            # 使用逐行写入方式
            success_count = fetcher.get_all_pr_details_by_line(args.owner, args.repo, args.output, args.states)
            
            # 显示统计信息
            print(f"\n=== 统计信息 ===")
            print(f"总共获取了 {success_count} 个PR的详细信息")
            
            if success_count == 0:
                print("未获取到任何PR详细信息")
        else:
            # 使用传统方式（将所有数据保存在内存中）
            pr_details = fetcher.get_all_pr_details(args.owner, args.repo, args.states)
            
            if pr_details:
                # 保存到文件
                fetcher.save_to_file(pr_details, args.output)
                
                # 显示统计信息
                print(f"\n=== 统计信息 ===")
                print(f"总共获取了 {len(pr_details)} 个PR的详细信息")
                
            else:
                print("未获取到任何PR详细信息")
            
    except KeyboardInterrupt:
        print("\n用户中断操作")
        sys.exit(1)
    except Exception as e:
        print(f"执行过程中出错: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()