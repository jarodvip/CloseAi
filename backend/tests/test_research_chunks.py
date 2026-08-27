from app.core.domain.services.research_service import split_into_chunks, tokenize_for_fts


def test_split_empty_and_short():
    assert split_into_chunks("") == []
    text = "短文本一段。\n第二段也不长。"
    chunks = split_into_chunks(text, max_chars=500)
    assert len(chunks) == 1
    assert "第二段" in chunks[0]


def test_split_by_max_chars():
    paras = ["甲" * 300, "乙" * 300, "丙" * 100]
    chunks = split_into_chunks("\n".join(paras), max_chars=500)
    # 前两段共600字超500必须分开；第三段与前一块合计400字可合并
    assert len(chunks) == 2
    assert max(len(c.replace("\n", "")) for c in chunks) <= 500


def test_tokenize_chinese():
    result = tokenize_for_fts("奶茶行业竞争激烈")
    assert isinstance(result, str)
    assert " " in result  # 词之间有空格
    tokens = result.split()
    assert "奶茶" in tokens or "行业" in tokens
