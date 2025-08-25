#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Pull Request Comments Fetcher
使用GitHub GraphQL API获取pull request的讨论内容

使用方法:
python get_pr_comments.py <owner> <repo> <pr_number> [--output output.json]

示例:
python get_pr_comments.py JabRef jabref 13553
python get_pr_comments.py JabRef jabref 9399 --output output/pr_data_9399.json
python get_pr_comments.py JabRef jabref 10592 --output output/pr_data_10592.json
python get_pr_comments.py JabRef jabref 11066 --output output/pr_data_11066.json
"""

import requests
import json
import argparse
import sys
import os
import yaml
from typing import Dict, Any
from datetime import datetime
import bisect
try:
    from functools import cache
except ImportError:  # Python < 3.9 fallback
    from functools import lru_cache as cache

class GitHubPRCommentsFetcher:
    def __init__(self, config_path: str = "config.yaml", token_path: str = "PAT.token"):
        """
        初始化GitHub API客户端
        
        Args:
            config_path: 配置文件路径
            token_path: GitHub PAT token文件路径
        """
        self.config = self.load_config(config_path)
        self.token = self.load_token(token_path)
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
                return yaml.safe_load(f)
        except FileNotFoundError:
            print(f"错误: 配置文件 {config_path} 不存在")
            sys.exit(1)
        except yaml.YAMLError:
            print(f"错误: 配置文件 {config_path} 格式错误")
            sys.exit(1)
    
    def load_token(self, token_path: str) -> str:
        """
        从文件加载GitHub Personal Access Token
        
        Args:
            token_path: token文件路径
            
        Returns:
            str: GitHub PAT token
        """
        try:
            with open(token_path, 'r', encoding='utf-8') as f:
                token = f.read().strip()
                if not token:
                    print(f"错误: token文件 {token_path} 为空")
                    sys.exit(1)
                return token
        except FileNotFoundError:
            print(f"错误: token文件 {token_path} 不存在")
            print(f"请创建 {token_path} 文件并将GitHub Personal Access Token写入其中")
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

    @cache
    def _compare_commits(self, owner: str, repo: str, before_sha: str, after_sha: str) -> Dict[str, Any]:
        """
        使用 GitHub REST Compare API 对比两个 commit，获取文件变更详情。
        参考: GET /repos/{owner}/{repo}/compare/{base}...{head}
        返回结构包含 filesChanged 列表，以与现有调用方兼容。
        """
        compare_url = f"https://api.github.com/repos/{owner}/{repo}/compare/{before_sha}...{after_sha}"
        rest_headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json"
        }
        try:
            resp = requests.get(compare_url, headers=rest_headers)
            if resp.status_code != 200:
                print(f"Warning: Could not compare {before_sha} and {after_sha}. HTTP {resp.status_code}: {resp.text}")
                return {}
            payload = resp.json()

            files_changed = []
            for f in payload.get("files", []):
                # 映射 REST 字段到统一返回格式
                change_type = f.get("status")  # added/removed/modified/renamed
                files_changed.append({
                    "path": f.get("filename"),
                    "patch": f.get("patch"),  # 二进制文件可能没有 patch
                    "additions": f.get("additions"),
                    "deletions": f.get("deletions"),
                    "changeType": change_type
                })

            result = {
                "ahead_by": payload.get("ahead_by"),
                "behind_by": payload.get("behind_by"),
                "total_commits": payload.get("total_commits"),
                "filesChanged": files_changed
            }
            return result
        except Exception as e:
            print(f"Warning: Could not compare {before_sha} and {after_sha}. Error: {e}")
            return {}

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
      baseRefOid
      headRefOid
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
            oid
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
        }}
      }}
      files(first: {self.limits['files']}) {{
        nodes {{
          path
          additions
          deletions
          changeType
        }}
      }}
      
      timelineItems(first: 250, itemTypes: [PULL_REQUEST_COMMIT]) {{
        nodes {{
          ... on PullRequestCommit {{
            commit {{
              oid
              committedDate
            }}
          }}
        }}
      }}
      
      reviewThreads(first: {self.limits['reviews']}) {{
        nodes {{
          id
          isResolved
          isOutdated
          path
          line
          startLine
          originalLine
          originalStartLine
          comments(first: {self.limits['review_comments']}) {{
            nodes {{
              id
              body
              createdAt
              path
              diffHunk
              author {{
                login
              }}
            }}
          }}
        }}
      }}
      
      reviews(first: {self.limits['reviews']}) {{
        nodes {{
          id
          body
          state
          submittedAt
          author {{
            login
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

        # 步骤三：预处理时间线上的 Commit，按时间排序
        # =========================================
        timeline_commits = []
        pr_data = data["data"]["repository"]["pullRequest"]
        if pr_data.get("timelineItems"):
            for item in pr_data["timelineItems"]["nodes"]:
                # 确保节点不为空且包含 commit 数据
                if item and "commit" in item:
                    commit_date = datetime.fromisoformat(item["commit"]["committedDate"].replace("Z", "+00:00"))
                    timeline_commits.append({
                        "oid": item["commit"]["oid"],
                        "date": commit_date
                    })
        
        # 按提交时间升序排序
        timeline_commits.sort(key=lambda c: c["date"])
        # 提取出排序后的时间和 OID 列表，用于二分查找
        commit_dates = [c["date"] for c in timeline_commits]
        commit_oids = [c["oid"] for c in timeline_commits]

        # 步骤四：遍历评论，为其匹配正确的“修改前”Commit
        # ===============================================
        after_sha = pr_data.get("headRefOid")
        
        if not after_sha or not timeline_commits:
            return pr_data

        if pr_data.get("reviewThreads"):
            for thread in pr_data["reviewThreads"]["nodes"]:
                for comment in thread["comments"]["nodes"]:
                    comment_created_at = datetime.fromisoformat(comment["createdAt"].replace("Z", "+00:00"))
                    
                    # 使用二分查找，找到最后一个时间上不晚于评论创建时间的 commit
                    # `bisect_right` 返回插入点，减 1 就是我们想要的 commit 的索引
                    index = bisect.bisect_right(commit_dates, comment_created_at) - 1
                    
                    if index >= 0:
                        before_sha = commit_oids[index]
                        comment["matched_commit_oid"] = before_sha # 将我们精确匹配到的 oid 存起来
                        
                        if before_sha != after_sha:
                            print(f"分析: 评论(id: {comment['id']})后有代码更新，精确比较 {before_sha[:7]}...{after_sha[:7]}")
                            changes = self._compare_commits(owner, repo, before_sha, after_sha)
                            comment["changes_after_review"] = changes
                        else:
                            comment["changes_after_review"] = {}
                    else:
                        # 如果找不到（比如评论时间比所有 commit 都早），则标记为空
                        comment["matched_commit_oid"] = None
                        comment["changes_after_review"] = {}

        # 仅汇总“全局讨论”：Issue comments + 非空 Review body
        global_discussions = []

        # 1) Issue comments
        if pr_data.get("comments") and pr_data["comments"].get("nodes"):
            for c in pr_data["comments"]["nodes"]:
                global_discussions.append({
                    "id": c.get("id"),
                    "body": c.get("body"),
                    "author": (c.get("author") or {}).get("login"),
                    "createdAt": c.get("createdAt"),
                    "source_type": "issue_comment"
                })

        # 2) Review 总评正文（仅保留非空 body）
        if pr_data.get("reviews") and pr_data["reviews"].get("nodes"):
            for r in pr_data["reviews"]["nodes"]:
                body = (r.get("body") or "").strip()
                if body:
                    global_discussions.append({
                        "id": r.get("id"),
                        "body": body,
                        "author": (r.get("author") or {}).get("login"),
                        "createdAt": r.get("submittedAt"),
                        "state": r.get("state"),
                        "source_type": "review_body"
                    })

        # 按时间排序（升序），缺失时间放末尾
        def _global_sort_key(item):
            ts = item.get("createdAt")
            try:
                return datetime.fromisoformat(ts.replace("Z", "+00:00")) if ts else datetime.max
            except Exception:
                return datetime.max

        global_discussions.sort(key=_global_sort_key)
        pr_data["globalDiscussions"] = global_discussions

        return pr_data
    
    def get_file_contents(self, owner: str, repo: str, file_paths: list, base_sha: str = None, head_sha: str = None) -> Dict:
        """
        获取指定文件的修改前后完整内容
        
        Args:
            owner: 仓库所有者
            repo: 仓库名称
            file_paths: 文件路径列表
            base_sha: 基础分支的commit SHA（修改前）
            head_sha: 头分支的commit SHA（修改后）
            
        Returns:
            Dict: 包含文件内容的字典
        """
        # 构建动态查询，为每个文件创建别名
        file_queries = []
        for i, file_path in enumerate(file_paths):
            # 修改后的文件内容
            file_queries.append(f"""
            file_{i}_after: object(expression: "{head_sha or 'HEAD'}:{file_path}") {{
              ... on Blob {{
                text
                byteSize
                isBinary
              }}
            }}""")
            
            # 修改前的文件内容
            file_queries.append(f"""
            file_{i}_before: object(expression: "{base_sha or 'HEAD~1'}:{file_path}") {{
              ... on Blob {{
                text
                byteSize
                isBinary
              }}
            }}""")
        
        query = f"""
        query($owner: String!, $repo: String!) {{
          repository(owner: $owner, name: $repo) {{
            {''.join(file_queries)}
          }}
        }}
        """
        
        variables = {
            "owner": owner,
            "repo": repo
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
        
        # 重新组织数据结构
        result = {}
        repo_data = data["data"]["repository"]
        
        for i, file_path in enumerate(file_paths):
            result[file_path] = {
                "before": repo_data.get(f"file_{i}_before"),
                "after": repo_data.get(f"file_{i}_after")
            }
        
        return result
    
    def fetch_pr_data(self, owner: str, repo: str, pr_number: int, fetch_code_snippet: bool = False) -> str:
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
            
            # 获取文件变更的完整内容（仅在启用时）
            if fetch_code_snippet and 'files' in pr_data and 'nodes' in pr_data['files']:
                file_paths = [file_node['path'] for file_node in pr_data['files']['nodes']]
                if file_paths:
                    print(f"正在获取 {len(file_paths)} 个文件的完整内容...")
                    try:
                        # 使用PR的正确base和head commit SHA
                        base_sha = pr_data.get('baseRefOid')
                        head_sha = pr_data.get('headRefOid')
                        print(f"Base SHA: {base_sha}, Head SHA: {head_sha}")
                        
                        file_contents = self.get_file_contents(owner, repo, file_paths, base_sha, head_sha)
                        # 将文件内容添加到对应的文件节点中
                        for file_node in pr_data['files']['nodes']:
                            file_path = file_node['path']
                            if file_path in file_contents:
                                file_node['fullContent'] = file_contents[file_path]
                        print("文件内容获取完成")
                    except Exception as e:
                        print(f"获取文件内容时出错: {e}")
                        # 即使获取文件内容失败，也继续返回基本的PR数据
            
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
  python get_pr_comments.py JabRef jabref 13553 --fetch-code-snippet --output pr_data.json
  python get_pr_comments.py RylynnWang TestGraphQL 1 --output test_pr_data.json
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
        default="config.yaml",
        help="配置文件路径 (默认: config.yaml)"
    )
    parser.add_argument(
        "--token",
        default="PAT.token",
        help="GitHub Personal Access Token文件路径 (默认: PAT.token)"
    )
    parser.add_argument(
        "--fetch-code-snippet",
        action="store_true",
        help="获取文件的完整代码内容 (默认: 不获取)"
    )
    
    args = parser.parse_args()
    
    # 检查配置文件是否存在
    if not os.path.exists(args.config):
        print(f"错误: 配置文件 {args.config} 不存在")
        print("请确保配置文件包含以下格式:")
        print("limits:")
        print("  comments: 100")
        print("  reviews: 100")
        print("  review_comments: 50")
        print("  commits: 100")
        print("  closing_issues: 25")
        print("  reactions: 10")
        sys.exit(1)
    
    # 检查token文件是否存在
    if not os.path.exists(args.token):
        print(f"错误: token文件 {args.token} 不存在")
        print(f"请创建 {args.token} 文件并将GitHub Personal Access Token写入其中")
        sys.exit(1)
    
    # 创建fetcher
    fetcher = GitHubPRCommentsFetcher(args.config, args.token)

    # 获取PR数据
    result = fetcher.fetch_pr_data(args.owner, args.repo, args.pr_number, args.fetch_code_snippet)

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