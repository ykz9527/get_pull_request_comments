import fetch_each_part_in_pr_util as githubutil
from datetime import datetime
import util.ai.llm_client as llm_client
import util.ai.prompt as prompt
import json
import time
from util.logging import default_logger

# source .env before you run this script, in this file is the LLM api key

def main():
    pr_info = {
        "owner": "JabRef",
        "repo": "JabRef",
        "pr_number": 10592,
    }

    with open(f"output/pr_data_py_github_{pr_info['pr_number']}.json",'r')as f:
        pr_data = json.load(f)

    review_threads = pr_data["reviewThreads"]
    globalDiscussions = pr_data["globalDiscussions"]
    # reviews = pr_data["reviews"]

    review_thread_suggestion_list = extract_review_thread_pipeline(review_threads,globalDiscussions)
    # review_thread_suggestion_list = []
    comment_suggestion_list = extract_comment_and_review_pipeline(globalDiscussions)
    # review_suggestion_list = extract_comment_and_review_pipeline(reviews,"评审")

    all_suggestions = {
        "reviewThreadSuggestions": review_thread_suggestion_list,
        "commentSuggestions": comment_suggestion_list,
        # "reviewSuggestions": review_suggestion_list,
    }

    with open(f"output/all_suggestions_{pr_info['pr_number']}_{time.ctime()}.json",'w')as f:
        json.dump(all_suggestions,f,indent=2,ensure_ascii=False)

def extract_comment_and_review_pipeline(comments_or_reviews):
    """
    提取 comment 中的 suggestion 的 pipeline
    
    Args:
        comments (list): list of comments
        commits (list): list of commits
    
    Returns:
        list: list of suggestions
    """

    suggestion_list = []
    comment_body_list = []
    for comment in comments_or_reviews:
        default_logger.info(f"start process comment [{comment['id']}]")
        if comment["body"].strip() == "":
            default_logger.info(f"[{comment['id']}] is empty")
            continue
        comment_body_list.append({
            'author': comment['author'],
            'body': comment['body'],
        })

    comment_prompt = prompt.extract_suggestion_by_dialog_with_code(comment_body_list,"","",0,0)
    default_logger.debug(f"prompt: [{comment_prompt}]")

    retry_times = 5
    while retry_times > 0:
        try:
            model_client = llm_client.get_llm_client("deepseek-chat")
            response = model_client.generate_text([{"role": "user", "content": comment_prompt}])
            default_logger.debug(f"[{comment['id']}] model response: [{response}]")
            suggestion_list.append({
                "commentId": comment["id"],
                "review": json.loads(response),
            })
            break
        except Exception as e:
            default_logger.error(f"[{comment['id']}] has error: [{e}]")
            retry_times -= 1
            continue

    return suggestion_list


