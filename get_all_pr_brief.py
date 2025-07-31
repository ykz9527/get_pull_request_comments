#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Pull Request Information Fetcher
获取GitHub仓库的所有pull request ID列表或详细信息

使用方法:
python get_all_pr_brief.py <owner> <repo> [--states STATE1 STATE2 ...] [--output FILE] [--detailed]

示例:
# 获取PR ID列表
python get_all_pr_brief.py JabRef jabref
python get_all_pr_brief.py JabRef jabref --states OPEN --output pr_ids.json

# 获取PR详细信息
python get_all_pr_brief.py JabRef jabref --detailed
python get_all_pr_brief.py JabRef jabref --detailed --states OPEN CLOSED --output detailed_prs.json

可获取的PR信息包括:
- number: PR编号
- title: PR标题
- state: PR状态 (OPEN/CLOSED/MERGED)
- createdAt: 创建时间
- updatedAt: 更新时间
- closedAt: 关闭时间
- mergedAt: 合并时间
- author: 作者用户名
- mergeable: 是否可合并
- merged: 是否已合并
- isDraft: 是否为草稿
- additions: 新增行数
- deletions: 删除行数
- changedFiles: 修改文件数
- url: PR链接
- headRefName: 源分支名
- baseRefName: 目标分支名
"""

import requests
import json
import argparse
import sys
from typing import List, Dict, Any

class GitHubPRIDsFetcher:
    def __init__(self, config_path: str = "config.json"):
        """
        初始化GitHub API客户端
        
        Args:
            config_path: 配置文件路径
        """
        self.config = self.load_config(config_path)
        self.token = self.config["github_token"]
        self.limits = self.config["limits"]
        self.api_url = "https://api.github.com/graphql"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def load_config(self, config_path: str) -> dict:
        """
        加载配置文件
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            dict: 配置字典
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"错误: 配置文件 {config_path} 不存在")
            sys.exit(1)
        except json.JSONDecodeError:
            print(f"错误: 配置文件 {config_path} 格式错误")
            sys.exit(1)
    
    def get_all_pr_ids(self, owner: str, repo: str, states: List[str] = None) -> List[int]:
        """
        获取仓库的所有pull request ID
        
        Args:
            owner: 仓库所有者
            repo: 仓库名称
            states: PR状态过滤列表，可选值：OPEN, CLOSED, MERGED
            
        Returns:
            List[int]: PR ID列表
        """
        pr_data = self.get_all_pr_info(owner, repo, states)
        return [pr["number"] for pr in pr_data]
    
    def get_all_pr_info(self, owner: str, repo: str, states: List[str] = None) -> List[Dict[str, Any]]:
        """
        获取仓库的所有pull request详细信息
        
        Args:
            owner: 仓库所有者
            repo: 仓库名称
            states: PR状态过滤列表，可选值：OPEN, CLOSED, MERGED
            
        Returns:
            List[Dict[str, Any]]: PR详细信息列表
        """
        pr_info_list = []
        has_next_page = True
        cursor = None
        
        while has_next_page:
            # 构建状态过滤条件
            states_filter = ""
            if states:
                states_str = ", ".join([f"{state}" for state in states])
                states_filter = f", states: [{states_str}]"
            
            query = f"""
             query($owner: String!, $repo: String!, $cursor: String) {{
               repository(owner: $owner, name: $repo) {{
                 pullRequests(first: {self.limits['pull_requests_per_page']}, after: $cursor, orderBy: {{field: CREATED_AT, direction: DESC}}{states_filter}) {{
                  nodes {{
                    number
                    title
                    state
                    createdAt
                    updatedAt
                    closedAt
                    mergedAt
                    author {{
                      login
                    }}
                    mergeable
                    merged
                    isDraft
                    additions
                    deletions
                    changedFiles
                    url
                    headRefName
                    baseRefName
                  }}
                  pageInfo {{
                    hasNextPage
                    endCursor
                  }}
                }}
              }}
            }}
            """
            
            variables = {
                "owner": owner,
                "repo": repo,
                "cursor": cursor
            }
            
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json={"query": query, "variables": variables}
            )
            
            if response.status_code != 200:
                print(f"API请求失败: {response.status_code}")
                print(response.text)
                return []
            
            data = response.json()
            
            if "errors" in data:
                print(f"GraphQL错误: {data['errors']}")
                return []
            
            pull_requests = data["data"]["repository"]["pullRequests"]
            
            # 提取PR信息
            for pr in pull_requests["nodes"]:
                pr_info = {
                    "number": pr["number"],
                    "title": pr["title"],
                    "state": pr["state"],
                    "createdAt": pr["createdAt"],
                    "updatedAt": pr["updatedAt"],
                    "closedAt": pr["closedAt"],
                    "mergedAt": pr["mergedAt"],
                    "author": pr["author"]["login"] if pr["author"] else None,
                    "mergeable": pr["mergeable"],
                    "merged": pr["merged"],
                    "isDraft": pr["isDraft"],
                    "additions": pr["additions"],
                    "deletions": pr["deletions"],
                    "changedFiles": pr["changedFiles"],
                    "url": pr["url"],
                    "headRefName": pr["headRefName"],
                    "baseRefName": pr["baseRefName"]
                }
                pr_info_list.append(pr_info)
            
            # 检查是否还有下一页
            page_info = pull_requests["pageInfo"]
            has_next_page = page_info["hasNextPage"]
            cursor = page_info["endCursor"]
            
            print(f"已获取 {len(pr_info_list)} 个PR信息...")
        
        return pr_info_list

