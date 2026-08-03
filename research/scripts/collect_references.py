"""Collect recent references for the SCI manuscript package.

The script searches OpenAlex public metadata, filters recent papers around
BIM/building-code compliance checking, downloads legally advertised open-access
PDFs when available, and writes a reproducible reference package.
"""

from __future__ import annotations

import csv
import json
import re
import ssl
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "references"
PDF_DIR = OUT / "pdfs"
PACKAGE = OUT / "building_code_compliance_references_2021_2026.zip"

YEAR_MIN = 2021
YEAR_MAX = 2026

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0 Safari/537.36"
    ),
    "Accept": "application/pdf,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
}

INSECURE_DOWNLOAD_CONTEXT = ssl._create_unverified_context()

QUERIES = [
    "automated compliance checking BIM building code",
    "automated code compliance checking building regulations BIM",
    "building code compliance checking BIM knowledge graph",
    "BIM regulatory compliance checking knowledge graph",
    "natural language processing building regulations automated compliance checking",
    "large language model building code compliance checking",
    "information extraction building codes BIM compliance",
    "semantic rule checking building code BIM",
]

MUST_KEYWORDS = {
    "bim",
    "building information modeling",
    "building information modelling",
    "building code",
    "building codes",
    "building regulation",
    "building regulations",
    "code compliance",
    "compliance checking",
    "automated compliance",
    "regulatory compliance",
    "knowledge graph",
    "rule checking",
}

BOOST_KEYWORDS = {
    "ifc": 4,
    "ontology": 3,
    "semantic": 3,
    "knowledge graph": 6,
    "natural language processing": 5,
    "large language model": 5,
    "llm": 4,
    "rule extraction": 5,
    "automated compliance checking": 8,
    "code compliance checking": 8,
    "bim": 6,
    "building code": 6,
    "building regulation": 6,
}


@dataclass
class Paper:
    title: str
    year: int
    authors: list[str]
    venue: str = ""
    abstract: str = ""
    doi: str = ""
    url: str = ""
    semantic_scholar_id: str = ""
    citation_count: int = 0
    pdf_url: str = ""
    source_query: str = ""
    score: int = 0
    download_status: str = "not_attempted"
    local_pdf: str = ""
    notes: list[str] = field(default_factory=list)

    @property
    def key(self) -> str:
        if self.doi:
            return self.doi.lower().replace("https://doi.org/", "")
        return re.sub(r"\W+", "", self.title.lower())[:120]


def clean_filename(text: str, max_len: int = 120) -> str:
    text = re.sub(r"[^\w\-.() ]+", "_", text, flags=re.UNICODE).strip()
    text = re.sub(r"\s+", "_", text)
    return text[:max_len].strip("._") or "paper"


def relevance_score(item: dict[str, Any], query: str) -> int:
    text = " ".join(
        [
            item.get("title") or "",
            item.get("abstract") or "",
            item.get("venue") or "",
            " ".join((item.get("fieldsOfStudy") or [])),
        ]
    ).lower()
    score = 0
    for kw in MUST_KEYWORDS:
        if kw in text:
            score += 3
    for kw, value in BOOST_KEYWORDS.items():
        if kw in text:
            score += value
    if "building" in text and ("compliance" in text or "regulation" in text or "code" in text):
        score += 8
    if "bim" in text and ("compliance" in text or "checking" in text):
        score += 8
    if "large language" in query and ("llm" in text or "large language" in text):
        score += 5
    score += min(int(item.get("citationCount") or 0), 50) // 10
    return score


def http_json(url: str, params: dict[str, str | int], timeout: int = 30) -> dict[str, Any]:
    from urllib.parse import urlencode

    full_url = f"{url}?{urlencode(params)}"
    request = Request(full_url, headers=HEADERS)
    for attempt in range(4):
        try:
            with urlopen(request, timeout=timeout) as response:
                data = response.read()
            return json.loads(data.decode("utf-8"))
        except HTTPError as exc:
            if exc.code == 429 and attempt < 3:
                time.sleep(3 * (attempt + 1))
                continue
            raise
    raise RuntimeError("unreachable retry state")


def abstract_from_openalex(index: dict[str, list[int]] | None) -> str:
    if not index:
        return ""
    positions: list[tuple[int, str]] = []
    for word, locs in index.items():
        for loc in locs:
            positions.append((loc, word))
    return " ".join(word for _, word in sorted(positions))


