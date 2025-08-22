import yaml
import requests
import json
from datetime import datetime
from pathlib import Path
import uuid

"""
这个脚本用于获取PR的信息，import 它，根据需要调用不同的函数。
"""

def fetch_pr_info(owner, repo, pr_number):
    # Read PAT from PAT.token
    pat_path = Path("PAT.token")
    if not pat_path.exists():
        raise FileNotFoundError("PAT.token file not found")
    with pat_path.open() as f:
        pat = f.read().strip()

    # Read config from config.yaml (though not used in this case, included for consistency)
    config_path = Path("config.yaml")
    if not config_path.exists():
        raise FileNotFoundError("config.yaml file not found")
    with config_path.open() as f:
        config = yaml.safe_load(f)

    # GitHub GraphQL query
    query = """
    query ($owner: String!, $repo: String!, $number: Int!) {
      repository(owner: $owner, name: $repo) {
        pullRequest(number: $number) {
          title
          body
          url
          state
          createdAt
          updatedAt
          baseRefOid
          headRefOid
          author {
            login
          }
        }
      }
    }
    """
    
    variables = {
        "owner": owner,
        "repo": repo,
        "number": pr_number
    }

    headers = {
        "Authorization": f"Bearer {pat}",
        "Content-Type": "application/json"
    }

    response = requests.post(
        "https://api.github.com/graphql",
        json={"query": query, "variables": variables},
        headers=headers
    )

    if response.status_code != 200:
        raise Exception(f"GitHub API request failed with status {response.status_code}: {response.text}")

    data = response.json()
    if "errors" in data:
        raise Exception(f"GraphQL query failed: {data['errors']}")

    pr_data = data.get("data", {}).get("repository", {}).get("pullRequest", {})
    if not pr_data:
        raise Exception("No pull request data found")

    # Save output to file
    output_path = Path(f"pr_{pr_number}_info.json")
    with output_path.open("w") as f:
        json.dump(pr_data, f, indent=2)

    return pr_data

def fetch_reviews(owner, repo, pr_number):
    # Read configuration from config.yaml
    with open('config.yaml', 'r') as file:
        config = yaml.safe_load(file)
        limits = config['limits']

    # Read PAT from PAT.token
    with open('PAT.token', 'r') as file:
        pat = file.read().strip()

    # GraphQL query with pagination
    query = """
    query($owner: String!, $repo: String!, $prNumber: Int!, $after: String) {
      repository(owner: $owner, name: $repo) {
        pullRequest(number: $prNumber) {
          reviews(first: %d, after: $after) {
            nodes {
              id
              body
              state
              submittedAt
              author {
                login
              }
            }
            pageInfo {
              hasNextPage
              endCursor
            }
          }
        }
      }
    }
    """ % limits['reviews']

    # GitHub API endpoint
    url = "https://api.github.com/graphql"

    # Headers for authentication
    headers = {
        "Authorization": f"Bearer {pat}",
        "Content-Type": "application/json"
    }

    # Initialize variables
    all_reviews = []
    after_cursor = None

    while True:
        # Variables for the query
        variables = {
            "owner": owner,
            "repo": repo,
            "prNumber": pr_number,
            "after": after_cursor
        }

        # Make the GraphQL request
        response = requests.post(
            url,
            json={"query": query, "variables": variables},
            headers=headers
        )

        # Check for successful response
        if response.status_code == 200:
            data = response.json()
            if 'errors' in data:
                print("Errors in GraphQL query:", data['errors'])
                break
            else:
                reviews_data = data['data']['repository']['pullRequest']['reviews']
                all_reviews.extend(reviews_data['nodes'])

                # Check if there are more pages
                page_info = reviews_data['pageInfo']
                if not page_info['hasNextPage']:
                    break
                after_cursor = page_info['endCursor']
        else:
            raise ValueError(f"Request failed with status code {response.status_code}: {response.text}")

    return all_reviews

