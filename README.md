# GitHub Pull Request Tools

## 如何实现

GitHub 提供了多种API接口来获取 PR 的详细信息：
1. **GraphQL API**：功能强大但复杂，需要手动构建查询
2. **PyGithub 库**：Python封装的GitHub REST API，更简洁易用

本项目同时提供两种实现：
- `get_pr_comments.py`：使用 GraphQL API
- `get_pr_comments_py_github.py`：使用 PyGithub 库（推荐）

想要获取 GitHub 页面的内容，把链接复制下来给各个大模型的网页工具（我用的 grok ）就能帮你写 GraphQL 脚本。
如果这些脚本没法满足你的要求，你可以自己复制链接给大模型就可以。

以下是这 4 个脚本的介绍。

这是一个GitHub Pull Request工具集，包含四个主要功能：
1. **获取PR详细内容** - 获取指定PR的讨论内容、评论、代码审查等详细信息
2. **获取PR ID列表** - 获取仓库中所有或特定状态的Pull Request ID列表
3. **批量获取PR详细信息** - 整合前两个功能，批量获取所有符合条件的PR的详细信息
4. **GFM内容处理** - 将GitHub Flavored Markdown内容转换为纯文本格式

提供两种API实现方式：
- **GraphQL版本**：使用GitHub GraphQL API（复杂但功能全面）
- **PyGithub版本**：使用PyGithub库（简洁易维护，推荐使用）

## 功能特性

### PR详细内容获取
#### GraphQL版本 (get_pr_comments.py)
- 使用GitHub GraphQL API，功能全面
- 获取PR的基本信息（标题、描述、状态等）
- 获取所有普通评论和回复
- 获取代码审查评论（包括行内评论）
- 获取提交记录
- 获取关联的问题
- **可选获取文件完整代码内容**：支持获取PR中所有变更文件的修改前后完整内容
- 支持输出到控制台或保存到文件

#### PyGithub版本 (get_pr_comments_py_github.py) - **推荐**
- 使用PyGithub库，代码更简洁易维护
- 功能与GraphQL版本相同，输出格式完全兼容
- 更好的错误处理和异常管理
- 相同的配置文件和命令行参数
- 支持所有GraphQL版本的功能特性

### PR列表获取 (get_all_pr_brief.py)
- 获取仓库的所有Pull Request ID或详细信息
- 支持按状态过滤（OPEN、CLOSED、MERGED）
- 支持控制台输出或保存到文件
- 可选择获取简洁的ID列表或详细的PR信息
- 详细信息包括：标题、状态、时间、作者、代码变更统计等

### 批量PR详细信息获取 (get_all_pr_comments.py)
- 整合前两个工具的功能，一次性获取所有符合条件的PR详细信息
- 先获取PR ID列表，再循环获取每个PR的详细信息
- 支持按状态过滤（OPEN、CLOSED、MERGED）
- **可选批量获取代码内容**：支持为所有PR获取文件的完整代码内容
- 显示处理进度和统计信息
- 错误处理：单个PR失败不影响整体流程
- 支持逐行写入模式防止内存溢出
- 自动保存到JSON文件

### GFM内容处理 (process_gfm_content.py)
- 读取JSON文件中的PR数据（支持JSON Lines格式）
- 将GitHub Flavored Markdown (GFM) 格式的body字段转换为纯文本
- 清理所有格式字符、超链接、HTML标签等
- 保留代码块内容，但移除格式标记
- 处理图片标签，保留alt文本或显示占位符
- 保持合理的段落结构和列表格式
- 支持批量处理多个PR记录
- 提供详细的处理统计信息
- 错误处理：单个记录处理失败不影响整体流程

**GFM处理特性：**
- **链接处理**：`[text](url)` → 只保留 `text`
- **图片处理**：`![alt](url)` → 转换为 `[图片: alt]`
- **代码块**：`` `code` `` → 保留 `code` 内容
- **HTML标签**：`<tag>content</tag>` → 只保留 `content`
- **列表**：`<li>item</li>` → 转换为 `• item`
- **表格**：转换为简单的文本格式
- **格式清理**：移除多余的空白字符和换行

## 安装依赖

本项目使用 uv 作为 Python 包管理器和虚拟环境工具。

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
     files: 100
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
   - `files`: 获取PR变更文件的最大数量（默认100个）
   
   **调整建议：**
   - 对于大型项目或活跃的PR，可以适当增加这些限制值
   - 对于简单的PR或网络较慢的环境，可以减少这些值以提高响应速度
   - 如果遇到GitHub API速率限制，建议降低这些值
   
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

