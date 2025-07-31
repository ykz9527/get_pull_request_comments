#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Pull Request Comments Fetcher
使用GitHub GraphQL API获取pull request的讨论内容

使用方法:
python get_pr_comments.py <owner> <repo> <pr_number> [--output output.json]

示例:
python get_pr_comments.py JabRef jabref 13553
python get_pr_comments.py JabRef jabref 13553 --output pr_data.json
"""

import requests
import json
import argparse
import sys
import os
from typing import Dict

class GitHubPRCommentsFetcher:
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
    
    def load_config(self, config_path: str) -> Dict:
        """
        加载配置文件
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            Dict: 配置字典
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
    
    def get_rate_limit_info(self) -> Dict:
        """
        获取GitHub API配额信息
        
        Returns:
            Dict: 包含API配额信息的字典
        """
        query = """
        query {
          rateLimit {
            limit
            remaining
            resetAt
            used
            cost
          }
        }
        """
        
        response = requests.post(
            self.api_url,
            headers=self.headers,
            json={"query": query}
        )
        
        if response.status_code == 200:
            data = response.json()
            if "errors" not in data:
                return data["data"]["rateLimit"]
        
        return None
    
    def get_pr_comments(self, owner: str, repo: str, pr_number: int) -> Dict:
        """
        获取pull request的所有讨论内容
        
        Args:
            owner: 仓库所有者
            repo: 仓库名称
            pr_number: PR编号
            
        Returns:
            Dict: 包含PR信息和评论的字典
        """
        query = f"""
        query($owner: String!, $repo: String!, $number: Int!) {{
          repository(owner: $owner, name: $repo) {{
            pullRequest(number: $number) {{
              title
              body
              url
              state
              createdAt
              updatedAt
              author {{
                login
              }}
              closingIssuesReferences(first: {self.limits['closing_issues']}) {{
                nodes {{
                  number
                  title
                }}
              }}
              commits(first: {self.limits['commits']}) {{
                totalCount
                nodes {{
                  commit {{
                    message
                    committedDate
                    author {{
                      user {{
                        login
                      }}
                    }}
                  }}
                }}
              }}
              comments(first: {self.limits['comments']}) {{
                nodes {{
                  id
                  body
                  createdAt
                  updatedAt
                  author {{
                    login
                  }}
                  reactions(first: {self.limits['reactions']}) {{
                    nodes {{
                      content
                      user {{
                        login
                      }}
                    }}
                  }}
                }}
                pageInfo {{
                  hasNextPage
                  endCursor
                }}
              }}
              reviews(first: {self.limits['reviews']}) {{
                nodes {{
                  id
                  body
                  state
                  createdAt
                  author {{
                    login
                  }}
                  comments(first: {self.limits['review_comments']}) {{
                    nodes {{
                      id
                      body
                      createdAt
                      path
                      line
                      startLine
                      originalLine
                      originalStartLine
                      diffHunk
                      author {{
                        login
                      }}
                    }}
                  }}
                }}
              }}
            }}
          }}
        }}
        """
        
        variables = {
            "owner": owner,
            "repo": repo,
            "number": pr_number
        }
        
        response = requests.post(
            self.api_url,
            headers=self.headers,
            json={"query": query, "variables": variables}
        )
        
        if response.status_code != 200:
            raise Exception(f"API请求失败: {response.status_code} - {response.text}")
        
        data = response.json()
        
        if "errors" in data:
            raise Exception(f"GraphQL错误: {data['errors']}")
        
        return data["data"]["repository"]["pullRequest"]
    
    def fetch_pr_data(self, owner: str, repo: str, pr_number: int) -> str:
        """
        获取PR数据并返回JSON字符串
        
        Args:
            owner: 仓库所有者
            repo: 仓库名称
            pr_number: PR编号
            
        Returns:
            str: JSON格式的PR数据
        """
        try:
            print(f"正在获取 {owner}/{repo} PR #{pr_number} 的讨论内容...")
            
            # 获取查询前的API配额信息
            rate_limit_before = self.get_rate_limit_info()
            
            # 获取PR数据
            pr_data = self.get_pr_comments(owner, repo, pr_number)
            
            # 获取查询后的API配额信息
            rate_limit_after = self.get_rate_limit_info()
            
            # 计算本次查询消耗的点数
            cost_info = {}
            if rate_limit_before and rate_limit_after:
                cost_info = {
                    "queryCost": rate_limit_before["remaining"] - rate_limit_after["remaining"],
                    "rateLimit": {
                        "limit": rate_limit_after["limit"],
                        "remaining": rate_limit_after["remaining"],
                        "used": rate_limit_after["used"],
                        "resetAt": rate_limit_after["resetAt"]
                    }
                }
                print(f"本次查询消耗点数: {cost_info['queryCost']}")
                print(f"剩余配额: {rate_limit_after['remaining']}/{rate_limit_after['limit']}")
                print(f"配额重置时间: {rate_limit_after['resetAt']}")
            
            # 将配额信息添加到结果中
            result = {
                "prData": pr_data,
                "apiUsage": cost_info
            }
            
            return result
        except Exception as e:
            error_data = {"error": str(e)}
            return error_data

def main():
    """
    主函数
    """
    parser = argparse.ArgumentParser(
        description="获取GitHub Pull Request的讨论内容",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python get_pr_comments.py JabRef jabref 13553
  python get_pr_comments.py JabRef jabref 13553 --output pr_data.json
        """
    )
    
    parser.add_argument("owner", help="仓库所有者")
    parser.add_argument("repo", help="仓库名称")
    parser.add_argument("pr_number", type=int, help="Pull Request编号")
    parser.add_argument(
        "--output", 
        help="输出文件名，不指定则输出到控制台"
    )
    parser.add_argument(
        "--config",
        default="config.json",
        help="配置文件路径 (默认: config.json)"
    )
    
    args = parser.parse_args()
    
    # 检查配置文件是否存在
    if not os.path.exists(args.config):
        print(f"错误: 配置文件 {args.config} 不存在")
        print("请确保配置文件包含以下格式:")
        print(json.dumps({
            "github_token": "your_github_token_here",
            "limits": {
                "comments": 100,
                "reviews": 100,
                "review_comments": 50,
                "commits": 100,
                "closing_issues": 25,
                "reactions": 10
            }
        }, indent=2))
        sys.exit(1)
    
    # 创建fetcher
    fetcher = GitHubPRCommentsFetcher(args.config)
    
    # 获取PR数据
    result = fetcher.fetch_pr_data(args.owner, args.repo, args.pr_number)

    result = json.dumps(result, indent=4, ensure_ascii=False)
    
    # 输出结果
    if args.output is None:
        print("\n=== PR数据 (JSON格式) ===")
        print(result)
    else:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(result)
            print(f"\nPR数据已保存到 {args.output}")
        except Exception as e:
            print(f"保存文件时出错: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main()