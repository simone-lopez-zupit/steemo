from app.config import JIRA_URL, EMAIL, API_TOKEN

from bs4 import BeautifulSoup
from jira import JIRA
from asyncio import to_thread

jira = JIRA(server=JIRA_URL, basic_auth=(EMAIL, API_TOKEN))

def get_issue_text_with_described_images(issue_key: str) -> str:
    issue = jira.issue(issue_key, expand="renderedFields")
    summary = issue.fields.summary
    html_desc = issue.renderedFields.description or ""

    soup = BeautifulSoup(html_desc, "html.parser")
    clean = soup.get_text(separator="\n").strip()
    return f"{summary}\n\n{clean}"

async def get_issue_text_async(issue_key: str) -> str:
    return await to_thread(get_issue_text_with_described_images, issue_key)