### 1. 获取PR详细内容

#### 1.1 GraphQL版本 (get_pr_comments.py)

##### 命令行格式
```bash
python get_pr_comments.py <owner> <repo> <pr_number> [--output console|file] [--filename output.json]
```

##### 参数说明
- `owner`: 仓库所有者
- `repo`: 仓库名称
- `pr_number`: Pull Request编号
- `--output`: 输出文件名，不指定则输出到控制台
- `--config`: 配置文件路径，默认为 `config.yaml`
- `--token`: GitHub Personal Access Token文件路径，默认为 `PAT.token`
- `--fetch-code-snippet`: 获取文件的完整代码内容（修改前后对比），默认不获取

##### 使用示例
```bash
# 输出到控制台
python get_pr_comments.py JabRef jabref 13553

# 保存到文件
python get_pr_comments.py JabRef jabref 13553 --output pr_data.json

# 获取文件的完整代码内容（修改前后对比）
python get_pr_comments.py JabRef jabref 13553 --fetch-code-snippet --output pr_data.json

# 使用自定义配置文件和token文件
python get_pr_comments.py JabRef jabref 13553 --output pr_data.json --config my_config.yaml --token my_token.token
```

#### 1.2 PyGithub版本 (get_pr_comments_py_github.py) - **推荐**

##### 命令行格式
```bash
python get_pr_comments_py_github.py <owner> <repo> <pr_number> [--output console|file] [--filename output.json]
```

##### 参数说明
参数与GraphQL版本完全相同，输出格式也完全兼容。

##### 使用示例
```bash
# 输出到控制台
python get_pr_comments_py_github.py JabRef jabref 13553

# 保存到文件
python get_pr_comments_py_github.py JabRef jabref 13553 --output pr_data.json

# 获取文件的完整代码内容（修改前后对比）
python get_pr_comments_py_github.py JabRef jabref 13553 --fetch-code-snippet --output pr_data.json

# 使用自定义配置文件和token文件
python get_pr_comments_py_github.py JabRef jabref 13553 --output pr_data.json --config my_config.yaml --token my_token.token
```

##### PyGithub版本的优势
- 代码更简洁，维护性更好
- 更好的错误处理和异常管理
- 不需要手动构建复杂的GraphQL查询
- 使用标准的GitHub REST API，更稳定
- 输出格式与GraphQL版本100%兼容

#### --fetch-code-snippet 参数说明

`--fetch-code-snippet` 参数是一个可选功能，用于获取PR中所有变更文件的完整代码内容（修改前后对比）。

**功能特点：**
- 获取PR中每个变更文件的修改前完整内容（base版本）
- 获取PR中每个变更文件的修改后完整内容（head版本）

**输出格式：**
在每个文件节点中会添加 `fullContent` 对象，包含：
```json
{
  "path": "src/example.java",
  "additions": 10,
  "deletions": 5,
  "changeType": "MODIFIED",
  "fullContent": {
    "before": {
      "text": "修改前的完整文件内容",
      "byteSize": 1024,
      "isBinary": false
    },
    "after": {
      "text": "修改后的完整文件内容",
      "byteSize": 1124,
      "isBinary": false
    }
  }
}
```

**使用建议：**
- 默认不启用此功能，以提高执行速度和减少API调用
- 对于大型PR或包含大文件的PR，会显著增加执行时间和输出文件大小

**性能影响：**
- 会为每个变更文件额外发起API请求
- 增加网络传输时间和API配额消耗
- 输出文件大小会显著增加
- 对于包含大量文件变更的PR，建议谨慎使用

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

#### 详细信息字段说明

当使用 `--detailed` 参数时，每个PR包含以下信息：
- `number`: PR编号
- `title`: PR标题
- `state`: PR状态 (OPEN/CLOSED/MERGED)
- `createdAt`: 创建时间
- `updatedAt`: 更新时间
- `closedAt`: 关闭时间
- `mergedAt`: 合并时间
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
- `--fetch-code-snippet`: 获取文件的完整代码内容（修改前后对比），默认不获取

#### 使用示例

