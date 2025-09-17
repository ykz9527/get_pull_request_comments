import json

def extract_opinion_by_dialog_with_code(dialog, code, comment, start_line, end_line):
    """
    从GitHub代码评审对话中提取设计知识的prompt生成器
    
    Args:
        dialog: 程序员对话内容（JSON格式字符串）
        code: 相关代码内容
        line: 结束行号
        start_line: 开始行号
    
    Returns:
        str: 用于大模型的完整promptcloudfdse.
    """

    line_info = f"line {start_line}"

    if start_line != end_line:
        line_info = f"lines {start_line} to {end_line}"

    concerned_lines = code.splitlines()[start_line-1:end_line]
    concerned_lines = "\n".join(concerned_lines)
    
    dialog = json.dumps(dialog, indent = 2,ensure_ascii=False)

    prompt = f"""你是一个软件工程专家，需要从 GitHub 上程序员的代码评审对话中提取有价值的设计知识和最佳实践。

## 重要约束
保证抽取的内容精简，含义明确

## 任务说明
仔细阅读程序员对话内容，仅提取对话中明确提到的设计建议和技术决策，重点关注：
- 开发者在对话中明确提出的问题、挑战或需要解决的技术难点
- 开发者在对话中明确提出的具体解决方案、技术选型或实现建议
- 开发者在对话中明确提出的支持其建议的理由、论据或技术依据
- 开发者在对话中明确或暗示的适用条件、前提假设或限制因素

## 输出格式
请按以下 JSON 格式输出提取的设计知识：
[
  {{
    "problem": "这个设计建议、技术决策、观点所关注的问题",
    "suggestion": "具体的设计建议和推荐做法",
    "reasons": ["支持该建议的理由或论据"],
    "context": ["建议的一些前提条件,随着时间会改变的因素"],
  }}
]

## 字段说明
"problem": "这个字段代表了触发讨论的核心问题或挑战，即'为什么需要讨论这个话题？'它描述了开发者试图解决的技术难点、性能问题、架构缺陷或用户体验问题等。例如：'在应用运行时获取和处理数据，会导致性能瓶颈和不稳定的网络依赖'。"
"suggestion": "这个字段是对'我们应该如何解决这个问题？'的具体回答。它必须是一个明确的、可操作的技术建议或解决方案，而不是模糊的方向性指导。可以包括具体的实现方法、架构选择、设计模式等。例如：'在项目构建时预先生成一个静态的、优化过的数据库文件，应用在运行时只负责加载这个本地文件'。"
"reasons": "这个字段解释了'为什么这个建议是合理的？'它提供了支持该建议的技术理由、性能优势、架构好处或最佳实践依据。这些论据必须在对话中明确提到，不能进行推测。例如：['与项目现有架构保持一致', '极大提升应用启动性能，避免UI冻结']。"
"contexts": "这个字段记录了建议成功实施所需的前提条件、适用范围或技术限制。这可以包括：1. 版本依赖关系（如'需要Java 8或以上版本'）；2. 环境要求（如'需要8GB以上内存'）；3. 业务约束（如'仅适用于用户量小于100万的场景'）。这个字段允许适度的合理推测，即使对话中没有明确提及。"
"type": "这个字段记录了建议的类型，包括：架构设计、代码风格、性能优化、安全漏洞、测试维护、错误处理、用户体验、环境配置。这个字段允许根据建议内容进行推测，即使开发者没有明确提到具体类型。"

## 提取原则
1. **严格来源规则**：所有核心内容（problem、suggestion、reasons）必须严格来自对话内容。对话是唯一有效的提取来源。

2. **辅助信息规则**：提供的代码片段（code, concerned_lines）和相关评论（comment）仅用于帮助理解：
   - 对话中提到的函数名和变量名
   - 正在讨论的代码逻辑
   - 讨论的技术背景
   这些内容不能用作提取建议的来源。

3. **禁止推断规则**：不要从对话内容之外进行推断：
   - 不要从代码内容推断可能的建议
   - 不要从相关评论中提取内容
   - 不要基于自己的专业知识添加建议
   - 不要组合不同来源的信息
   - 如果对话中没有明确提到理由，reasons必须为空数组

4. **精确匹配规则**：建议的表述必须忠实于对话中的原始表达，不要使用其他来源的信息改写或增强建议内容

5. **上下文提取规则**：对于contexts字段：
   - 关注可能随时间变化的条件（版本依赖、环境要求、业务约束）
   - 只包含那些变化会显著影响建议有效性的条件
   - 优先使用明确提到的版本号、系统要求或规模限制
   - 允许适度推测，但必须基于对话内容的合理延伸
   - 不要包含永久性的技术事实或通用最佳实践

6. **类型推断规则**：对于type字段：
   - 允许根据建议内容推测其类型
   - 即使开发者没有明确提到具体类型也可以进行分类
   - 必须基于建议的实际内容，而不是个人偏好
   - 如果一个建议符合多个类型，选择最主要的一个

## 补充说明
- problem 须明确描述讨论的问题或挑战
- suggestion 字段不能是空字符串，必须包含具体的技术建议
- reasons 数组可以是空数组，当且仅当对话中没有明确提到任何支持理由时
- context 数组可以是空数组，但建议尽量填充相关的前提条件
- 你可以在提取的建议和论据中添加自然语言描述的相关背景，比如代码的上下文，代码的功能，等等
- 你的输出应该是**中文**
- 你的输出应该是能够被程序直接解析成 JSON 格式的字符串，不要输出其他任何的标记、说明，不要将你输出的内容包含在 ```json ``` 块中

## 输出示例:
[
  {{
    "problem": "在应用运行时获取和处理数据，会导致性能瓶颈和不稳定的网络依赖。",
    "suggestion": "在应用运行时动态加载、更新和处理掠夺性期刊列表。",
    "reasons": ["可以确保用户总是使用最新的数据列表"],
    "contexts": ["用户的运行环境必须有稳定的互联网连接", "JabRef 应用必须被授予发起网络请求的权限"]
  }},
  {{
    "problem": "运行时处理数据的方式与项目现有成熟模式（如期刊缩写列表）不一致，且效率低下。",
    "suggestion": "在项目构建时（ON BUILD）预先生成一个静态的、优化过的数据库文件（.mv），应用在运行时（ON RUN）只负责加载这个本地文件。",
    "reasons": ["与项目现有架构保持一致", "极大提升应用启动性能，避免UI冻结", "对离线用户和打包者友好"],
    "contexts": ["用于生成列表的外部数据源（如Beall's list等网站）必须是可抓取的，且其页面结构在构建期间保持相对稳定"]
  }},
  {{
    "problem": "数据来源和状态管理分散，导致代码耦合和维护困难。",
    "suggestion": "(宏观思想) 确立 `PredatoryJournalRepository` 作为掠夺性期刊数据的“单一数据源 (Single Source of Truth)”。所有业务逻辑代码都应通过它来获取数据。",
    "reasons": ["实现关注点分离，提高代码的可测试性和可维护性", "封装了数据加载和解析的复杂性"],
    "contexts": ["项目必须遵循依赖倒置原则，高层模块不应依赖于底层模块的具体实现"]
  }},
  {{
    "problem": "直接返回 null 会导致调用方代码复杂且容易出现 NullPointerException。",
    "suggestion": "(微观实现) Repository 的数据加载方法在失败时不应返回 null，而应返回 `Optional<T>`。",
    "reasons": ["强制调用方显式处理数据可能不存在的情况，避免了NPE", "这是一种更现代、更安全的Java编程范式"],
    "contexts": ["项目代码的 Java 版本必须在 8 或以上，以支持 Optional API"]
  }},
  {{
    "problem": "初版代码在代码风格、命名和实现细节上存在大量不规范之处。",
    "suggestion": "对整体实现进行全面的代码质量与风格统一的重构。",
    "reasons": ["提升代码的可读性和可维护性", "遵循Java社区和JabRef项目的编码规范"],
    "contexts": ["团队成员必须就统一的编码规范（如命名、日志格式等）达成共识"]
  }}
]

现在请分析以下内容：

对话内容(一段多轮的代码评审对话，可能包含多个开发者的发言)：
{dialog}

相关评论(可以理解为当前对话内容的上下文，不需要从中抽取任何内容，只是帮助你更好理解对话内容)：
{comment}

相关代码：
{code}

涉及行的代码：
{concerned_lines}
"""
    return prompt