def extract_single_review_thread(review_thread,globalDiscussions):
    """
    提取单个 review thread 的 pipiline
    
    Args:
        review_thread (dict): the review thread
        commit (dict): the commit just before the comment
        pr_info (dict): the info of pr
    
    Returns:
        list: suggestions
    """
    # try:
    #     code_snippet = githubutil.fetch_file_content(pr_info["owner"],pr_info["repo"],commit["oid"],review_thread["path"])
    #     if code_snippet is None or code_snippet.strip() == "":
    #         default_logger.warning(f"when extract review thread [{review_thread['id']}], has not found code snippet {review_thread['path']} related")
    #         raise ValueError(f"when extract review thread [{review_thread['id']}], has not found code snippet {review_thread['path']} related")
    # except Exception as e:
    #     default_logger.error(f"when extract review thread [{review_thread['id']}], has error: [{e}]")
    #     raise e
    diffHunk = review_thread["diffHunk"]
    comments_in_review_thread = []

    for comment in review_thread["comments"]["nodes"]:
        comments_in_review_thread.append(
            {
                "user": comment["author"],
                "comment": comment["body"],
            }
        )
    if review_thread['related_review_body_id'] is not None:
        id = review_thread['related_review_body_id']
        # globalDiscussions is a list, need to find matching id
        matching_discussion = next((d for d in globalDiscussions if d['id'] == id), None)
        if matching_discussion:
            comment_summary = matching_discussion['body']
        else:
            comment_summary = ""
    else:
        comment_summary = ""

    start_line = None
    end_line = None
    if review_thread["originalLine"] is not None:
        if review_thread["originalStartLine"] is not None:
            start_line = review_thread["originalStartLine"]
            end_line = review_thread["originalLine"]
        else:
            start_line = review_thread["originalLine"]
            end_line = review_thread["originalLine"]
    else:
        default_logger.error(f"[{review_thread['id']}] has no originalLine")
        raise ValueError(f"[{review_thread['id']}] has no originalLine")
    
    suggestion_prompt = prompt.extract_suggestion_by_dialog_with_code(comments_in_review_thread, diffHunk,comment_summary, start_line,end_line)

    model_client = llm_client.get_llm_client("deepseek-chat")
    default_logger.debug(f"when extract review thread [{review_thread['id']}], suggestion_prompt: [{suggestion_prompt}]")

    retry_times = 5

    while retry_times > 0:
        try:
            response = model_client.generate_text([{"role": "user", "content": suggestion_prompt}])
            default_logger.debug(f"when extract review thread [{review_thread['id']}], response: [{response}]")
            suggestions = json.loads(response)
            return suggestions
        except Exception as e:
            default_logger.error(f"when extract review thread [{review_thread['id']}], has error: [{e}]")
            retry_times -= 1
            time.sleep(1)

    raise Exception(f"when extract review thread [{review_thread['id']}], reached max retry times")
    
def extract_review_thread_pipeline(review_threads,globalDiscussions):
    """
    提取 review thread 中的设计决策的 pipeline
    
    Args:
        review_threads (list): list of review threads
        commits (list): list of commits
        pr_info (dict): the info of pr
    
    Returns:
        list: list of suggestions
    """
    suggestion_list = []

    for review_thread in review_threads:
        try:
            default_logger.info(f"Start processing review thread {review_thread["id"]}")
            if review_thread["comments"]["nodes"] is None or len(review_thread["comments"]["nodes"])==0:
                default_logger.warning(f"review_thread: [{review_thread['id']}] has no comment")
                continue

            default_logger.info(f"looking for the commit just before the comment of review_thread: [{review_thread['id']}]")
            # commit_just_before = find_commit_just_before_target_time(commits, review_thread["comments"]["nodes"][0]["createdAt"])
            # if commit_just_before is None:
            #     default_logger.warning(f"review_thread: [{review_thread['id']}] has no commit just before the comment")
            #     continue

            # default_logger.info(f"review_thread: [{review_thread['id']}] has commit: [{commit_just_before['oid']}] just before the comment")
            default_logger.info(f"start to extract suggestion of review_thread: [{review_thread['id']}]")
            suggestion = extract_single_review_thread(review_thread,globalDiscussions)

            suggestion_list.append({
                "reviewThreadId": review_thread["id"],
                "review": suggestion,
            })

        except Exception as e:
            default_logger.error(f"when extract review thread [{review_thread['id']}], has error: [{e}]")
            continue
        
    return suggestion_list

def find_commit_just_before_target_time(commits, due_time):
    """
    查找在目标时间之前的最近一次提交
    
    Args:
        commits (list): list of commits
        due_time (str): the time of comment
    
    Returns:
        dict: the commit just before the comment
    """
    due_time_dt = datetime.fromisoformat(due_time.replace('Z', '+00:00'))
    if not commits or datetime.fromisoformat(commits[0]["committedDate"].replace('Z', '+00:00')) >= due_time_dt:
        return None
    left, right = 0, len(commits) - 1
    while left < right:
        mid = (left + right + 1) // 2
        commit_time = datetime.fromisoformat(commits[mid]["committedDate"].replace('Z', '+00:00'))
        if commit_time < due_time_dt: 
            left = mid  
        else:
            right = mid - 1 
    return commits[left]

if __name__ == "__main__":
    main()