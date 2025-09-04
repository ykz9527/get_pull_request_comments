import json

def do_content_message(message):
    """
    A function that returns a prompt to classify GitHub discussion messages as relevant (Yes) or irrelevant (No) to code/project.
    
    Args:
        message (str): The GitHub discussion message to classify.
    
    Returns:
        str: The prompt content.
    """
    prompt = f"""
You are a classifier for filtering GitHub developer discussions. Your task is to determine if a given message is relevant to code, programming, or the project itself. 

Relevant messages include:
- Discussions about code snippets, bugs, features, implementations, or technical aspects of the project.
- Suggestions for improvements, error reports, or questions about functionality.
- Updates on project progress, merges, or pull requests.

Irrelevant messages include:
- Social chit-chat, like holiday greetings (e.g., "Happy New Year!"), personal thanks (e.g., "Thanks for your help!"), congratulations, or off-topic comments.
- Non-technical acknowledgments or casual conversations not tied to code/project.

For the input message, respond ONLY with "Yes" if it is relevant, or "No" if it is irrelevant. Do not add any explanations, reasons, or extra text.

Examples:
Input: "I fixed the bug in line 42 by changing the variable type to int."
Output: Yes

Input: "Merry Christmas everyone!"
Output: No

Input: "Thanks a lot for reviewing my PR!"
Output: No

Input: "We should add error handling to the API endpoint to prevent crashes."
Output: Yes

Input: "Great job on the last commit!"
Output: No

Now, classify this message: {message}
""" 
    return prompt