def extract_suggestion_by_dialog_with_code_english(dialog, code, comment, start_line, end_line):
    """
    Prompt generator for extracting design knowledge from GitHub code review dialogues
    
    Args:
        dialog: Programmer dialogue content (JSON format string)
        code: Related code content
        comment: Comment content
        start_line: Starting line number
        end_line: Ending line number
    
    Returns:
        str: Complete prompt for large language model
    """

    line_info = f"line {start_line}"

    if start_line != end_line:
        line_info = f"lines {start_line} to {end_line}"

    concerned_lines = code.splitlines()[start_line-1:end_line]
    concerned_lines = "\n".join(concerned_lines)
    
    dialog = json.dumps(dialog, indent = 2,ensure_ascii=False)

    prompt = f"""You are a software engineering expert who needs to extract valuable design knowledge and best practices from programmers' code review dialogues on GitHub.

## Important Constraints
**Strict Requirement: Only extract content that developers explicitly discuss or suggest in the dialogue. Except for the condition and type fields, all other fields must absolutely not be based on code inference or add suggestions not mentioned in the dialogue!**

## Task Description
Carefully read the programmer dialogue content and **only extract** design suggestions and technical decisions explicitly mentioned in the dialogue, focusing on:
- Problems or requirements explicitly raised by developers in the dialogue
- Suggestions or recommended practices explicitly proposed by developers in the dialogue
- Arguments or reasons explicitly provided by developers in the dialogue

## Output Format
Please output the extracted design knowledge in the following JSON format:
[
  {{
    "problem": "Problem that triggered the discussion",
    "suggestion": "Specific design suggestions or recommended practices",
    "reasons": ["Reasons or arguments supporting the suggestion"],
    "contexts": ["Prerequisites for the suggestion"],
    "type": "Type of suggestion",
  }}
]

## Field Descriptions
"problem": "This field represents 'Why do we need to discuss?' or 'What is the context we are trying to solve?' It records the root cause that triggered this design discussion. For example, we found that users have a very poor image loading experience when the network is poor.As short as possible"
"suggestion": "This field is the answer to 'What should we do?' It is the core of the entire design knowledge, a specific, actionable action plan or technical choice. It should be clear guidance, not a vague direction. For example, it is best to split this large Service class into multiple smaller, single-responsibility classes."
"reasons": "This field answers 'Why is this suggestion good?' It MUST ONLY include reasons that are explicitly stated in the dialogue content. If no reasons are explicitly mentioned in the dialogue, this should be an empty array. Do not add any inferred or speculated reasons. For example, if a developer explicitly states 'We should use caching because it reduces database load and improves response time', these would be valid reasons to include."
"contexts": "This field captures time-sensitive or environment-dependent conditions that may affect the validity of the suggestion over time. It includes:\n1. Version dependencies: Specific versions of software, frameworks, or APIs that the suggestion relies on\n2. Environmental requirements: Particular operating systems, hardware configurations, or network conditions\n3. Business constraints: Specific business scenarios, data scales, or user volumes where the suggestion applies\nWhen these conditions change, the suggestion may become invalid or need modification. For example, 'This optimization is specifically for React v16.x' or 'This approach works for user bases under 1 million'."
"type": "This field records the type of suggestion, including architecture design, code style, performance optimization, vulnerability security, testing and maintenance, error handling, user experience, environment configuration. This field allows some speculation, that is, what developers may not have explicitly mentioned in the discussion"

## Extraction Principles
1. **STRICT SOURCE RULE**: All extracted content (problems, suggestions, reasons) MUST ONLY come from the dialogue content. The dialogue is the ONLY valid source for extraction.

2. **AUXILIARY INFORMATION RULE**: The provided code snippets (code, concerned_lines) and Related comments are ONLY for understanding context. They MUST NEVER be used as sources for extraction. They only help you understand:
   - Function names and variables mentioned in the dialogue
   - Code logic being discussed
   - Technical background of the discussion

3. **NO INFERENCE RULE**: Only extract content that is explicitly discussed in the dialogue. Do not:
   - Infer possible suggestions from code content
   - Extract content from Related comments
   - Add suggestions based on your own expertise
   - Combine information from different sources
   - Add any reasons that are not explicitly stated in the dialogue (reasons field must be empty array if no reasons are mentioned)

4. **PRECISE MATCHING RULE**: The expression of suggestions should be faithful to the original expression in the dialogue. Do not rephrase or enhance suggestions with information from other sources.

5. **CONTEXTS EXTRACTION RULE**: For the contexts field:
   - Focus on conditions that may change over time (version dependencies, environment requirements, business constraints)
   - Only include conditions that would invalidate or significantly affect the suggestion if they change
   - Prefer explicit mentions of version numbers, system requirements, or scale limitations
   - Do not include general best practices or permanent technical facts

## Additional Notes
- **Source Validation**: Before including any content in your output, verify that it comes ONLY from the dialogue content
- **Empty Fields**: 
  - The suggestion field cannot be an empty string
  - The reference field must contain at least one statement from the dialogue (not from comments)
- **Background Information**: You can use your understanding from code and comments to better comprehend the dialogue, but all extracted content must come from the dialogue itself
- **Output Format**:
  - All output should be in **English**
  - Output should be a directly parseable JSON string
  - Do not include any additional markers or explanations
  - Do not wrap output in ```json ``` blocks

## Output Example:
[
  {{
  "problem": "Each call to loadrepository() needs to fetch predatory journal updates from the network, which is inefficient.",
  "suggestion": "Suggest modifying JournalListMvGenerator to directly generate a local .mv file for predatory journals.",
  "reasons": [
    "This way it only needs to be generated once when the file is updated, and all subsequent calls can load directly from local without network access.",
    "Trying to use BackgroundTask wrapper to solve this problem is difficult and will cause MainArchitectureTest test failures."
  ],
  "contexts": ["This optimization is only relevant for JDK versions 8 and above", "The solution assumes the system has at least 8GB of available memory"],
  "type": "performance optimization",
  }},
  {{
    "problem": "Error: At least one of p12-filepath or p12-file-base64 must be provided",
    "suggestion": "You can ignore the failure reminder",
    "reasons": [" github's encrypted signature key is needed, which may cause this error during deployment, but it doesn't affect anything."]
  ],
  "contexts": ["Deployment error on mac"],
  "type": "environment configuration"
  }},
  {{
  "problem": "Multiple Services contain duplicate user permission validation logic, causing code redundancy and difficulty in maintenance.",
  "suggestion": "Suggest using AOP (Aspect-Oriented Programming) or Interceptor approach to extract permission validation logic into an independent aspect, uniformly handling all requests that need permission verification.",
  "reasons": ["Can eliminate duplicate code and improve code reusability.", "When permission logic changes, only one place needs to be modified, reducing maintenance costs."]
  ],
  "contexts": [],
  "type": "architecture design"
  }}
]

Now please analyze the following content:

Dialogue content (a multi-round code review dialogue that may include multiple developers' statements):
{dialog}

Additional Context (IMPORTANT: This section is STRICTLY for reference only):
- This context MAY OR MAY NOT be relevant to the dialogue content
- DO NOT extract ANY information from this section
- If the dialogue content is clear enough, you can ignore this context completely
- This section only serves as optional background information to help understand technical terms or concepts mentioned in the dialogue
{comment}

Related code:
{code}

Code for the involved lines:
{concerned_lines}
"""
    return prompt


def extract_set_by_llm_with_suggestion_cards(suggestion_cards, comment):
  return ""