def get_pr_comments(owner, repo, pr_number):
    # Read PAT from PAT.token
    with open('PAT.token', 'r') as f:
        token = f.read().strip()

    # Read config from config.yaml
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    comments_per_page = config['limits']['comments']

    # GitHub GraphQL endpoint
    url = 'https://api.github.com/graphql'
    headers = {
        'Authorization': f'bearer {token}',
        'Content-Type': 'application/json'
    }

    # Function to fetch comments with pagination
    def fetch_comments(cursor=None):
        query = '''
        query {
          repository(owner: "%s", name: "%s") {
            pullRequest(number: %d) {
              comments(first: %d%s) {
                edges {
                  node {
                    id
                    author {
                      login
                    }
                    body
                    createdAt
                    updatedAt
                    url
                  }
                }
                pageInfo {
                  hasNextPage
                  endCursor
                }
              }
            }
          }
        }
        ''' % (owner, repo, pr_number, comments_per_page, f', after: "{cursor}"' if cursor else '')

        response = requests.post(url, headers=headers, json={'query': query})
        if response.status_code != 200:
            raise Exception(f"API request failed with status {response.status_code}: {response.text}")

        data = response.json()
        if 'errors' in data:
            raise Exception(f"GraphQL errors: {data['errors']}")

        comments_data = data['data']['repository']['pullRequest']['comments']
        comments = [edge['node'] for edge in comments_data['edges']]
        page_info = comments_data['pageInfo']
        return comments, page_info['hasNextPage'], page_info['endCursor']

    # Collect all comments
    all_comments = []
    has_next_page = True
    cursor = None
    while has_next_page:
        comments, has_next_page, cursor = fetch_comments(cursor)
        all_comments.extend(comments)

    return all_comments

def get_pr_commits(owner, repo, pr_number):
    with open('PAT.token', 'r') as f:
        pat = f.read().strip()
    
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    commits_limit = config['limits']['commits']
    
    endpoint = "https://api.github.com/graphql"
    headers = {
        "Authorization": f"bearer {pat}",
        "Content-Type": "application/json"
    }
    
    all_commits = []
    cursor = None
    has_next_page = True
    
    while has_next_page:
        query = """
        query {
          repository(owner: "%s", name: "%s") {
            pullRequest(number: %d) {
              commits(first: %d%s) {
                edges {
                  node {
                    commit {
                      oid
                      message
                      committedDate
                      author {
                        user{
                          login
                        }
                        name
                        email
                      }
                    }
                  }
                }
                pageInfo {
                  hasNextPage
                  endCursor
                }
              }
            }
          }
        }
        """ % (owner, repo, pr_number, commits_limit, f', after: "{cursor}"' if cursor else "")
        
        response = requests.post(endpoint, headers=headers, json={"query": query})
        if response.status_code != 200:
            raise Exception(f"GraphQL query failed: {response.status_code} - {response.text}")
        
        data = response.json()
        if 'errors' in data:
            raise Exception(f"GraphQL errors: {data['errors']}")
        
        pr_commits = data['data']['repository']['pullRequest']['commits']
        all_commits.extend([edge['node']['commit'] for edge in pr_commits['edges']])
        
        page_info = pr_commits['pageInfo']
        has_next_page = page_info['hasNextPage']
        cursor = page_info['endCursor']
    
    return all_commits

def get_file_content(owner: str, repo: str, commit_sha: str, file_path: str) -> str:
    """
    获取 GitHub 仓库中指定 commit 和路径的文件内容。
    
    Args:
        owner (str): 仓库所有者用户名
        repo (str): 仓库名称
        commit_sha (str): Commit 的 SHA 值
        file_path (str): 文件路径（相对于仓库根目录）
    
    Returns:
        str: 文件内容
    
    Raises:
        Exception: 包含 JSON 格式错误信息的异常
    """
    # GitHub GraphQL API 端点
    url = "https://api.github.com/graphql"

    # 读取 GitHub 个人访问令牌
    try:
        with open("PAT.token", "r") as f:
            token = f.read().strip()
    except FileNotFoundError:
        error_info = {
            "error": "Token file not found",
            "details": "Could not find PAT.token file in the current directory"
        }
        raise Exception(json.dumps(error_info))

    # 设置请求头
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # GraphQL 查询
    query = """
    query GetFileContent($owner: String!, $repo: String!, $expression: String!) {
      repository(owner: $owner, name: $repo) {
        object(expression: $expression) {
          ... on Blob {
            text
          }
        }
      }
    }
    """

    # 查询变量
    variables = {
        "owner": owner,
        "repo": repo,
        "expression": f"{commit_sha}:{file_path}"
    }

    # 构造请求体
    payload = {
        "query": query,
        "variables": variables
    }

    # 发送请求
    response = requests.post(url, headers=headers, json=payload)

    # 解析响应
    if response.status_code == 200:
        data = response.json()
        if "errors" in data:
            error_info = {
                "error": "GraphQL query failed",
                "details": data["errors"]
            }
            raise Exception(json.dumps(error_info))
        elif data["data"]["repository"]["object"] is None:
            error_info = {
                "error": "File or commit not found",
                "details": f"No content found for commit {commit_sha} and path {file_path}"
            }
            raise Exception(json.dumps(error_info))
        else:
            return data["data"]["repository"]["object"]["text"]
    else:
        error_info = {
            "error": "HTTP request failed",
            "status_code": response.status_code,
            "details": response.json()
        }
        raise Exception(json.dumps(error_info))

