"""外部数据服务：摄取、检索、背调。所有文本入库前必经此处，保证来源可追溯。"""
from typing import Dict, List, Optional, Tuple


def split_into_chunks(text: str, max_chars: int = 500) -> List[str]:
    """按段落聚合成 ~max_chars 的块；单段超长时硬切"""
    if not text or not text.strip():
        return []
    chunks: List[str] = []
    buf = ""
    for para in [p.strip() for p in text.split("\n") if p.strip()]:
        while len(para) > max_chars:
            if buf:
                chunks.append(buf)
                buf = ""
            chunks.append(para[:max_chars])
            para = para[max_chars:]
        if len(buf) + len(para) + 1 > max_chars and buf:
            chunks.append(buf)
            buf = para
        else:
            buf = f"{buf}\n{para}" if buf else para
    if buf:
        chunks.append(buf)
    return chunks


def tokenize_for_fts(text: str) -> str:
    """jieba 预分词：索引写入与查询两侧必须使用同一实现"""
    import jieba

    jieba.setLogLevel(60)  # 关闭构建日志刷屏
    return " ".join(jieba.cut(text or ""))
