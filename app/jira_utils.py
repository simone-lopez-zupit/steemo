from app.config import JIRA_URL, EMAIL, API_TOKEN,STORY_POINTS_FLD

from bs4 import BeautifulSoup
from jira import JIRA
from asyncio import to_thread
import re
from app.models import JQLRequest
import json
from pathlib import Path
from requests.auth import HTTPBasicAuth
import requests

trained_file_path = Path("data/trained_with.json")
with trained_file_path.open("r", encoding="utf-8") as f:
    trained_data = json.load(f)

trained_issues_set = set()
for issues in trained_data.values():
    trained_issues_set.update(issues)
jira = JIRA(
    server=JIRA_URL,
    basic_auth=(EMAIL, API_TOKEN),
    options={"rest_api_version": "3"} 
)
def filter_trained(issues):
    return [i for i in issues if i.key not in trained_issues_set]

def get_issue_text_with_described_images(issue_key: str) -> str:
    issue = jira.issue(issue_key, expand="renderedFields")
    summary = issue.fields.summary
    html_desc = issue.renderedFields.description or ""

    soup = BeautifulSoup(html_desc, "html.parser")
    clean = soup.get_text(separator="\n").strip()
    return f"{summary}\n\n{clean}"
# def get_issue_text_with_described_images(issue_key: str) -> str:
#     issue = jira.issue(issue_key, expand="renderedFields")
#     summary = issue.fields.summary
#     html_desc = issue.renderedFields.description or ""

#     soup = BeautifulSoup(html_desc, "html.parser")
#     clean_desc = soup.get_text(separator="\n").strip()

#     raw_ac = getattr(issue.fields, "customfield_11332", None)
#     ac_items = []
    
#     if raw_ac:
#         text_matches = re.findall(r'text:\s*>?-?\s*(.*?)(?=\s+checked:)', raw_ac, flags=re.DOTALL)
#         ac_items = [re.sub(r'\s+', ' ', match.strip()) for match in text_matches]
                
#     for i in range(len(ac_items)) :
#         ac_items[i]=f"Obbiettivo:{i+1}.{ac_items[i]}"
#     ac_items = "\n\n".join(ac_items)
#     if(len(ac_items)>0):
#         return f"{summary}\n\n{clean_desc}\n\n**Obbiettivi:**\n\n{ac_items}"
#     else:
#         return f"{summary}\n\n{clean_desc}"

async def get_issue_text_async(issue_key: str) -> str:
    return await to_thread(get_issue_text_with_described_images, issue_key)

async def get_all_queried_stories(jqlRequest: JQLRequest):
    def fetch_issues(jql: str):
        all_issues = []
        url = f"{JIRA_URL}/rest/api/3/search/jql"
        auth = HTTPBasicAuth(EMAIL, API_TOKEN)

        next_token = None
        chunk = 100

        while True:
            params = {
                "jql": jql,
                "maxResults": chunk,
                "fields": ["summary", STORY_POINTS_FLD, "created"],
            }
            if next_token:
                params["nextPageToken"] = next_token

            response = requests.get(
                url,
                headers={"Accept": "application/json"},
                params=params,
                auth=auth
            )
            response.raise_for_status()
            data = response.json()

            issues = data.get("issues", [])
            if not issues:
                break

            all_issues.extend(issues)

            next_token = data.get("nextPageToken")
            if not next_token:
                break

        return all_issues

    if jqlRequest.project == "all":
        jql = (
            'issuetype = Story AND "Story Points" IS NOT EMPTY '
            f'AND {jqlRequest.date_jql}'
        )
    else:
        jql = (
            f'project = {jqlRequest.project} AND issuetype = Story '
            'AND "Story Points" IS NOT EMPTY '
            f'AND {jqlRequest.date_jql}'
        )

    all_tasks = await to_thread(fetch_issues, jql)

    filtered = [i for i in all_tasks if i["key"] not in trained_issues_set]

    return [
        (
            issue["key"],
            issue["fields"].get(STORY_POINTS_FLD, "N/A"),
            issue["fields"]["created"]
        )
        for issue in filtered
    ]