def extract_suggestion_by_dialog_with_code(dialog, code, comment, start_line, end_line):
    """
    从GitHub代码评审对话中提取设计知识的prompt生成器
    
    Args:
        dialog: 程序员对话内容（JSON格式字符串）
        code: 相关代码内容
        line: 结束行号
        start_line: 开始行号
    
    Returns:
        str: 用于大模型的完整prompt
    """

    line_info = f"line {start_line}"

    if start_line != end_line:
        line_info = f"lines {start_line} to {end_line}"

    concerned_lines = code.splitlines()[start_line-1:end_line]
    concerned_lines = "\n".join(concerned_lines)
    
    dialog = json.dumps(dialog, indent = 2,ensure_ascii=False)

    prompt = f"""你是一个软件工程专家，需要从 GitHub 上程序员的代码评审对话中提取有价值的设计知识和最佳实践。

## 重要约束
**严格要求：只能提取对话中开发者明确讨论或建议的内容，除了condition和type字段,其他字段绝对不能基于代码推断或添加对话中未涉及的建议！**

## 任务说明
仔细阅读程序员对话内容，**仅提取**对话中明确提到的设计建议和技术决策，重点关注：
- 开发者在对话中明确提出的问题或需求
- 开发者在对话中明确提出的建议或推荐做法
- 开发者在对话中明确提出的论据或理由

## 输出格式
请按以下 JSON 格式输出提取的设计知识：
[
  {{
    "problem": "现有代码的问题",
    "suggestion": "具体的设计建议或推荐做法",
    "reasons": ["支持该建议的理由或论据"],
    "condition": ["建议的一些前提条件"],
    "type": "建议的类型",
    "reference": ["建议的参考来源"]
  }}
]

## 字段说明
"problem": "这个字段代表了“为什么需要讨论？”或者说“我们试图解决的上下文是什么？”。它记录了触发这次设计讨论的根本原因。比如，我们发现用户在网络不好的情况下，图片加载体验非常糟糕。"
"suggestion": "这个字段是“我们应该做什么？”的答案。它是整个设计知识的核心，是一个具体的、可操作的行动方案或技术选型。它应该是一个明确的指导，而不是一个模糊的方向。比如，最好是将这个大的 Service 类拆分成多个更小的、职责单一的类。"
"reasons": "这个字段回答了“为什么这个建议（Suggestion）是好的？”。它为 suggestion 提供了理论支持和逻辑依据，是说服他人接受该建议的关键。比如，因为缓存可以把常用的数据放在内存里，避免了每次都去查数据库，能极大提升响应速度。"
"condition": "这个字段记录了建议的一些前提条件，比如建议的适用范围，建议的限制条件，等等。这个字段允许一定的推测，也就是讨论中开发者可能没有明确提到的"
"type": "这个字段记录了建议的类型，包括 architecture design, code style, performance optimization, vulnerability security, testing and maintenance, error handling, user experience, environment configuration。这个字段允许一定的推测，也就是讨论中开发者可能没有明确提到的"
"reference": "这个字段记录了建议的参考来源，即，对话中某个或几个开发者的评论。这个字段应该是你提取 suggestion 字段的直接依据。你不需要把附和其他开发者和表达同意的评论也包含进来，只包含核心的评论就可以。例如：你不应该包含 'I agree'、'Good idea' 等表示附和和同意的发言。"

## Type 字段中的类型如下：
- architecture design: 涉及关于软件系统整体结构、组件和组织的宏观决策，以确保可扩展性、模块化和可维护性。示例：使用 PredatoryJournalListManager 统一管理项目中的掠夺性期刊的数据流，而不是自己实现数据管理。
- code style: 涉及编写干净、可读且一致的代码的规范和指南，例如命名约定、缩进或格式规则。示例：不要使用单字母变量，例如 int x，而是使用有意义的变量名，例如 int journalCount。
- performance optimization: 专注于提高代码执行效率的技术，减少 CPU、内存或时间等资源的使用。示例：建议为频繁访问的数据库查询实现缓存，以减少 Web 
- vulnerability security: 涉及识别和缓解与安全漏洞相关的风险，例如防止注入攻击、未经授权的访问或数据泄露。示例：建议对用户提交的表单进行输入净化，以防止 SQL 注入攻击。
- testing and maintenance: 涵盖编写测试、确保代码可靠性以及使代码库易于更新或调试的策略。示例：需要为 PredatoryJournalListManager 的更改添加测试用例，以确保其行为符合预期。
- error handling: 涉及检测、报告和从错误或异常中恢复的方法，以使应用程序更健壮且用户友好。示例：外部 API 调用出错时，返回一个空 List 而不是直接抛出异常。
- user experience: 涉及提升最终用户与软件交互时的可用性、可访问性和满意度的设计选择。示例：建议在 API 调用期间添加加载指示器，以避免用户认为应用程序卡死。
- environment configuration: 涉及设置和管理开发、测试或生产环境，包括工具、依赖或部署设置。示例：将 PredatoryJournalListMvGenerator 挂接到 build.gradle 文件中描述的构建过程中。

## 提取原则
1. **必须基于对话**：每个建议都必须能在对话中找到对应的明确表述,只从对话内容中抽取表述
2. **不能推断**：只提取对话中实际讨论的内容
3. 提供的代码片段（code, concerned_lines）仅用于帮助你理解对话中提到的具体函数名、变量名或代码逻辑。你的所有输出（问题、建议、论据）必须在对话或评论（dialog, comment）中有明确的文字来源，不要基于代码内容推断可能的建议
4. **精确匹配**：建议的表述应该忠实于对话中的原始表达

## 补充说明
- 如果对话中没有提及问题，问题字段（problem）为空字符串
- 建议字段（suggestion）不能是空字符串
- reference 字段不能是空数组
- 你可以在提取的建议和论据中添加自然语言描述的相关背景，比如代码的上下文，代码的功能，等等
- 你的输出应该是**英文**
- 你的输出应该是能够被程序直接解析成 JSON 格式的字符串，不要输出其他任何的标记、说明，不要将你输出的内容包含在 ```json ``` 块中

## 输出示例:
[
  {{
  "problem": "每次调用 loadrepository() 都需要从网络获取掠夺性期刊的更新，效率低下。",
  "suggestion": "建议修改 JournalListMvGenerator，让它直接为掠夺性期刊生成一个本地的 .mv 文件。",
  "reasons": [
    "这样做只需要在文件更新时生成一次，之后的所有调用都可以直接从本地加载，无需访问网络。",
    "尝试使用 BackgroundTask 包装器来解决此问题很困难，并且会导致 MainArchitectureTest 测试失败。"
  ],
  "condition": ["在 JournalListMvGenerator 中直接为掠夺性期刊生成一个 .mv 文件更合理。"],
  "type": "性能优化",
  "reference": ["Repeatedly calling `loadrepository()` downloads updates of predatory journals from the network multiple times, which is highly inefficient. Please modify `JournalListMvGenerator` to generate a local `.mv` cache each time."]
  }},
  {{
    "problem": "mac上部署时报错，Error: At least one of p12-filepath or p12-file-base64 must be provided",
    "suggestion": "可以无视失败提醒",
    "reasons": ["在macOS测试时需要用到github的加密签名秘钥，这可能会导致部署时的报这个错，不影响什么。"]
  ],
  "condition": [],
  "type": "环境配置"
  "reference": ["The deployment check for macOS is failing with the following error message:\r\n`Error: At least one of p12-filepath or p12-file-base64 must be provided`\r\n\r\nIs there something I need to do for this to pass?","Hi you can ignore the failing mac test. I does not work on forks because it require some github secrets for signing. We are working on trying to remove this run then for forks"]
  }},
  {{
  "problem": "多个 Service 中存在重复的用户权限校验逻辑，导致代码冗余且难以维护。",
  "suggestion": "建议使用AOP（面向切面编程）或拦截器（Interceptor）的方式，将权限校验逻辑抽取成一个独立的切面，统一处理所有需要权限验证的请求。",
  "reasons": ["可以消除重复代码，提高代码复用性。", "当权限逻辑变更时，只需要修改一处，降低了维护成本。"]
  ],
  "condition": [],
  "type": "架构设计"
  "refernece":["There is already an Interceptor in the repository. We should use that instead of creating a new one to handle the permission check."]
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
    "problem": "Problems with existing code",
    "suggestion": "Specific design suggestions or recommended practices",
    "reasons": ["Reasons or arguments supporting the suggestion"],
    "condition": ["Prerequisites for the suggestion"],
    "type": "Type of suggestion",
    "reference": ["Reference sources for the suggestion"]
  }}
]

## Field Descriptions
"problem": "This field represents 'Why do we need to discuss?' or 'What is the context we are trying to solve?' It records the root cause that triggered this design discussion. For example, we found that users have a very poor image loading experience when the network is poor."
"suggestion": "This field is the answer to 'What should we do?' It is the core of the entire design knowledge, a specific, actionable action plan or technical choice. It should be clear guidance, not a vague direction. For example, it is best to split this large Service class into multiple smaller, single-responsibility classes."
"reasons": "This field answers 'Why is this suggestion good?' It provides theoretical support and logical basis for the suggestion, and is key to convincing others to accept the suggestion. For example, because caching can put frequently used data in memory, avoiding database queries every time, which can greatly improve response speed."
"condition": "This field records some prerequisites for the suggestion, such as the applicable scope of the suggestion, limitation conditions of the suggestion, etc. This field allows some speculation, that is, what developers may not have explicitly mentioned in the discussion"
"type": "This field records the type of suggestion, including architecture design, code style, performance optimization, vulnerability security, testing and maintenance, error handling, user experience, environment configuration. This field allows some speculation, that is, what developers may not have explicitly mentioned in the discussion"
"reference": "This field records the reference sources for the suggestion, that is, comments from one or several developers in the dialogue. This field should be the direct basis for you to extract the suggestion field. You don't need to include comments that echo other developers and express agreement, just include core comments. For example: you should not include statements like 'I agree', 'Good idea' that express echoing and agreement."

## Types in the Type field are as follows:
- architecture design: Involves macro decisions about the overall structure, components and organization of software systems to ensure scalability, modularity and maintainability. Example: Use PredatoryJournalListManager to uniformly manage predatory journal data flow in the project, rather than implementing data management yourself.
- code style: Involves specifications and guidelines for writing clean, readable and consistent code, such as naming conventions, indentation or formatting rules. Example: Don't use single-letter variables like int x, but use meaningful variable names like int journalCount.
- performance optimization: Focuses on techniques to improve code execution efficiency, reducing the use of resources such as CPU, memory or time. Example: Suggest implementing caching for frequently accessed database queries to reduce Web
- vulnerability security: Involves identifying and mitigating risks related to security vulnerabilities, such as preventing injection attacks, unauthorized access or data leaks. Example: Suggest input sanitization for user-submitted forms to prevent SQL injection attacks.
- testing and maintenance: Covers strategies for writing tests, ensuring code reliability, and making codebases easy to update or debug. Example: Need to add test cases for changes to PredatoryJournalListManager to ensure its behavior meets expectations.
- error handling: Involves methods for detecting, reporting and recovering from errors or exceptions to make applications more robust and user-friendly. Example: When external API calls fail, return an empty List instead of directly throwing an exception.
- user experience: Involves design choices that enhance usability, accessibility and satisfaction when end users interact with software. Example: Suggest adding loading indicators during API calls to avoid users thinking the application is frozen.
- environment configuration: Involves setting up and managing development, testing or production environments, including tools, dependencies or deployment settings. Example: Hook PredatoryJournalListMvGenerator into the build process described in the build.gradle file.

## Extraction Principles
1. **Must be based on dialogue**: Each suggestion must have a corresponding explicit statement in the dialogue, only extract statements from dialogue content
2. **Cannot infer**: Only extract content actually discussed in the dialogue
3. The provided code snippets (code, concerned_lines) are only used to help you understand specific function names, variable names or code logic mentioned in the dialogue. All your outputs (problems, suggestions, reasons) must have clear textual sources in the dialogue or comments (dialog, comment), do not infer possible suggestions based on code content
4. **Precise matching**: The expression of suggestions should be faithful to the original expression in the dialogue

## Additional Notes
- If no problem is mentioned in the dialogue, the problem field is an empty string
- The suggestion field cannot be an empty string
- The reference field cannot be an empty array
- You can add natural language descriptions of relevant background in the extracted suggestions and reasons, such as code context, code functionality, etc.
- Your output should be in **English**
- Your output should be a string that can be directly parsed into JSON format by a program, do not output any other markers or explanations, do not include your output in ```json ``` blocks

## Output Example:
[
  {{
  "problem": "Each call to loadrepository() needs to fetch predatory journal updates from the network, which is inefficient.",
  "suggestion": "Suggest modifying JournalListMvGenerator to directly generate a local .mv file for predatory journals.",
  "reasons": [
    "This way it only needs to be generated once when the file is updated, and all subsequent calls can load directly from local without network access.",
    "Trying to use BackgroundTask wrapper to solve this problem is difficult and will cause MainArchitectureTest test failures."
  ],
  "condition": ["It makes more sense to directly generate a .mv file for predatory journals in JournalListMvGenerator."],
  "type": "performance optimization",
  "reference": ["Repeatedly calling `loadrepository()` downloads updates of predatory journals from the network multiple times, which is highly inefficient. Please modify `JournalListMvGenerator` to generate a local `.mv` cache each time."]
  }},
  {{
    "problem": "Deployment error on mac, Error: At least one of p12-filepath or p12-file-base64 must be provided",
    "suggestion": "You can ignore the failure reminder",
    "reasons": ["When testing on macOS, github's encrypted signature key is needed, which may cause this error during deployment, but it doesn't affect anything."]
  ],
  "condition": [],
  "type": "environment configuration"
  "reference": ["The deployment check for macOS is failing with the following error message:\r\n`Error: At least one of p12-filepath or p12-file-base64 must be provided`\r\n\r\nIs there something I need to do for this to pass?","Hi you can ignore the failing mac test. I does not work on forks because it require some github secrets for signing. We are working on trying to remove this run then for forks"]
  }},
  {{
  "problem": "Multiple Services contain duplicate user permission validation logic, causing code redundancy and difficulty in maintenance.",
  "suggestion": "Suggest using AOP (Aspect-Oriented Programming) or Interceptor approach to extract permission validation logic into an independent aspect, uniformly handling all requests that need permission verification.",
  "reasons": ["Can eliminate duplicate code and improve code reusability.", "When permission logic changes, only one place needs to be modified, reducing maintenance costs."]
  ],
  "condition": [],
  "type": "architecture design"
  "reference":["There is already an Interceptor in the repository. We should use that instead of creating a new one to handle the permission check."]
  }}
]

Now please analyze the following content:

Dialogue content (a multi-round code review dialogue that may include multiple developers' statements):
{dialog}

Related comments (can be understood as context for the current dialogue content, no need to extract any content from it, just to help you better understand the dialogue content):
{comment}

Related code:
{code}

Code for the involved lines:
{concerned_lines}
"""
    return prompt


