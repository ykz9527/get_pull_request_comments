import json
import pandas as pd
import pypandoc

with open("output/pr_data_py_github_10592.json", "r") as f:
    data = json.load(f)

review_threads = data["reviewThreads"]

comments = data["globalDiscussions"]

comment_list = []

review_list = []

for comment in comments:
    comment_list.append({
        "user": comment["author"],
        "comment": comment["body"]
        })

for review_thread in review_threads:
    diff_hunk = review_thread["diffHunk"]
    dialog = []
    for comment in review_thread["comments"]["nodes"]:
        dialog.append({
            "user": comment["author"],
            "comment": comment["body"]
            })

    review_list.append({
        "diff_hunk": diff_hunk,
        "dialog": dialog
    })

output = {
    "comments": comment_list,
    "reviews": review_list
}



with open("output/pr_data_py_github_10592_review_for_kag.json", "w") as f:
    json.dump(output, f, indent=4)

markdown_string = ""

markdown_string += "Global Discussions:\n"
for comment in comment_list:

    markdown_string += f"{comment['user']}: {comment['comment']}\n\n"

markdown_string += "\n\nCode Reviews:\n"

for review in review_list:
    # markdown_string += f"Diff Hunk:\n {review['diff_hunk']} |\n\n"
    markdown_string += "Dialog:\n"
    for comment in review["dialog"]:
        markdown_string += f"{comment['user']}: {comment['comment']}\n\n"
    
    markdown_string += "\n\n"

with open("output/pr_data_py_github_10592_review_for_kag.txt", "w") as f:
    f.write(markdown_string)
    


