# GitHub Pull Request Tools

这是一个GitHub Pull Request工具集，包含三个主要功能：
1. **获取PR详细内容** - 获取指定PR的讨论内容、评论、代码审查等详细信息
2. **获取PR ID列表** - 获取仓库中所有或特定状态的Pull Request ID列表
3. **批量获取PR详细信息** - 整合前两个功能，批量获取所有符合条件的PR的详细信息

所有工具都使用GitHub的GraphQL API，支持灵活的配置和多种输出选项。

## 功能特性

### PR详细内容获取 (get_pr_comments.py)
- 获取PR的基本信息（标题、描述、状态等）
- 获取所有普通评论和回复
- 获取代码审查评论（包括行内评论）
- 获取提交记录
- 获取关联的问题
- 支持命令行参数
- 支持输出到控制台或保存到文件
- JSON格式输出

### PR列表获取 (get_all_pr_brief.py)
- 获取仓库的所有Pull Request ID或详细信息
- 支持按状态过滤（OPEN、CLOSED、MERGED）
- 支持分页查询，获取完整历史记录
- 支持控制台输出或保存到文件
- 支持自定义输出文件名
- 可选择获取简洁的ID列表或详细的PR信息
- 详细信息包括：标题、状态、时间、作者、代码变更统计等

### 批量PR详细信息获取 (get_all_pr_details.py)
- 整合前两个工具的功能，一次性获取所有符合条件的PR详细信息
- 先获取PR ID列表，再循环获取每个PR的详细信息
- 在每个PR详细信息中自动添加prID字段
- 支持按状态过滤（OPEN、CLOSED、MERGED）
- 显示处理进度和统计信息
- 错误处理：单个PR失败不影响整体流程
- 自动保存到JSON文件

## 安装依赖

```bash
uv venv --python 3.12 .venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

## 配置

1. 创建GitHub Personal Access Token：
   - 访问 https://github.com/settings/tokens
   - 点击 "Generate new token"
   - 选择适当的权限（至少需要 `public_repo` 权限）
   - 复制生成的token

2. 创建PAT.token文件：
   ```bash
   echo "your_github_token_here" > PAT.token
   ```

3. 配置config.yaml文件：
   ```yaml
   limits:
     comments: 100
     reviews: 100
     review_comments: 100
     commits: 100
     closing_issues: 100
     reactions: 100
     pull_requests_per_page: 100
   ```

   **limits配置说明：**
   
   这些限制参数控制从GitHub API获取数据的数量，主要用于：
   - **性能优化**：避免请求过多数据导致响应缓慢
   - **API配额管理**：减少GitHub API的使用量，避免触发速率限制
   - **内存控制**：防止大型PR的数据量过大导致内存问题
   
   各参数含义：
   - `comments`: 获取PR普通评论的最大数量（默认100条）
   - `reviews`: 获取代码审查的最大数量（默认100个）
   - `review_comments`: 每个代码审查中行内评论的最大数量（默认100条）
   - `commits`: 获取PR提交记录的最大数量（默认100个）
   - `closing_issues`: 获取PR关联问题的最大数量（默认100个）
   - `reactions`: 每条评论的反应表情最大数量（默认100个）
   - `pull_requests_per_page`: 获取PR列表时每页的数量（默认100个）
   
   **调整建议：**
   - 对于大型项目或活跃的PR，可以适当增加这些限制值
   - 对于简单的PR或网络较慢的环境，可以减少这些值以提高响应速度
   - 如果遇到GitHub API速率限制，建议降低这些值
   
   **设置无限制：**
   
   如果需要获取所有数据而不受限制，可以将相应的值设置为较大的数字（如9999）：
   ```yaml
   limits:
     comments: 9999
     reviews: 9999
     review_comments: 9999
      commits: 9999
      closing_issues: 9999
      reactions: 9999
      pull_requests_per_page: 100
   ```
   
   **⚠️ 注意事项：**
   - 设置过大的限制值可能导致请求超时或内存不足
   - 会消耗更多的GitHub API配额，可能触发速率限制
   - 对于评论数量极多的PR（如几千条评论），建议谨慎使用
   - 建议先用默认值测试，确认正常后再根据需要调整
   
   **GitHub API 限额详情：** <mcreference link="https://docs.github.com/en/graphql/overview/rate-limits-and-node-limits-for-the-graphql-api" index="1">1</mcreference>
   - **主要速率限制**：认证用户每小时5000点 <mcreference link="https://docs.github.com/en/graphql/overview/rate-limits-and-node-limits-for-the-graphql-api" index="1">1</mcreference>
   - **次级速率限制**：GraphQL API端点每分钟最多2000点 <mcreference link="https://docs.github.com/en/graphql/overview/rate-limits-and-node-limits-for-the-graphql-api" index="4">4</mcreference>
   - **并发请求限制**：同时最多100个并发请求（REST和GraphQL共享） <mcreference link="https://docs.github.com/en/graphql/overview/rate-limits-and-node-limits-for-the-graphql-api" index="1">1</mcreference>
   - **点数计算**：每个GraphQL查询至少消耗1点，复杂查询会消耗更多点数 <mcreference link="https://github.blog/developer-skills/github/exploring-github-cli-how-to-interact-with-githubs-graphql-api-endpoint/" index="2">2</mcreference>
   - **超时惩罚**：如果请求超时，下一小时会额外扣除点数 <mcreference link="https://docs.github.com/en/graphql/overview/rate-limits-and-node-limits-for-the-graphql-api" index="1">1</mcreference>

## 使用方法

### 1. 获取PR详细内容 (get_pr_comments.py)

#### 命令行格式
```bash
python get_pr_comments.py <owner> <repo> <pr_number> [--output console|file] [--filename output.json]
```

#### 参数说明
- `owner`: 仓库所有者
- `repo`: 仓库名称
- `pr_number`: Pull Request编号
- `--output`: 输出文件名，不指定则输出到控制台
- `--config`: 配置文件路径，默认为 `config.yaml`
- `--token`: GitHub Personal Access Token文件路径，默认为 `PAT.token`

#### 使用示例
```bash
# 输出到控制台
python get_pr_comments.py JabRef jabref 13553

