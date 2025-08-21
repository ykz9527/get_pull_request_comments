import requests
import json

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
    
if __name__ == "__main__":
    # 示例调用
    try:
        content = get_file_content("RylynnWang", "TestGraphQL", "bce87a1a7db7a1a200ab4e6b71debff3bec025b7", "train_bpe_tokenizer.py")
        print(content)
    except Exception as e:
        print(f"Error: {e}")