def search_openalex() -> dict[str, Paper]:
    endpoint = "https://api.openalex.org/works"
    seen: dict[str, Paper] = {}
    for query in QUERIES:
        params = {
            "search": query,
            "filter": f"from_publication_date:{YEAR_MIN}-01-01,to_publication_date:{YEAR_MAX}-12-31",
            "per-page": 50,
            "sort": "relevance_score:desc",
        }
        payload = http_json(endpoint, params)
        for item in payload.get("results", []):
            year = item.get("publication_year")
            if not isinstance(year, int) or year < YEAR_MIN or year > YEAR_MAX:
                continue
            title = (item.get("title") or "").strip()
            if not title:
                continue
            primary = item.get("primary_location") or {}
            source = primary.get("source") or {}
            best_oa = item.get("best_oa_location") or {}
            abstract = abstract_from_openalex(item.get("abstract_inverted_index"))
            score = relevance_score(
                {
                    "title": title,
                    "abstract": abstract,
                    "venue": source.get("display_name") or "",
                    "fieldsOfStudy": [c.get("display_name", "") for c in item.get("concepts", [])],
                    "citationCount": item.get("cited_by_count") or 0,
                },
                query,
            )
            if score < 14:
                continue
            authors = []
            for authorship in item.get("authorships") or []:
                author = authorship.get("author") or {}
                if author.get("display_name"):
                    authors.append(author["display_name"])
            pdf = best_oa.get("pdf_url") or primary.get("pdf_url") or ""
            paper = Paper(
                title=title,
                year=year,
                authors=authors,
                venue=source.get("display_name") or "",
                abstract=abstract,
                doi=(item.get("doi") or "").replace("https://doi.org/", ""),
                url=item.get("id") or "",
                semantic_scholar_id="",
                citation_count=int(item.get("cited_by_count") or 0),
                pdf_url=pdf,
                source_query=query,
                score=score,
            )
            existing = seen.get(paper.key)
            if existing is None or paper.score > existing.score:
                seen[paper.key] = paper
        time.sleep(1.1)

    return seen


def download_pdf(paper: Paper, index: int) -> None:
    if not paper.pdf_url:
        paper.download_status = "no_open_access_pdf_advertised"
        return
    parsed = urlparse(paper.pdf_url)
    if parsed.scheme not in {"http", "https"}:
        paper.download_status = "invalid_pdf_url"
        return
    stem = clean_filename(f"{index:02d}_{paper.year}_{paper.title}")
    path = PDF_DIR / f"{stem}.pdf"
    try:
        request = Request(paper.pdf_url, headers={**HEADERS, "Referer": paper.pdf_url})
        with urlopen(request, timeout=45, context=INSECURE_DOWNLOAD_CONTEXT) as response, path.open("wb") as fh:
            content_type = response.headers.get("content-type", "").lower()
            first = b""
            while True:
                chunk = response.read(65536)
                if not chunk:
                    break
                if not first:
                    first = chunk[:8]
                fh.write(chunk)
        if path.stat().st_size < 10_000:
            path.unlink(missing_ok=True)
            paper.download_status = "downloaded_file_too_small"
            return
        if "pdf" not in content_type and not first.startswith(b"%PDF"):
            path.unlink(missing_ok=True)
            paper.download_status = f"not_a_pdf: content-type={content_type or 'unknown'}"
            return
        paper.download_status = "downloaded_open_access_pdf"
        paper.local_pdf = str(path.relative_to(OUT)).replace("\\", "/")
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        path.unlink(missing_ok=True)
        paper.download_status = f"download_failed: {type(exc).__name__}: {exc}"


def citation_apa(paper: Paper) -> str:
    authors = paper.authors[:6]
    if not authors:
        author_text = "Unknown author"
    elif len(paper.authors) > 6:
        author_text = ", ".join(authors) + ", et al."
    else:
        author_text = ", ".join(authors)
    doi = f" https://doi.org/{paper.doi}" if paper.doi else f" {paper.url}" if paper.url else ""
    venue = f" {paper.venue}." if paper.venue else ""
    return f"{author_text} ({paper.year}). {paper.title}.{venue}{doi}".strip()


