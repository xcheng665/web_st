"""Create per-paper reference notes and refresh the reference zip package."""

from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "references"
PAPERS_DIR = OUT / "paper_notes"
PACKAGE = OUT / "building_code_compliance_references_2021_2026.zip"


def clean_filename(text: str, max_len: int = 96) -> str:
    text = re.sub(r"[^\w\-.() ]+", "_", text, flags=re.UNICODE).strip()
    text = re.sub(r"\s+", "_", text)
    return text[:max_len].strip("._") or "paper"


def main() -> None:
    rows = json.loads((OUT / "references.json").read_text(encoding="utf-8"))
    PAPERS_DIR.mkdir(parents=True, exist_ok=True)
    for existing in PAPERS_DIR.glob("*.md"):
        existing.unlink()

    for row in rows:
        idx = int(row["index"])
        title = row["title"]
        filename = f"{idx:02d}_{row['year']}_{clean_filename(title)}.md"
        path = PAPERS_DIR / filename
        abstract = row.get("abstract") or "无摘要。"
        doi = row.get("doi") or ""
        doi_url = f"https://doi.org/{doi}" if doi else ""
        lines = [
            f"# {idx}. {title}",
            "",
            f"- 年份：{row.get('year') or ''}",
            f"- 来源：{row.get('venue') or '未标明'}",
            f"- 作者：{row.get('authors') or '未标明'}",
            f"- DOI：{doi or '无'}",
            f"- DOI 链接：{doi_url or '无'}",
            f"- OpenAlex：{row.get('url') or '无'}",
            f"- 开放 PDF 链接：{row.get('pdf_url') or '未发现'}",
            f"- 本地 PDF：{row.get('local_pdf') or '未下载'}",
            f"- 下载状态：{row.get('download_status') or ''}",
            f"- 引用次数（OpenAlex）：{row.get('citation_count') or 0}",
            f"- 检索 query：{row.get('source_query') or ''}",
            "",
            "## 摘要",
            "",
            abstract,
            "",
            "## 与本论文的关系",
            "",
            "该文献被纳入“BIM/建筑规范自动合规审查、规范文本语义解析、知识图谱或 LLM 辅助规则抽取”方向的近五年参考文献包。写作时可根据其方法侧重点分别归入 Related Work 中的 ACC、NLP/LLM 规范解析、语义/本体/知识图谱或 BIM-IFC 合规检查小节。",
            "",
        ]
        path.write_text("\n".join(lines), encoding="utf-8")

    with (OUT / "README_zh.md").open("w", encoding="utf-8") as fh:
        pdf_count = sum(1 for row in rows if row.get("download_status") == "downloaded_open_access_pdf")
        fh.write("# 参考文献文件包说明\n\n")
        fh.write(f"- 主题：BIM/工程信息化自动规范合规审查、建筑规范知识图谱、LLM/NLP 规范解析。\n")
        fh.write(f"- 时间范围：2021–2026。\n")
        fh.write(f"- 文献数量：{len(rows)} 篇。\n")
        fh.write(f"- 已自动下载开放 PDF：{pdf_count} 篇。\n")
        fh.write("- 其余文献：提供 DOI、OpenAlex 页面、开放 PDF 链接状态、摘要和单篇 Markdown 参考文件。\n")
        fh.write("- 注意：未下载全文的论文并非无关，而是出版方未提供可自动抓取的开放 PDF，或站点禁止命令行下载；请通过 DOI/学校数据库/期刊官网获取。\n\n")
        fh.write("## 文件结构\n\n")
        fh.write("- `reference_list_zh.md`：20 篇总览。\n")
        fh.write("- `references.csv` / `references.json`：结构化清单。\n")
        fh.write("- `references.bib`：BibTeX 引用。\n")
        fh.write("- `paper_notes/`：每篇一份中文参考笔记。\n")
        fh.write("- `pdfs/`：成功下载的开放获取 PDF。\n")

    with zipfile.ZipFile(PACKAGE, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file in OUT.rglob("*"):
            if file == PACKAGE:
                continue
            if file.is_file():
                zf.write(file, file.relative_to(OUT))

    print(PACKAGE)


if __name__ == "__main__":
    main()
