"""存量 PDF/Word 批量导入脚本（容错：单文件失败不中断批量）"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from app.db.session import SessionLocal  # noqa: E402
from app.core.domain.services.research_service import ingest_text  # noqa: E402


def read_pdf(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def read_docx(path: Path) -> str:
    from docx import Document

    doc = Document(str(path))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def parse_any(path: Path) -> str:
    """按扩展名分发解析；任何失败都返回空串"""
    suffix = path.suffix.lower()
    try:
        if suffix == ".pdf":
            return read_pdf(path)
        if suffix in {".docx"}:
            return read_docx(path)
        return ""
    except Exception:
        print(f"[warn] 解析失败: {path}")
        return ""


def main(argv=None):
    parser = argparse.ArgumentParser(description="批量导入 PDF/Word 到外部数据层")
    parser.add_argument("path", help="文件或目录")
    parser.add_argument("--industry", default=None, help="行业标签")
    parser.add_argument("--source-name", dest="source_name", default=None, help="来源名称")
    parser.add_argument("--max-chars", type=int, default=500)
    args = parser.parse_args(argv)

    root = Path(args.path)
    files = sorted(root.rglob("*")) if root.is_dir() else [root]
    total = 0
    ok_files = 0
    db = SessionLocal()
    try:
        for f in files:
            if not f.is_file() or f.suffix.lower() not in {".pdf", ".docx"}:
                continue
            text = parse_any(f)
            if not text:
                continue
            made = ingest_text(db, text, source_type="doc", title=f.stem,
                               source_name=args.source_name or f.parent.name,
                               industry=args.industry)
            total += len(made)
            ok_files += 1
            print(f"[ok] {f.name}: {len(made)} chunks")
    finally:
        db.close()
    print(f"完成：{ok_files} 个文件，共 {total} 个文本块")


if __name__ == "__main__":
    main()