def main():
    parser = argparse.ArgumentParser(
        description="获取GitHub仓库的所有pull request ID或详细信息",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python get_all_pr_brief.py JabRef jabref
  python get_all_pr_brief.py JabRef jabref --detailed --output detailed_prs.json
  python get_all_pr_brief.py JabRef jabref --states OPEN CLOSED --output pr_data.json
        """
    )
    parser.add_argument("owner", help="仓库所有者")
    parser.add_argument("repo", help="仓库名称")
    parser.add_argument("--states", nargs="+", choices=["OPEN", "CLOSED", "MERGED"], 
                       help="过滤PR状态，可选：OPEN CLOSED MERGED")
    parser.add_argument(
        "--output", 
        help="输出文件名，不指定则输出到控制台"
    )
    parser.add_argument("--detailed", action="store_true", help="获取详细信息而不仅仅是ID")
    parser.add_argument("--ids-only", action="store_true", help="仅获取ID列表（默认行为）")
    
    args = parser.parse_args()
    
    try:
        fetcher = GitHubPRIDsFetcher()
        
        # 根据参数决定获取详细信息还是仅ID
        if args.detailed:
            pr_data = fetcher.get_all_pr_info(args.owner, args.repo, args.states)
            data_to_save = pr_data
            data_type = "详细信息"
            file_suffix = "_pr_info"
        else:
            pr_ids = fetcher.get_all_pr_ids(args.owner, args.repo, args.states)
            data_to_save = pr_ids
            data_type = "ID"
            file_suffix = "_pr_ids"
        
        if data_to_save:
            states_info = f"（状态过滤: {', '.join(args.states)}）" if args.states else ""
            print(f"\n成功获取到 {len(data_to_save)} 个PR {data_type}{states_info}")
            
            # 根据输出方式处理结果
            if args.output is None:
                print(f"\n=== PR {data_type} (JSON格式) ===")
                print(json.dumps(data_to_save, indent=2, ensure_ascii=False))
            else:
                # 输出到文件
                output_file = args.output
                
                try:
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(data_to_save, f, indent=2, ensure_ascii=False)
                    print(f"\nPR {data_type}已保存到: {output_file}")
                except Exception as e:
                    print(f"保存文件时出错: {e}")
                    sys.exit(1)
        else:
            print(f"未获取到任何PR {data_type}")
            
    except Exception as e:
        print(f"发生错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()