```bash
# 获取所有状态的PR详细信息
python get_all_pr_comments.py JabRef jabref

# 只获取已合并和已关闭的PR
python get_all_pr_comments.py JabRef jabref --states MERGED CLOSED

# 只获取开放状态的PR并指定输出文件
python get_all_pr_comments.py JabRef jabref --states OPEN --output jabref_open_prs.json

# 获取PR详细信息并包含文件的完整代码内容
python get_all_pr_comments.py JabRef jabref --states MERGED --fetch-code-snippet --output jabref_merged_prs.json

# 使用自定义配置文件和token文件
python get_all_pr_comments.py JabRef jabref --config my_config.yaml --token my_token.token --output jabref_prs.json

# 使用逐行写入模式防止内存溢出（适用于大量PR的情况）
python get_all_pr_comments.py JabRef jabref --output jabref_all_prs.jsonl --store-by-line

# 结合状态过滤、代码获取和逐行写入
python get_all_pr_comments.py JabRef jabref --states OPEN --fetch-code-snippet --output jabref_open_prs.jsonl --store-by-line
```

### 4. GFM内容处理 (process_gfm_content.py)

#### 命令行格式
```bash
python process_gfm_content.py <input_file> <output_file> [--verbose]
```

#### 参数说明
- `input_file`: 输入JSON文件路径（必需）
- `output_file`: 输出JSON文件路径（必需）
- `--verbose, -v`: 显示详细处理信息（可选）

#### 使用示例

```bash
# 处理JSON Lines格式的文件
python process_gfm_content.py "output/jabref_merged_prs copy.json" "output/processed_prs.json"

# 处理标准JSON格式的文件
python process_gfm_content.py "input.json" "output.json"

# 显示详细处理信息
python process_gfm_content.py "input.json" "output.json" --verbose
```

#### 输入格式支持

脚本支持两种输入格式：

**JSON Lines格式（推荐）：**
每行一个JSON对象，这是批量获取脚本的默认输出格式：
```
{"prData": {...}, "apiUsage": {...}}
{"prData": {...}, "apiUsage": {...}}
{"prData": {...}, "apiUsage": {...}}
```

**标准JSON格式：**
包含JSON对象数组的文件：
```json
[
  {"prData": {...}, "apiUsage": {...}},
  {"prData": {...}, "apiUsage": {...}},
  {"prData": {...}, "apiUsage": {...}}
]
```

#### 输出格式

输出文件采用JSON Lines格式，每行一个处理后的JSON对象，保持原有的数据结构，但body字段被转换为纯文本：

```json
{
  "prData": {
    "title": "PR标题",
    "body": "转换后的纯文本内容，没有格式字符和超链接",
    "url": "PR链接",
    "state": "OPEN",
    "comments": {
      "nodes": [
        {
          "body": "转换后的评论纯文本内容",
          "author": {"login": "用户名"}
        }
      ]
    }
  },
  "apiUsage": {...}
}
```

#### 处理特性

**GFM元素转换规则：**
- **Markdown链接**：`[text](url)` → `text`
- **Markdown图片**：`![alt](url)` → `[图片: alt]`
- **行内代码**：`` `code` `` → `code`
- **代码块**：```code``` → `[代码块] code [/代码块]`
- **粗体文本**：`**text**` → `text`
- **斜体文本**：`*text*` → `text`
- **HTML标签**：`<tag>content</tag>` → `content`
- **列表项**：`<li>item</li>` → `• item`
- **表格**：转换为简单的文本格式
- **标题**：`# title` → `title`

**文本清理：**
- 移除多余的空白字符和换行
- 保持合理的段落结构
- 清理行首行尾空白
- 合并连续的空白行

#### 注意事项

1. 脚本会处理以下字段中的GFM内容：
   - `prData.body`：PR描述内容
   - `comments.nodes[].body`：评论内容
   - `reviewThreads.nodes[].comments.nodes[].body`：审查评论内容

2. 如果GFM转换失败，会使用简单的文本清理作为备用方案

3. 脚本提供详细的处理统计信息，包括：
   - 总记录数
   - 成功处理数
   - 跳过记录数
   - 错误数量

4. 支持错误处理：单个记录处理失败不会影响整体流程

#### 输出格式

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

- `queryCost`: 本次查询消耗的API点数
- `rateLimit.limit`: 每小时的API配额总限制
- `rateLimit.remaining`: 当前剩余的API配额
- `rateLimit.used`: 已使用的API配额
- `rateLimit.resetAt`: API配额重置时间（UTC时间）

脚本会在控制台显示API使用情况，帮助用户监控配额消耗。

## 项目结构

```
├── get_pr_comments.py      # PR详细内容获取脚本
├── get_all_pr_brief.py     # PR ID列表获取脚本
├── get_all_pr_comments.py  # 批量获取PR详细信息脚本
├── process_gfm_content.py  # GFM内容处理脚本
├── requirements.txt         # Python依赖包
├── config.yaml             # 配置文件
├── PAT.token              # GitHub Personal Access Token
└── README.md              # 项目说明文档
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