def extract_suggestions_by_comment_and_review(comment_body):
    """
    从GitHub代码评审对话中提取设计知识的prompt生成器
    
    Args:
        comment_body: 程序员对话内容（JSON格式字符串）
        type: 对话类型（评论或评审）
    
    Returns:
        str: 用于大模型的完整prompt
    """
    prompt = f"""你是一个软件工程专家，需要从 GitHub 上程序员从PR里的评论中提取有价值的设计知识和最佳实践。

## 重要约束
**严格要求：只能提取评论中开发者明确讨论或建议的内容，绝对不能添加评论中未涉及的建议！**

## 任务说明
仔细阅读程序员评论的内容，尽可能全的提取评论中明确提到的设计建议和技术决策，重点关注：
- 开发者在评论中明确提出的架构设计原则
- 评论中讨论的代码组织方式
- 评论中提及的性能优化建议
- 评论中推荐的最佳实践
- 评论中说明的技术选型理由
- 评论中讨论的设计模式应用

## 输出格式
请按以下 JSON 格式输出提取的设计知识：
[
  {{
    "problem": "现有代码的问题",
    "suggestion": "具体的设计建议或推荐做法",
    "reasons": ["支持该建议的理由或论据"]
  }}
]

## 字段说明
"problem": "这个字段代表了“为什么需要讨论？”或者说“我们试图解决的上下文是什么？”。它记录了触发这次设计讨论的根本原因。比如，我们发现用户在网络不好的情况下，图片加载体验非常糟糕。"
"suggestion": "这个字段是“我们应该做什么？”的答案。它是整个设计知识的核心，是一个具体的、可操作的行动方案或技术选型。它应该是一个明确的指导，而不是一个模糊的方向。比如，最好是将这个大的 Service 类拆分成多个更小的、职责单一的类。"
"reasons": "这个字段回答了“为什么这个建议（Suggestion）是好的？”。它为 suggestion 提供了理论支持和逻辑依据，是说服他人接受该建议的关键。比如，因为缓存可以把常用的数据放在内存里，避免了每次都去查数据库，能极大提升响应速度。"

## 提取原则
1. **必须基于评论**：每个建议都必须能在评论中找到对应的明确表述
2. 一句话如果有多个建议一定一定需要分别记录
3. **不能补充**：不要添加评论中未提及但你认为相关的建议

## 补充说明
- 如果没有提取到任何设计建议，输出空数组
- 如果评论中没有提及问题，问题字段（problem）为空字符串
- 建议字段（suggestion）不能是空字符串
- 你可以在提取的建议和论据中添加自然语言描述的相关背景，比如代码的上下文，代码的功能，等等
- 你的输出应该是中文
- 你的输出应该是能够被程序直接解析成 JSON 格式的字符串，不要输出其他任何的标记、说明，不要将你输出的内容包含在 ```json ``` 块中

## 输出示例:
[
  {{
    "problem": "",
    "suggestion": "代码风格建议：using-jabrefs-code-style",
    "reasons": []
  }},
  {{
    "problem": "mac上部署时报错，Error: At least one of p12-filepath or p12-file-base64 must be provided",
    "suggestion": "可以无视失败提醒",
    "reasons": ["在macOS测试时需要用到github的加密签名秘钥，这可能会导致部署时的报这个错，不影响什么。"]
  }},
  {
  "problem": "多个 Service 中存在重复的用户权限校验逻辑，导致代码冗余且难以维护。",
  "suggestion": "建议使用AOP（面向切面编程）或拦截器（Interceptor）的方式，将权限校验逻辑抽取成一个独立的切面，统一处理所有需要权限验证的请求。",
  "reasons": ["可以消除重复代码，提高代码复用性。", "当权限逻辑变更时，只需要修改一处，降低了维护成本。"]
  }
]

现在请分析以下内容：

评论内容：
{comment_body}
"""
    return prompt