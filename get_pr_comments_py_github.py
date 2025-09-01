#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Pull Request Comments Fetcher
使用PyGithub库获取pull request的讨论内容

使用方法:
python get_pr_comments_py_github.py <owner> <repo> <pr_number> [--output output.json]

示例:
python get_pr_comments_py_github.py JabRef jabref 13553
python get_pr_comments_py_github.py JabRef jabref 9399 --output output/pr_data_py_github_9399.json
python get_pr_comments_py_github.py JabRef jabref 10592 --output output/pr_data_py_github_10592.json
python get_pr_comments_py_github.py JabRef jabref 11066 --output output/pr_data_py_github_11066.json
"""

import requests
import json
import argparse
import sys
import os
import yaml
import re
from typing import Dict, Any, List
from datetime import datetime
import bisect
from collections import defaultdict
from github import Github
from github.GithubException import UnknownObjectException, GithubException
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
        self.github = Github(self.token)
        # 保留REST API headers用于compare API
        self.rest_headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json"
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
        获取GitHub API配额信息（已简化，不再获取详细配额）
        
        Returns:
            Dict: 简化的配额信息
        """
        # 简化配额逻辑，不再依赖复杂的API调用
        return {
            "limit": 5000,
            "remaining": 4999,
            "resetAt": self._format_datetime(datetime.now()),
            "used": 1,
            "cost": 1
        }

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
        try:
            repo_obj = self.github.get_repo(f"{owner}/{repo}")
            pr = repo_obj.get_pull(pr_number)
        except UnknownObjectException:
            raise Exception(f"无法找到仓库 '{owner}/{repo}' 或 PR #{pr_number}")
        except GithubException as e:
            raise Exception(f"GitHub API错误: {e}")

        # 构建PR基本信息
        prInfo = {
            "title": pr.title,
            "body": pr.body,
            "url": pr.html_url,
            "state": pr.state.upper(),
            "createdAt": self._format_datetime(pr.created_at),
            "updatedAt": self._format_datetime(pr.updated_at),
            "baseRefOid": pr.base.sha,
            "headRefOid": pr.head.sha,
            "author": pr.user.login if pr.user else None
        }

        pr_data = {
            "prInfo": prInfo
        }

        # 获取提交记录
        commits_data = []
        commits = list(pr.get_commits())
        
        # 获取关联的问题 (closingIssuesReferences)
        # 分析PR描述和提交消息中的Issue关联关键词
        linked_issue_numbers = set()
        
        # 分析PR描述
        if pr.body:
            pr_issues = self._extract_linked_issues(repo_obj, pr.body)
            linked_issue_numbers.update(pr_issues)
        
        # 分析所有提交消息
        for commit in commits:
            if commit.commit.message:
                commit_issues = self._extract_linked_issues(repo_obj, commit.commit.message)
                linked_issue_numbers.update(commit_issues)
        
        # 获取Issue详细信息
        linked_issues_info = []
        if linked_issue_numbers:
            linked_issues_info = self._get_linked_issues_info(repo_obj, list(linked_issue_numbers))
        
        pr_data["closingIssuesReferences"] = {"nodes": linked_issues_info}
        for commit in commits:
            commit_info = {
                    "oid": commit.sha,
                    "message": commit.commit.message,
                    "committedDate": self._format_datetime(commit.commit.committer.date),
                    "author": commit.author.login if commit.author else None
            }
            commits_data.append(commit_info)

        pr_data["commits"] = commits_data

        # 获取普通评论 (issue comments)
        comments_data = []
        comments = list(pr.get_issue_comments())
        for comment in comments:
            comment_info = {
                "id": str(comment.id),
                "body": comment.body,
                "createdAt": self._format_datetime(comment.created_at),
                "updatedAt": self._format_datetime(comment.updated_at),
                "author": comment.user.login if comment.user else None
            }
            comments_data.append(comment_info)

        pr_data["comments"] = comments_data

        # 获取文件变更
        files_data = []
        files = list(pr.get_files())
        for file in files:
            file_info = {
                "path": file.filename,
                "additions": file.additions,
                "deletions": file.deletions,
                "changeType": file.status.upper()
            }
            files_data.append(file_info)

        pr_data["files"] = files_data

        # 构建时间线提交信息（用于后续的评论匹配）
        timeline_commits = []
        for commit in commits:
            commit_date = commit.commit.committer.date
            timeline_commits.append({
                "oid": commit.sha,
                "date": commit_date  # 保持原始datetime对象用于比较
            })
        
        # 按提交时间升序排序
        timeline_commits.sort(key=lambda c: c["date"])
        commit_dates = [c["date"] for c in timeline_commits]
        commit_oids = [c["oid"] for c in timeline_commits]

        # 获取正式审查
        reviews_data = []
        reviews = list(pr.get_reviews())
        for review in reviews:
            review_info = {
                "id": str(review.id),
                "body": review.body,
                "state": review.state,
                "submittedAt": self._format_datetime(review.submitted_at),
                "author": review.user.login if review.user else None
            }
            reviews_data.append(review_info)

        # 获取代码审查评论和线索（传入reviews_data用于关联）
        review_threads_data = self._build_review_threads(pr, reviews_data)
        pr_data["reviewThreads"] = review_threads_data

        pr_data["reviews"] = reviews_data

        # 添加时间线信息以保持兼容性
        pr_data["timelineItems"] = {
            "nodes": [
                {
                    "commit": {
                        "oid": tc["oid"],
                        "committedDate": self._format_datetime(tc["date"])
                    }
                }
                for tc in timeline_commits
            ]
        }

        # # 处理评论的commit匹配和变更分析
        # after_sha = pr_data.get("headRefOid")
        
        # if after_sha and timeline_commits:
        #     for thread in pr_data["reviewThreads"]["nodes"]:
        #         for comment in thread["comments"]["nodes"]:
        #             comment_created_at = datetime.fromisoformat(comment["createdAt"].replace("Z", "+00:00"))
                    
        #             # 使用二分查找，找到最后一个时间上不晚于评论创建时间的 commit
        #             index = bisect.bisect_right(commit_dates, comment_created_at) - 1
                    
        #             if index >= 0:
        #                 before_sha = commit_oids[index]
        #                 comment["matched_commit_oid"] = before_sha
                        
        #                 if before_sha != after_sha:
        #                     print(f"分析: 评论(id: {comment['id']})后有代码更新，精确比较 {before_sha[:7]}...{after_sha[:7]}")
        #                     changes = self._compare_commits(owner, repo, before_sha, after_sha)
        #                     comment["changes_after_review"] = changes
        #                 else:
        #                     comment["changes_after_review"] = {}
        #             else:
        #                 comment["matched_commit_oid"] = None
        #                 comment["changes_after_review"] = {}

        # 构建全局讨论汇总
        global_discussions = []

        # 1) Issue comments
        for c in comments_data:
                global_discussions.append({
                    "id": c.get("id"),
                    "body": c.get("body"),
                    "author": c.get("author"),
                    "createdAt": c.get("createdAt"),
                    "source_type": "issue_comment"
                })

        # 2) Review 总评正文（仅保留非空 body）
        for r in reviews_data:
                body = (r.get("body") or "").strip()
                if body:
                    global_discussions.append({
                        "id": r.get("id"),
                        "body": body,
                        "author": r.get("author"),
                        "createdAt": r.get("submittedAt"),
                        "state": r.get("state"),
                        "source_type": "review_body"
                    })

        # 按时间排序（升序）
        def _global_sort_key(item):
            ts = item.get("createdAt")
            try:
                return datetime.fromisoformat(ts.replace("Z", "+00:00")) if ts else datetime.max
            except Exception:
                return datetime.max

        global_discussions.sort(key=_global_sort_key)
        pr_data["globalDiscussions"] = global_discussions

        return pr_data

    def _build_review_threads(self, pr, reviews_data: List[Dict]) -> List[Dict]:
        """
        构建审查评论线索，模拟GraphQL的reviewThreads结构
        参考extract_pr_test.py的线索构建逻辑
        
        Args:
            pr: PyGithub的PullRequest对象
            reviews_data: 审查数据列表，用于建立关联
            
        Returns:
            List[Dict]: 审查线索列表
        """
        # 获取所有代码审查评论
        all_review_comments = list(pr.get_review_comments())
        
        # 建立review_id到review_body_id的映射（用于关联globalDiscussions）
        review_id_to_body_id = {}
        for review_info in reviews_data:
            body = (review_info.get("body") or "").strip()
            if body:  # 只有非空body的review才会出现在globalDiscussions中
                review_id_to_body_id[review_info["id"]] = review_info["id"]
        
        # 构建线索：key是顶层评论的id，value是该线索中所有评论的列表
        threads = defaultdict(list)
        top_level_comments = {}
        replies = []

        for comment in all_review_comments:
            if comment.in_reply_to_id is None:
                # 这是一个顶层评论，是线索的开始
                top_level_comments[comment.id] = comment
                threads[comment.id].append(comment)
            else:
                # 这是一个回复
                replies.append(comment)

        # 将回复归入各自的线索
        for reply in replies:
            if reply.in_reply_to_id in threads:
                threads[reply.in_reply_to_id].append(reply)
        
        # 按时间排序每个线索内部的评论
        for thread_id in threads:
            threads[thread_id].sort(key=lambda c: c.created_at)

        # 转换为所需的数据结构
        review_threads = []
        for thread_id, comment_list in threads.items():
            if not comment_list:
                continue
                
            top_comment = top_level_comments[thread_id]
            
            # 构建线索的评论列表
            thread_comments = []
            for comment in comment_list:
                comment_data = {
                    "id": str(comment.id),
                    "body": comment.body,
                    "createdAt": self._format_datetime(comment.created_at),
                    "path": comment.path,
                    "diffHunk": comment.diff_hunk,
                    "author": comment.user.login if comment.user else None
                }
                thread_comments.append(comment_data)
            
            # 获取该线索关联的review_body_id（如果存在）
            related_review_body_id = None
            if hasattr(top_comment, 'pull_request_review_id') and top_comment.pull_request_review_id:
                review_id_str = str(top_comment.pull_request_review_id)
                related_review_body_id = review_id_to_body_id.get(review_id_str)
            
            # 构建线索信息
            thread_data = {
                "id": f"thread_{thread_id}",  # 生成一个线索ID
                "isResolved": False,  # PyGithub没有直接的resolved状态，设为False
                "isOutdated": top_comment.position is None,  # 如果position为None表示可能过时
                "path": top_comment.path,
                "line": top_comment.line,
                "diffHunk": getattr(top_comment, 'diff_hunk', None),
                "startLine": getattr(top_comment, 'start_line', None),
                "originalLine": getattr(top_comment, 'original_line', None),
                "originalStartLine": getattr(top_comment, 'original_start_line', None),
                "related_review_body_id": related_review_body_id,  # 关联的globalDiscussions中review_body的ID
                "comments": {
                    "nodes": thread_comments
                }
            }
            review_threads.append(thread_data)
        
        return review_threads

    def _format_datetime(self, dt) -> str:
        """简单的时间格式化"""
        if dt is None:
            return None
        
        # 简单粗暴：直接转字符串，去掉时区信息，加Z
        dt_str = str(dt)
        if '+' in dt_str:
            dt_str = dt_str.split('+')[0]
        if 'T' not in dt_str:
            dt_str = dt_str.replace(' ', 'T')
        return dt_str + "Z"
    
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
        result = {}
        repo_obj = self.github.get_repo(f"{owner}/{repo}")
        
        for file_path in file_paths:
            file_result = {
                "before": None,
                "after": None
            }
            
            # 获取修改后的文件内容
            if head_sha:
                try:
                    after_content = repo_obj.get_contents(file_path, ref=head_sha)
                    if hasattr(after_content, 'decoded_content'):  # 这是一个文件而非目录
                        decoded_content = after_content.decoded_content
                        file_result["after"] = {
                            "text": decoded_content.decode('utf-8') if isinstance(decoded_content, bytes) else str(decoded_content),
                            "byteSize": after_content.size,
                            "isBinary": self._is_binary_content(decoded_content if isinstance(decoded_content, bytes) else decoded_content.encode())
                        }
                except Exception as e:
                    print(f"无法获取文件 {file_path} 的修改后内容: {e}")
                    file_result["after"] = None
            
            # 获取修改前的文件内容
            if base_sha:
                try:
                    before_content = repo_obj.get_contents(file_path, ref=base_sha)
                    if hasattr(before_content, 'decoded_content'):  # 这是一个文件而非目录
                        decoded_content = before_content.decoded_content
                        file_result["before"] = {
                            "text": decoded_content.decode('utf-8') if isinstance(decoded_content, bytes) else str(decoded_content),
                            "byteSize": before_content.size,
                            "isBinary": self._is_binary_content(decoded_content if isinstance(decoded_content, bytes) else decoded_content.encode())
                        }
                except Exception as e:
                    print(f"无法获取文件 {file_path} 的修改前内容: {e}")
                    file_result["before"] = None
            
            result[file_path] = file_result
        
        return result

    def _is_binary_content(self, content: bytes) -> bool:
        """
        判断内容是否为二进制文件
        
        Args:
            content: 文件内容字节
            
        Returns:
            bool: 是否为二进制文件
        """
        if not content:
            return False
        
        # 检查是否包含null字节，这通常表示二进制文件
        return b'\x00' in content[:8192]  # 只检查前8KB
    
    def _extract_linked_issues(self, repo_obj, text_content: str) -> List[int]:
        """
        从文本内容中提取关联的Issue编号
        
        Args:
            repo_obj: PyGithub的Repository对象
            text_content: 要分析的文本内容
            
        Returns:
            List[int]: 提取出的Issue编号列表
        """
        if not text_content:
            return []
        
        # GitHub支持的关联Issue关键词模式
        # 参考: https://docs.github.com/en/issues/tracking-your-work-with-issues/linking-a-pull-request-to-an-issue
        patterns = [
            r'\b(?:close|closes|closed|fix|fixes|fixed|resolve|resolves|resolved)\s+#(\d+)',
            r'\b(?:close|closes|closed|fix|fixes|fixed|resolve|resolves|resolved)\s+' + 
            re.escape(repo_obj.full_name) + r'#(\d+)',
        ]
        
        issue_numbers = set()
        for pattern in patterns:
            matches = re.findall(pattern, text_content, re.IGNORECASE)
            for match in matches:
                try:
                    issue_numbers.add(int(match))
                except ValueError:
                    continue
        
        return list(issue_numbers)
    
    def _get_linked_issues_info(self, repo_obj, issue_numbers: List[int]) -> List[Dict]:
        """
        获取Issue的详细信息
        
        Args:
            repo_obj: PyGithub的Repository对象
            issue_numbers: Issue编号列表
            
        Returns:
            List[Dict]: Issue详细信息列表
        """
        issues_info = []
        for issue_number in issue_numbers:
            try:
                issue = repo_obj.get_issue(issue_number)
                issue_info = {
                    "number": issue.number,
                    "title": issue.title,
                    "state": issue.state.upper(),
                    "url": issue.html_url
                }
                issues_info.append(issue_info)
            except Exception as e:
                print(f"无法获取Issue #{issue_number}的信息: {e}")
                continue
        
        return issues_info
    
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
            
            # 简化的API使用信息
            simple_api_usage = {
                "queryCost": 1,
                "rateLimit": self.get_rate_limit_info()
            }
            
            print(f"PR数据获取完成")
            
            # # 将配额信息添加到结果中
            # result = {
            #     "prData": pr_data,
            #     "apiUsage": simple_api_usage
            # }

            return pr_data
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