# 保存到文件
python get_pr_comments.py JabRef jabref 13553 --output pr_data.json

# 使用自定义配置文件和token文件
python get_pr_comments.py JabRef jabref 13553 --output pr_data.json --config my_config.yaml --token my_token.token
```

### 2. 获取PR ID列表或详细信息 (get_all_pr_brief.py)

#### 命令行格式
```bash
python get_all_pr_brief.py <owner> <repo> [--states STATE1 STATE2 ...] [--output FILE] [--detailed]
```

#### 参数说明
- `owner`: 仓库所有者
- `repo`: 仓库名称
- `--states`: 过滤PR状态，可选：OPEN CLOSED MERGED（可多选）
- `--output`: 输出文件名，不指定则输出到控制台
- `--detailed`: 获取详细信息而不仅仅是ID
- `--ids-only`: 仅获取ID列表（默认行为）

#### 使用示例

**获取PR ID列表：**
```bash
# 控制台显示所有PR ID
python get_all_pr_brief.py JabRef jabref

# 获取开放状态的PR ID并保存到文件
python get_all_pr_brief.py JabRef jabref --states OPEN --output pr_ids.json

# 获取已合并的PR ID并保存到自定义文件
python get_all_pr_brief.py JabRef jabref --states MERGED --output merged_pr_ids.json
```

**获取PR详细信息：**
```bash
# 控制台显示所有PR详细信息
python get_all_pr_brief.py JabRef jabref --detailed

# 获取开放状态的PR详细信息并保存到文件
python get_all_pr_brief.py JabRef jabref --detailed --states OPEN --output detailed_open_prs.json

# 获取已合并的PR详细信息并保存到自定义文件
python get_all_pr_brief.py JabRef jabref --detailed --states MERGED --output detailed_merged_prs.json
```

### 3. 批量获取PR详细信息 (get_all_pr_comments.py)

#### 命令行格式
```bash
python get_all_pr_comments.py <owner> <repo> [--states STATE1 STATE2 ...] [--output FILE] [--config CONFIG]
```

#### 参数说明
- `owner`: 仓库所有者（必需）
- `repo`: 仓库名称（必需）
- `--states`: PR状态过滤，可选值：OPEN, CLOSED, MERGED（可选多个）
- `--output`: 输出文件名（默认：all_pr_details.json）
- `--config`: 配置文件路径（默认：config.yaml）
- `--token`: GitHub Personal Access Token文件路径（默认：PAT.token）
- `--store-by-line`: 逐行写入JSON数据以防止内存溢出（仅在明确指定 --output 时可用）

#### 使用示例

```bash
# 获取所有状态的PR详细信息
python get_all_pr_comments.py JabRef jabref

# 只获取已合并和已关闭的PR
python get_all_pr_comments.py JabRef jabref --states MERGED CLOSED

# 只获取开放状态的PR并指定输出文件
python get_all_pr_comments.py JabRef jabref --states OPEN --output jabref_open_prs.json

# 使用自定义配置文件和token文件
python get_all_pr_comments.py JabRef jabref --config my_config.yaml --token my_token.token --output jabref_prs.json

