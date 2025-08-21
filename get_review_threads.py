import yaml
import requests
import json
from datetime import datetime
import uuid

# Read configuration from config.yaml
with open('config.yaml', 'r') as file:
    config = yaml.safe_load(file)
    limits = config['limits']

# Read PAT from PAT.token
with open('PAT.token', 'r') as file:
    pat = file.read().strip()

# GraphQL query with commit oid in comments
query = """
query($owner: String!, $repo: String!, $prNumber: Int!, $reviewLimit: Int!, $commentLimit: Int!) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $prNumber) {
      reviewThreads(first: $reviewLimit) {
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
              commit {
                oid
              }
              author {
                login
              }
            }
          }
        }
      }
    }
  }
}
"""

# Variables for the query
variables = {
    "owner": "RylynnWang",
    "repo": "TestGraphQL",
    "prNumber": 1,
    "reviewLimit": limits['reviews'],
    "commentLimit": limits['review_comments']
}

# GitHub API endpoint
url = "https://api.github.com/graphql"

# Headers for authentication
headers = {
    "Authorization": f"Bearer {pat}",
    "Content-Type": "application/json"
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
    else:
        # Extract reviewThreads nodes
        review_threads = data['data']['repository']['pullRequest']['reviewThreads']['nodes']
        # Save to JSON file
        output_file = f"pr_review_threads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(review_threads, f, indent=2, ensure_ascii=False)
        print(f"Review threads with comment commit OIDs saved to {output_file}")
else:
    print(f"Request failed with status code {response.status_code}: {response.text}")