def write_outputs(papers: list[Paper]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    PDF_DIR.mkdir(parents=True, exist_ok=True)

    rows = []
    for idx, paper in enumerate(papers, start=1):
        rows.append(
            {
                "index": idx,
                "title": paper.title,
                "year": paper.year,
                "authors": "; ".join(paper.authors),
                "venue": paper.venue,
                "doi": paper.doi,
                "url": paper.url,
                "pdf_url": paper.pdf_url,
                "local_pdf": paper.local_pdf,
                "download_status": paper.download_status,
                "citation_count": paper.citation_count,
                "relevance_score": paper.score,
                "source_query": paper.source_query,
                "abstract": paper.abstract,
                "notes": " | ".join(paper.notes),
            }
        )

    with (OUT / "references.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    with (OUT / "references.json").open("w", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False, indent=2)

    with (OUT / "references.bib").open("w", encoding="utf-8") as fh:
        for idx, paper in enumerate(papers, start=1):
            key = f"ref{idx:02d}_{paper.year}"
            fh.write(f"@article{{{key},\n")
            fh.write(f"  title = {{{paper.title}}},\n")
            fh.write(f"  year = {{{paper.year}}},\n")
            if paper.authors:
                fh.write(f"  author = {{{' and '.join(paper.authors)}}},\n")
            if paper.venue:
                fh.write(f"  journal = {{{paper.venue}}},\n")
            if paper.doi:
                fh.write(f"  doi = {{{paper.doi}}},\n")
            if paper.url:
                fh.write(f"  url = {{{paper.url}}},\n")
            fh.write("}\n\n")

    with (OUT / "reference_list_zh.md").open("w", encoding="utf-8") as fh:
        fh.write("# 近五年相关领域参考文献包\n\n")
        fh.write("检索主题：BIM/工程信息化自动规范合规审查、建筑规范知识图谱、规范文本信息抽取、LLM/NLP 辅助规范解析。\n\n")
        fh.write("说明：仅下载论文页面明确提供的开放获取 PDF；未下载项保留 DOI/论文页链接，避免使用非授权全文来源。\n\n")
        for idx, paper in enumerate(papers, start=1):
            fh.write(f"## {idx}. {paper.title}\n\n")
            fh.write(f"- 年份：{paper.year}\n")
            fh.write(f"- 期刊/会议：{paper.venue or '未标明'}\n")
            fh.write(f"- 作者：{'; '.join(paper.authors[:8]) or '未标明'}\n")
            fh.write(f"- DOI：{paper.doi or '无'}\n")
            fh.write(f"- 论文页：{paper.url or '无'}\n")
            fh.write(f"- 开放 PDF：{paper.pdf_url or '未发现'}\n")
            fh.write(f"- 本地文件：{paper.local_pdf or '未下载'}\n")
            fh.write(f"- 下载状态：{paper.download_status}\n")
            fh.write(f"- APA：{citation_apa(paper)}\n")
            if paper.abstract:
                abstract = paper.abstract.replace("\n", " ")
                fh.write(f"- 摘要摘录：{abstract[:700]}{'…' if len(abstract) > 700 else ''}\n")
            fh.write("\n")

    with zipfile.ZipFile(PACKAGE, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file in OUT.rglob("*"):
            if file == PACKAGE:
                continue
            if file.is_file():
                zf.write(file, file.relative_to(OUT))


def main() -> None:
    papers_by_key = search_openalex()
    ranked = sorted(
        papers_by_key.values(),
        key=lambda p: (p.score, bool(p.pdf_url), p.citation_count, p.year),
        reverse=True,
    )
    selected = ranked[:20]
    if len(selected) < 20:
        raise SystemExit(f"Only found {len(selected)} papers after filtering.")

    OUT.mkdir(parents=True, exist_ok=True)
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    for idx, paper in enumerate(selected, start=1):
        download_pdf(paper, idx)
        time.sleep(0.6)

    write_outputs(selected)
    print(json.dumps(
        {
            "selected": len(selected),
            "downloaded_pdfs": sum(p.download_status == "downloaded_open_access_pdf" for p in selected),
            "package": str(PACKAGE),
        },
        ensure_ascii=False,
        indent=2,
    ))


if __name__ == "__main__":
    main()