def fetch_all_review_threads(owner, repo, pr_number):
    # Read configuration from config.yaml
    with open('config.yaml', 'r') as file:
        config = yaml.safe_load(file)
        limits = config['limits']

    # Read PAT from PAT.token
    with open('PAT.token', 'r') as file:
        pat = file.read().strip()

    # GraphQL query with pagination support
    query = """
    query($owner: String!, $repo: String!, $prNumber: Int!, $reviewLimit: Int!, $commentLimit: Int!, $after: String) {
      repository(owner: $owner, name: $repo) {
        pullRequest(number: $prNumber) {
          reviewThreads(first: $reviewLimit, after: $after) {
            nodes {
              id
              isResolved
              isOutdated
              path
              line
              startLine
              originalLine
              originalStartLine
              comments(first: $commentLimit) {
                nodes {
                  id
                  body
                  createdAt
                  path
                  diffHunk
                  author {
                    login
                  }
                }
              }
            }
            pageInfo {
              hasNextPage
              endCursor
            }
          }
        }
      }
    }
    """

    # GitHub API endpoint
    url = "https://api.github.com/graphql"

    # Headers for authentication
    headers = {
        "Authorization": f"Bearer {pat}",
        "Content-Type": "application/json"
    }

    # Initialize variables
    all_review_threads = []
    after_cursor = None

    while True:
        # Variables for the query
        variables = {
            "owner": owner,
            "repo": repo,
            "prNumber": pr_number,
            "reviewLimit": limits['reviews'],
            "commentLimit": limits['review_comments'],
            "after": after_cursor
        }

        # Make the GraphQL request
        response = requests.post(
            url,
            json={"query": query, "variables": variables},
            headers=headers
        )

        # Check for successful response
        if response.status_code == 200:
            data = response.json()
            if 'errors' in data:
                print("Errors in GraphQL query:", data['errors'])
                break
            else:
                # Extract reviewThreads nodes and pageInfo
                review_threads_data = data['data']['repository']['pullRequest']['reviewThreads']
                review_threads = review_threads_data['nodes']
                all_review_threads.extend(review_threads)

                # Check if there are more pages
                page_info = review_threads_data['pageInfo']
                if not page_info['hasNextPage']:
                    break
                after_cursor = page_info['endCursor']
        else:
            raise ValueError(f"Request failed with status code {response.status_code}: {response.text}")

    return all_review_threads


if __name__ == "__main__":
    output_dict = {}

    # content = get_file_content("RylynnWang", "TestGraphQL", "90a5095763c5c5c7aee2f51bf03c1d77a04096d5", "train_bpe_tokenizer.py")
    # output_dict.update({"fileContent":content})

    # owner = 'RylynnWang'
    # repo = 'TestGraphQL'
    # pr_number = 1

    owner = "JabRef" 
    repo = "JabRef"
    pr_number = 10592

    pr_info = fetch_pr_info(owner, repo, pr_number)
    output_dict.update({"prInfo":pr_info})

    commits_data = get_pr_commits(owner, repo, pr_number)
    output_dict.update({"commits":commits_data})

    review_threads = fetch_all_review_threads(owner, repo, pr_number)
    output_dict.update({"reviewThreads":review_threads})

    comments = get_pr_comments(owner, repo, pr_number)
    output_dict.update({"comments":comments})

    reviews = fetch_reviews(owner, repo, pr_number)
    output_dict.update({"reviews":reviews})

    print(json.dumps(output_dict, indent=2, ensure_ascii=False))
