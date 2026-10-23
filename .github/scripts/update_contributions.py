
import os
import re
import requests
from html import escape

USERNAME = os.environ["GITHUB_USERNAME"]
TOKEN = os.environ["GITHUB_TOKEN"]
README = "README.md"

START = "<!-- OPEN_SOURCE_CONTRIBUTIONS:START -->"
END = "<!-- OPEN_SOURCE_CONTRIBUTIONS:END -->"

session = requests.Session()
session.headers.update({
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
})

query = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      pullRequestContributions(first: 30, orderBy: {direction: DESC, field: OCCURRED_AT}) {
        nodes {
          occurredAt
          pullRequest {
            title
            url
            state
            repository {
              nameWithOwner
            }
          }
        }
      }
      issueContributions(first: 30, orderBy: {direction: DESC, field: OCCURRED_AT}) {
        nodes {
          occurredAt
          issue {
            title
            url
            repository {
              nameWithOwner
            }
          }
        }
      }
    }
  }
}
"""

response = session.post(
    "https://api.github.com/graphql",
    json={"query": query, "variables": {"login": USERNAME}},
    timeout=30,
)
response.raise_for_status()
payload = response.json()

if payload.get("errors"):
    raise RuntimeError(f"GitHub GraphQL error: {payload['errors']}")

user = payload.get("data", {}).get("user")
if not user:
    raise RuntimeError(f"GitHub user not found: {USERNAME}")

collection = user["contributionsCollection"]
items = []

for node in collection["pullRequestContributions"]["nodes"]:
    pr = node["pullRequest"]
    items.append({
        "date": node["occurredAt"][:10],
        "type": "Pull Request",
        "title": pr["title"],
        "url": pr["url"],
        "repo": pr["repository"]["nameWithOwner"],
        "state": pr["state"],
    })

for node in collection["issueContributions"]["nodes"]:
    issue = node["issue"]
    items.append({
        "date": node["occurredAt"][:10],
        "type": "Issue",
        "title": issue["title"],
        "url": issue["url"],
        "repo": issue["repository"]["nameWithOwner"],
        "state": "",
    })

items.sort(key=lambda item: item["date"], reverse=True)

if items:
    lines = [
        f"- **[{escape(item['title'])}]({item['url']})**",
        f"  - `{escape(item['repo'])}` · {item['type']} · {item['date']}"
        + (f" · {item['state'].title()}" if item["state"] else "")
        for item in items[:20]
    ]
    section = "\n".join(lines)
else:
    section = "_No public issue or pull request contributions were found yet._"

with open(README, "r", encoding="utf-8") as file:
    readme = file.read()

pattern = re.escape(START) + r".*?" + re.escape(END)
replacement = f"{START}\n{section}\n{END}"

updated, count = re.subn(pattern, replacement, readme, count=1, flags=re.S)

if count != 1:
    raise RuntimeError("Could not find the contribution markers in README.md.")

with open(README, "w", encoding="utf-8") as file:
    file.write(updated)

print(f"Updated contribution section with {len(items[:20])} entries.")
