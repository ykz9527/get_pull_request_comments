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

def extract_suggestion_by_dialog_with_code(dialog, code, start_line, end_line):
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
**严格要求：只能提取对话中开发者明确讨论或建议的内容，绝对不能基于代码推断或添加对话中未涉及的建议！**

## 任务说明
仔细阅读程序员对话内容，**仅提取**对话中明确提到的设计建议和技术决策，重点关注：
- 开发者在对话中明确提出的架构设计原则
- 对话中讨论的代码组织方式
- 对话中提及的性能优化建议
- 对话中推荐的最佳实践
- 对话中说明的技术选型理由
- 对话中讨论的设计模式应用

## 输出格式
请按以下 JSON 格式输出提取的设计知识：
[
  {{
    "problem": "现有代码的问题",
    "suggestion": "具体的设计建议或推荐做法",
    "argument": ["支持该建议的理由或论据"]
  }}
]

## 提取原则
1. **必须基于对话**：每个建议都必须能在对话中找到对应的明确表述
2. **不能推断**：不要基于代码内容推断可能的建议，只提取对话中实际讨论的内容
3. **不能补充**：不要添加对话中未提及但你认为相关的建议
4. **忽略非设计内容**：忽略纯粹的 bug 修复、语法错误、代码风格等讨论
5. **精确匹配**：建议的表述应该忠实于对话中的原始表达

## 补充说明
- 如果没有提取到任何设计建议，输出空数组
- 如果对话中没有提及问题，问题字段（problem）为空字符串
- 建议字段（suggestion）不能是空字符串
- 你可以在提取的建议和论据中添加自然语言描述的相关背景，比如代码的上下文，代码的功能，等等
- 你的输出应该是中文
- 你的输出应该是能够被程序直接解析成 JSON 格式的字符串，不要输出其他任何的标记、说明，不要将你输出的内容包含在 ```json ``` 块中

## 输出示例:
[
  {{
    "problem": "现有代码的问题1",
    "suggestion": "建议1",
    "argument": ["论据1"]
  }},
  {{
    "problem": "",
    "suggestion": "建议2",
    "argument": ["论据1","论据2"]
  }}
]

现在请分析以下内容：

对话内容：
{dialog}

相关代码：
{code}

讨论涉及的行：
{line_info}

涉及行的代码：
{concerned_lines}
"""
    return prompt

def extract_suggestions_by_comment_and_review(comment_body,content_type):
    """
    从GitHub代码评审对话中提取设计知识的prompt生成器
    
    Args:
        comment_body: 程序员对话内容（JSON格式字符串）
        type: 对话类型（评论或评审）
    
    Returns:
        str: 用于大模型的完整prompt
    """
    prompt = f"""你是一个软件工程专家，需要从 GitHub 上程序员的{content_type}中提取有价值的设计知识和最佳实践。

## 重要约束
**严格要求：只能提取{content_type}中开发者明确讨论或建议的内容，绝对不能添加对话中未涉及的建议！**

## 任务说明
仔细阅读程序员{content_type}的内容，**仅提取**{content_type}中明确提到的设计建议和技术决策，重点关注：
- 开发者在{content_type}中明确提出的架构设计原则
- {content_type}中讨论的代码组织方式
- {content_type}中提及的性能优化建议
- {content_type}中推荐的最佳实践
- {content_type}中说明的技术选型理由
- {content_type}中讨论的设计模式应用

## 输出格式
请按以下 JSON 格式输出提取的设计知识：
[
  {{
    "problem": "现有代码的问题",
    "suggestion": "具体的设计建议或推荐做法",
    "argument": ["支持该建议的理由或论据"]
  }}
]

## 提取原则
1. **必须基于{content_type}**：每个建议都必须能在{content_type}中找到对应的明确表述
3. **不能补充**：不要添加{content_type}中未提及但你认为相关的建议
4. **忽略非设计内容**：忽略纯粹的 bug 修复、语法错误、代码风格等讨论
5. **精确匹配**：建议的表述应该忠实于{content_type}中的原始表达

## 补充说明
- 如果没有提取到任何设计建议，输出空数组
- 如果{content_type}中没有提及问题，问题字段（problem）为空字符串
- 建议字段（suggestion）不能是空字符串
- 你可以在提取的建议和论据中添加自然语言描述的相关背景，比如代码的上下文，代码的功能，等等
- 你的输出应该是中文
- 你的输出应该是能够被程序直接解析成 JSON 格式的字符串，不要输出其他任何的标记、说明，不要将你输出的内容包含在 ```json ``` 块中

## 输出示例:
[
  {{
    "problem": "现有代码的问题1",
    "suggestion": "建议1",
    "argument": ["论据1"]
  }},
  {{
    "problem": "",
    "suggestion": "建议2",
    "argument": ["论据1","论据2"]
  }}
]

现在请分析以下内容：

{content_type}内容：
{comment_body}
"""
    return prompt