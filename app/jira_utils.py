from app.config import JIRA_URL, EMAIL, API_TOKEN,STORY_POINTS_FLD, ZUPIT_BOT_EMAIL, ZUPIT_BOT_TOKEN

from bs4 import BeautifulSoup
from jira import JIRA
from asyncio import to_thread
from app.models import JQLRequest
import json
from pathlib import Path
from requests.auth import HTTPBasicAuth
import requests

from app.repository import task_exists

zupit_bot_auth = HTTPBasicAuth(ZUPIT_BOT_EMAIL, ZUPIT_BOT_TOKEN)
headers = {"Accept": "application/json", "Content-Type": "application/json"}

jira_simonpaolo_lopez = JIRA(
    server=JIRA_URL,
    basic_auth=(EMAIL, API_TOKEN),
    options={"rest_api_version": "3"} 
)
jira_zupit_bot = JIRA(
    server=JIRA_URL,
    basic_auth=(ZUPIT_BOT_EMAIL, ZUPIT_BOT_TOKEN),
    options={"rest_api_version": "3"} 
)
def filter_trained(issues):
    return [i for i in issues if not task_exists(i.key)]

def get_issue_text_with_described_images(issue_key: str) -> str:
    issue = jira_simonpaolo_lopez.issue(issue_key, expand="renderedFields")
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

    filtered = [i for i in all_tasks if not task_exists(i["key"])]

    return [
        (
            issue["key"],
            issue["fields"].get(STORY_POINTS_FLD, "N/A"),
            issue["fields"]["created"]
        )
        for issue in filtered
    ]


def remove_watcher(issue_key: str):
    user_url = f"{JIRA_URL}/rest/api/3/user/search?query={ZUPIT_BOT_EMAIL}"
    user_resp = requests.get(user_url, headers=headers, auth=zupit_bot_auth)
    user_resp.raise_for_status()
    users = user_resp.json()
    if not users:
        raise ValueError(f"Nessun utente trovato per {ZUPIT_BOT_EMAIL}")
    
    account_id = users[0]["accountId"]

    url = f"{JIRA_URL}/rest/api/3/issue/{issue_key}/watchers"
    response = requests.delete(
        f"{url}?accountId={account_id}",
        headers=headers,
        auth=zupit_bot_auth,
    )

    if response.status_code in (204, 404):
        print(f"✅ Watcher {ZUPIT_BOT_EMAIL} rimosso da {issue_key}")
        return {"issueKey": issue_key, "removed": response.status_code == 204}

    print(f"⚠️ Errore rimozione watcher {ZUPIT_BOT_EMAIL} da {issue_key}: {response.status_code} {response.text}")
    response.raise_for_status()
    return {"issueKey": issue_key, "removed": False, "error": response.text}


def add_comment(issue_key: str, text: str):
    """Aggiunge un nuovo commento all’issue."""
    jira_zupit_bot.add_comment(issue_key, make_adf_comment(text))
    jira_zupit_bot.remove_watcher(issue_key)
    remove_watcher(issue_key)


def update_comment(issue_key: str, comment_id: str, text: str):
    """Aggiorna un commento esistente."""
    delete_comment(issue_key, comment_id)
    jira_zupit_bot.add_comment(issue_key, make_adf_comment(text))
    remove_watcher(issue_key)


def delete_comment(issue_key: str, comment_id: str):
    """Elimina un commento da un ticket Jira (API v2 per compatibilità)"""
    url = f"{JIRA_URL}/rest/api/2/issue/{issue_key}/comment/{comment_id}"
    response = requests.delete(url, headers=headers, auth=zupit_bot_auth)
    if response.status_code == 204:
        return {"deleted": True}
    elif response.status_code == 404:
        return {"deleted": False, "reason": "Comment not found"}
    else:
        response.raise_for_status()

def make_adf_comment(text: str) -> dict:
    return {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": text}],
            }
        ],
    }


def format_verified_similars(similar_tasks: dict) -> str:
    """
    Converte un dizionario di similari del tipo:
    { '2.0': [{'key': 'X', ...}, ...], ... }
    in una stringa leggibile tipo:
    "2sp: X, Y\n3sp: A, B"
    """
    if not similar_tasks:
        return "Nessuna storia simile trovata."

    lines = []
    for sp, tasks in sorted(similar_tasks.items(), key=lambda x: float(x[0])):
        keys = ", ".join(t["key"] for t in tasks)
        lines.append(f"{sp} sp: {keys}")
    return "\n".join(lines)


def delete_steemo_comment(data: dict):
    issue_key = data.get("key")
    comments = data.get("fields", {}).get("comment", {}).get("comments", [])

    steemo_comment = next(
        (c for c in comments if "STEEMO" in c.get("body", "") and "ZupitBot" in c.get("author", {}).get("displayName", "")),
        None
    )

    if not steemo_comment:
        return {"issueKey": issue_key, "deleted": False, "reason": "No STEEMO comment found"}

    comment_id = steemo_comment["id"]

    result = delete_comment(issue_key, comment_id)
    return {"issueKey": issue_key, "deleted": True, "comment_id": comment_id, **result}