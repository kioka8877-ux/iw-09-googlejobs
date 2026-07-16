"""
IW-09 GoogleJobs — Google Jobs Results
Iron Warrior #9 — Emploi, offres structurées.
Aucun dédié sur RapidAPI.
"""
from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import sys
sys.path.insert(0, '/home/user/iron_warriors/shared')
from base import create_app, fetch_html, clean_text, get_timestamp, measure_latency
import time

app = create_app("IW-09 GoogleJobs", "Google Jobs results — offres d'emploi structurées")

class JobResult(BaseModel):
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    url: str
    salary: Optional[str] = None
    snippet: Optional[str] = None
    posted_time: Optional[str] = None
    position: int

class JobResponse(BaseModel):
    query: str
    engine: str
    results: List[JobResult]
    timestamp: str
    latency_ms: int

@app.get("/search", response_model=JobResponse)
async def google_jobs(
    q: str = Query(..., description="Job search query"),
    num: int = Query(20, ge=1, le=50),
    gl: str = Query("us"),
    hl: str = Query("en"),
    location: str = Query("", description="Location filter"),
):
    start = time.time()
    query = f"{q} jobs"
    if location:
        query += f" {location}"
    url = f"https://www.google.com/search?q={quote_plus(query)}&ibp=htl;jobs&hl={hl}&gl={gl}"
    try:
        html = await fetch_html(url)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Google Jobs fetch failed: {e}")

    soup = BeautifulSoup(html, 'html.parser')
    results = []
    seen = set()

    # Google Jobs results
    for div in soup.find_all('div', class_='PwjeAc') or soup.find_all('li', class_='iFjolb'):
        title_tag = div.find('div', class_='BjJfJf') or div.find('h3')
        company_tag = div.find('div', class_='tJ9Kec') or div.find('span', class_='lNknVb')
        location_tag = div.find('div', class_='QkPDje')
        salary_tag = div.find('span', class_='Ox5Mhc')
        link = div.find('a', href=True)
        snippet_tag = div.find('div', class_='YGpsLb')

        if title_tag and link:
            href = link['href']
            if href.startswith('/url?q='):
                href = href.split('/url?q=')[1].split('&')[0]
            if href in seen or not href.startswith('http'):
                continue
            seen.add(href)
            results.append(JobResult(
                title=clean_text(title_tag.get_text()),
                company=clean_text(company_tag.get_text()) if company_tag else None,
                location=clean_text(location_tag.get_text()) if location_tag else None,
                url=href,
                salary=clean_text(salary_tag.get_text()) if salary_tag else None,
                snippet=clean_text(snippet_tag.get_text()) if snippet_tag else None,
                position=len(results) + 1,
            ))
            if len(results) >= num:
                break

    return JobResponse(
        query=q, engine="google_jobs", results=results,
        timestamp=get_timestamp(), latency_ms=measure_latency(start),
    )
