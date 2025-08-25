import os
import sys
from collections import defaultdict
from github import Github
from github.GithubException import UnknownObjectException

# --- 配置 ---
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

def print_header(title):
    """打印带分隔线的标题"""
    print("\n" + "="*80)
    print(f"--- {title} ---")
    print("="*80)

def extract_pr_details(repo_name, pr_number):
    """
    连接到GitHub API并抽取PR信息，清晰地展示审查、线索、评论之间的层级关系。
    """
    if not GITHUB_TOKEN:
        print("错误：请设置 'GITHUB_TOKEN' 环境变量。")
        sys.exit(1)

    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
    except UnknownObjectException:
        print(f"错误：无法找到仓库 '{repo_name}' 或 PR #{pr_number}。请检查输入是否正确。")
        sys.exit(1)
    except Exception as e:
        print(f"发生未知错误: {e}")
        sys.exit(1)

    # --- 打印PR基本信息、Commits、通用评论 (这部分无变化) ---
    print_header("PR 基本信息")
    print(f"标题: {pr.title}, 编号: #{pr.number}, 状态: {pr.state}, 作者: {pr.user.login}")
    print(f"链接: {pr.html_url}")
    
    print_header("Commits 列表")
    for commit in pr.get_commits():
        print(f"- {commit.sha[:7]} | {commit.commit.author.name} | {commit.commit.message.splitlines()[0]}")

    print_header("通用评论 (PR 主线讨论)")
    issue_comments = pr.get_issue_comments()
    if issue_comments.totalCount > 0:
        for comment in issue_comments:
            print("-" * 30)
            print(f"作者: {comment.user.login} | 时间: {comment.created_at}")
            print(f"内容:\n{comment.body}\n")
    else:
        print("(无通用评论)")

    # ======================================================================
    # (核心重构) 识别所有代码评论线索(Threads)，并将其与审查(Review)关联
    # ======================================================================
    print_header("代码审查与评论线索")

    # 步骤 A: 获取所有代码评论，并构建线索
    all_review_comments = list(pr.get_review_comments())
    
    # 字典1: 存放所有线索，key是顶层评论的id，value是该线索中所有评论的列表
    threads = defaultdict(list)
    # 字典2: 存放所有顶层评论对象，key是顶层评论的id
    top_level_comments = {}
    # 列表: 存放所有回复评论
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
        # in_reply_to_id 指向的是线索的顶层评论ID
        if reply.in_reply_to_id in threads:
            threads[reply.in_reply_to_id].append(reply)
            
    # 按时间排序每个线索内部的评论
    for thread_id in threads:
        threads[thread_id].sort(key=lambda c: c.created_at)

    # 步骤 B: 将构建好的线索按其所属的 Review ID 分组
    threads_by_review_id = defaultdict(list)
    for thread_id, comment_list in threads.items():
        top_level_comment = top_level_comments[thread_id]
        review_id = top_level_comment.pull_request_review_id
        threads_by_review_id[review_id].append(comment_list)

    # 步骤 C: 打印所有正式的审查(Review)及其关联的评论线索
    reviews = pr.get_reviews()
    if reviews.totalCount > 0:
        print("\n--- 审查总结 (Review Submissions) ---")
        for review in reviews:
            if review.state == 'COMMENTED' and not review.body:
                continue
            
            print("-" * 50)
            print(f"审查总结 | 作者: {review.user.login} | 时间: {review.submitted_at} | 状态: {review.state}")
            if review.body:
                print(f"总结内容:\n{review.body}")
            
            associated_threads = threads_by_review_id.get(review.id, [])
            if associated_threads:
                print("\n  └── 关联的代码评论线索:")
                for i, thread in enumerate(associated_threads, 1):
                    start_comment = thread[0]
                    print(f"\n    ▶ 线索 {i}: 在文件 {start_comment.path} (行号: {start_comment.line or 'N/A'})")
                    for comment in thread:
                        is_reply_str = "[回复]" if comment.in_reply_to_id else "[评论]"
                        print(f"      - {is_reply_str} 作者: {comment.user.login} | {comment.body.replace(chr(10), ' ')}")
            print("-" * 50)

    # 步骤 D: 打印所有独立的、不属于任何审查总结的评论线索
    standalone_threads = threads_by_review_id.get(None, [])
    if standalone_threads:
        print("\n--- 独立的评论线索 (Standalone Threads) ---")
        for i, thread in enumerate(standalone_threads, 1):
            start_comment = thread[0]
            print(f"\n  ▶ 线索 {i}: 在文件 {start_comment.path} (行号: {start_comment.line or 'N/A'})")
            for comment in thread:
                is_reply_str = "[回复]" if comment.in_reply_to_id else "[评论]"
                print(f"    - {is_reply_str} 作者: {comment.user.login} | {comment.body.replace(chr(10), ' ')}")
    
    if not reviews.totalCount and not standalone_threads:
        print("(无任何代码审查评论)")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("使用方法: python extract_pr.py <owner/repo> <pr_number>")
        print("例如: python extract_pr.py microsoft/vscode 157643")
        sys.exit(1)

    repo_arg = sys.argv[1]
    try:
        pr_num_arg = int(sys.argv[2])
    except ValueError:
        print("错误: PR 编号必须是一个整数。")
        sys.exit(1)
    
    extract_pr_details(repo_arg, pr_num_arg)