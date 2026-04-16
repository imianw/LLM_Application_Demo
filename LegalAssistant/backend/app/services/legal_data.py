import json
import math
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class LegalClause:
    id: str
    title: str
    law_name: str
    article: str
    source_file: str
    content: str


def load_legal_clauses(data_file: Path) -> list[LegalClause]:
    if not data_file.exists():
        raise FileNotFoundError(
            f"未找到法律数据文件: {data_file}. 请先准备 data/all_legal_clauses.json。"
        )

    raw = json.loads(data_file.read_text(encoding="utf-8"))
    clauses: list[LegalClause] = []

    for item in raw:
        if not isinstance(item, dict):
            continue

        for title, content in item.items():
            parts = title.split(" ", 1)
            law_name = parts[0] if parts else "未知法律"
            article = parts[1] if len(parts) > 1 else "未知条款"
            source_file = "all_legal_clauses.json"
            clauses.append(
                LegalClause(
                    id=f"{source_file}::{title}",
                    title=title,
                    law_name=law_name,
                    article=article,
                    source_file=source_file,
                    content=content.strip(),
                )
            )

    return clauses


def cosine_similarity(left: list[float], right: list[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)
