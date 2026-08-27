import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from scripts.import_docs import parse_any, read_docx  # noqa: E402


def _make_docx(tmp_path: Path) -> Path:
    from docx import Document

    doc = Document()
    doc.add_paragraph("第一段：气泡水行业景气度高。" )
    doc.add_paragraph("第二段：" + "渠道下沉" * 150)
    p = tmp_path / "sample.docx"
    doc.save(str(p))
    return p


def test_read_docx(tmp_path):
    p = _make_docx(tmp_path)
    text = read_docx(p)
    assert "气泡水行业景气度高" in text
    assert "渠道下沉" in text


def test_parse_any_dispatch_and_bad_file(tmp_path):
    p = _make_docx(tmp_path)
    assert "气泡水" in parse_any(p)
    bad = tmp_path / "broken.docx"
    bad.write_bytes(b"not-a-real-docx")
    assert parse_any(bad) == ""  # 解析失败返回空串而非抛出


def test_parse_unsupported_ext(tmp_path):
    f = tmp_path / "x.exe"
    f.write_bytes(b"\x00")
    assert parse_any(f) == ""
