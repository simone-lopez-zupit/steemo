from app.config import JIRA_URL, EMAIL, API_TOKEN,STORY_POINTS_FLD

from bs4 import BeautifulSoup
from jira import JIRA
from asyncio import to_thread

from app.models import JQLRequest
import json
from pathlib import Path
trained_file_path = Path("data/trained_with.json")
with trained_file_path.open("r", encoding="utf-8") as f:
    trained_data = json.load(f)

trained_issues_set = set()
for issues in trained_data.values():
    trained_issues_set.update(issues)
jira = JIRA(server=JIRA_URL, basic_auth=(EMAIL, API_TOKEN))

def filter_trained(issues):
    return [i for i in issues if i.key not in trained_issues_set]

def get_issue_text_with_described_images(issue_key: str) -> str:
    issue = jira.issue(issue_key, expand="renderedFields")
    summary = issue.fields.summary
    html_desc = issue.renderedFields.description or ""

    soup = BeautifulSoup(html_desc, "html.parser")
    clean = soup.get_text(separator="\n").strip()
    return f"{summary}\n\n{clean}"

async def get_issue_text_async(issue_key: str) -> str:
    return await to_thread(get_issue_text_with_described_images, issue_key)

async def get_all_queried_stories(jqlRequest: JQLRequest):
    dict_key_issues = {}
    if(jqlRequest.project=="all"):
        projects=jira.projects()
        keys=[proj.key for proj in projects]

        for k in keys:
            issues = []
            chunk_size = 100
            start = 0
           
            jql = (
                f'project = {k} AND issuetype = Story '
                'AND "Story Points" IS NOT EMPTY '
                f'AND {jqlRequest.date_jql}'
            )
            
            while True:
                batch = jira.search_issues(jql, startAt=start, maxResults=chunk_size,fields=f"summary,{STORY_POINTS_FLD}")
                if len(batch) == 0:
                    break
                issues.extend(batch)
                start += chunk_size
            dict_key_issues[k] = filter_trained(issues)
    else:
        issues = []
        chunk_size = 100
        start = 0
        
        jql = (
            f'project = {jqlRequest.project} AND issuetype = Story '
            'AND "Story Points" IS NOT EMPTY '
            f'AND {jqlRequest.date_jql}'
        )
        
        while True:
            batch = jira.search_issues(jql, startAt=start, maxResults=chunk_size,fields=f"summary,{STORY_POINTS_FLD}")
            if len(batch) == 0:
                break
            issues.extend(batch)
            start += chunk_size
        dict_key_issues[jqlRequest.project] = filter_trained(issues)
    return [
        (issue.key, getattr(issue.fields, STORY_POINTS_FLD, "N/A"))
        for issues in dict_key_issues.values()
        for issue in issues
    ]