# 使用逐行写入模式防止内存溢出（适用于大量PR的情况）
python get_all_pr_comments.py JabRef jabref --output jabref_all_prs.jsonl --store-by-line

# 结合状态过滤和逐行写入
python get_all_pr_comments.py JabRef jabref --states OPEN --output jabref_open_prs.jsonl --store-by-line
```

#### 输出格式

脚本支持两种输出格式：

**标准模式（默认）：**
生成一个JSON文件，包含一个数组，每个元素都是一个PR的详细信息字典。每个字典都包含：

- `prID`: PR的ID号（新增字段）
- `pullRequest`: PR的详细信息（来自GitHubPRCommentsFetcher）
  - `title`: PR标题
  - `body`: PR描述
  - `state`: PR状态
  - `comments`: 评论列表
  - `reviews`: 审查列表
  - 等等...

**逐行写入模式（--store-by-line）：**
生成一个JSONL文件（JSON Lines格式），每行包含一个完整的PR详细信息JSON对象。这种格式：
- 防止大量PR数据导致的内存溢出
- 支持流式处理，可以边获取边写入
- 每个PR处理完成后立即写入磁盘
- 适合处理大型仓库或历史悠久的项目

#### 注意事项

1. 确保 `config.json` 文件存在且包含有效的GitHub token
2. 对于大型仓库，获取所有PR详细信息可能需要较长时间
3. 脚本会显示进度信息，包括当前处理的PR编号
4. 如果某个PR获取失败，脚本会继续处理其他PR
5. 最终会显示统计信息，包括按状态分布的PR数量
6. **关于 --store-by-line 选项：**
   - 只能在明确指定 `--output` 参数时使用
   - 推荐用于处理大量PR（如超过1000个）的场景
   - 输出文件建议使用 `.jsonl` 扩展名以表明是JSON Lines格式
   - 该模式下无法生成标准的JSON数组格式，需要逐行解析

#### 详细信息字段说明

当使用 `--detailed` 参数时，每个PR包含以下信息：
- `number`: PR编号
- `title`: PR标题
- `state`: PR状态 (OPEN/CLOSED/MERGED)
- `created_at`: 创建时间
- `updated_at`: 更新时间
- `closed_at`: 关闭时间
- `merged_at`: 合并时间
- `author`: 作者用户名
- `mergeable`: 是否可合并
- `merged`: 是否已合并
- `isDraft`: 是否为草稿
- `additions`: 新增行数
- `deletions`: 删除行数
- `changedFiles`: 修改文件数
- `url`: PR链接
- `headRefName`: 源分支名
- `baseRefName`: 目标分支名

## 输出格式

所有输出均为JSON格式，包含PR的完整结构化数据和API使用情况：

```json
{
  "prData": {
    "title": "PR标题",
    "body": "PR描述",
    "url": "PR链接",
    "state": "OPEN",
    "createdAt": "2023-01-01T00:00:00Z",
    "author": {
      "login": "用户名"
    },
    "comments": {
      "nodes": [...]
    },
    "reviews": {
      "nodes": [...]
    },
    "commits": {
      "nodes": [...]
    }
  },
  "apiUsage": {
    "queryCost": 15,
    "rateLimit": {
      "limit": 5000,
      "remaining": 4985,
      "used": 15,
      "resetAt": "2023-12-01T12:00:00Z"
    }
  }
}
```

### API使用情况说明

- `query_cost`: 本次查询消耗的API点数
- `rate_limit.limit`: 每小时的API配额总限制
- `rate_limit.remaining`: 当前剩余的API配额
- `rate_limit.used`: 已使用的API配额
- `rate_limit.resetAt`: API配额重置时间（UTC时间）

脚本会在控制台显示API使用情况，帮助用户监控配额消耗。

## 项目结构

```
├── get_pr_comments.py   # PR详细内容获取脚本
├── get_all_pr_brief.py  # PR ID列表获取脚本
├── get_all_pr_comments.py # 批量获取PR详细信息脚本
├── config.yaml          # 配置文件
├── PAT.token           # GitHub Personal Access Token文件
├── requirements.txt     # 依赖包
└── README.md           # 说明文档
```

## API限制

- GitHub GraphQL API有速率限制
- 每小时最多5000个请求点数
- 复杂查询会消耗更多点数
- 可在config.yaml中调整数据获取的数量限制

## 故障排除

1. **配置文件不存在**：确保config.yaml文件存在且格式正确
2. **Token文件不存在**：确保PAT.token文件存在且包含有效的GitHub Personal Access Token
3. **Token权限不足**：确保token有访问目标仓库的权限
4. **API限制**：如果遇到速率限制，请等待一段时间后重试
5. **网络问题**：检查网络连接和GitHub API状态

## 许可证

本项目采用MIT许可证。