from app.config import JIRA_URL, EMAIL, API_TOKEN, WKHTML_PATH

import os
import base64
import tempfile
import requests
from bs4 import BeautifulSoup
import pdfkit
from jira import JIRA
import openai
from asyncio import to_thread
from app.prompts import IMAGE_DESCRIPTION_PROMPT

pdfkit_config = pdfkit.configuration(wkhtmltopdf=WKHTML_PATH)
jira = JIRA(server=JIRA_URL, basic_auth=(EMAIL, API_TOKEN))

def generate_pdf_base64_from_jira(issue_key: str) -> str:
    issue = jira.issue(issue_key, expand="renderedFields")
    summary = issue.fields.summary
    html_desc = issue.renderedFields.description or ""

    soup = BeautifulSoup(html_desc, "html.parser")
    for img_tag in soup.find_all("img"):
        src = img_tag.get("src")
        if not src:
            continue
        img_url = src if src.startswith("http") else JIRA_URL + src
        try:
            r = requests.get(img_url, auth=(EMAIL, API_TOKEN))
            if r.status_code == 200:
                mime = r.headers.get("Content-Type", "image/png")
                encoded = base64.b64encode(r.content).decode()
                img_tag["src"] = f"data:{mime};base64,{encoded}"
            else:
                img_tag.decompose()
        except Exception:
            img_tag.decompose()

    html = f"<html><head><meta charset='utf-8'></head><body><h1>{issue_key} - {summary}</h1>{soup}</body></html>"

    fd, tmp_pdf = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    try:
        pdfkit.from_string(html, tmp_pdf, configuration=pdfkit_config)
        with open(tmp_pdf, "rb") as f:
            return base64.b64encode(f.read()).decode()
    finally:
        os.remove(tmp_pdf)

def get_issue_text_with_described_images(issue_key: str) -> str:
    issue = jira.issue(issue_key, expand="renderedFields")
    summary = issue.fields.summary
    html_desc = issue.renderedFields.description or ""

    soup = BeautifulSoup(html_desc, "html.parser")

    # for idx, img_tag in enumerate(soup.find_all("img")):
    #     src = img_tag.get("src")
    #     if not src:
    #         img_tag.replace_with(f"(Figura {idx+1} non disponibile)")
    #         continue
    #     img_url = src if src.startswith("http") else JIRA_URL + src
    #     try:
    #         r = requests.get(img_url, auth=(EMAIL, API_TOKEN))
    #         if r.status_code == 200 and len(r.content) >= 5000:
    #             mime = r.headers.get("Content-Type", "image/png")
    #             b64 = base64.b64encode(r.content).decode()
    #             img_prompt = [
    #                 {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
    #                 {"type": "text", "text": IMAGE_DESCRIPTION_PROMPT}
    #             ]
    #             caption_resp = openai.OpenAI(api_key=os.getenv("OPENAI_KEY")).chat.completions.create(
    #                 model="gpt-4o",
    #                 messages=[{"role": "user", "content": img_prompt}],
    #                 temperature=0,
    #             )
    #             caption = caption_resp.choices[0].message.content.strip()
    #             img_tag.replace_with(f"(Figura {idx+1}) {caption}")
    #         else:
    #             img_tag.replace_with(f"(Figura {idx+1} non caricata)")
    #     except Exception:
    #         img_tag.replace_with(f"(Figura {idx+1} non disponibile)")

    clean = soup.get_text(separator="\n").strip()
    return f"{summary}\n\n{clean}"

async def get_issue_text_async(issue_key: str) -> str:
    return await to_thread(get_issue_text_with_described_images, issue_key)