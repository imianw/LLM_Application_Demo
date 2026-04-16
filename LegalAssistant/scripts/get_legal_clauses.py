import json
import os
import re

import requests
from bs4 import BeautifulSoup


URLS = [
    ("中华人民共和国劳动法", "https://www.cnr.cn/kby/zl/200704/t20070402_504433347.html"),
    ("中华人民共和国劳动合同法", "https://www.sdcourt.gov.cn/dzlyfy/392638/566553/653412/index.html"),
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


def extract_legal_clauses(law_name: str, url: str) -> dict[str, str]:
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    response.encoding = response.apparent_encoding
    soup = BeautifulSoup(response.text, "html.parser")

    legal_clauses: dict[str, str] = {}
    current_clause = None
    current_content: list[str] = []

    for text in soup.stripped_strings:
        if re.match(r"^第[一二三四五六七八九十百零]+章", text):
            continue

        if any(
            keyword in text
            for keyword in [
                "版权所有",
                "技术支持",
                "京ICP备",
                "京公网安备",
                "Produced By",
                "地址：",
                "电话：",
                "扫一扫",
                "责任编辑",
                "相关链接",
                "网站地图",
                "联系我们",
                "主办单位",
                "网站标识码",
            ]
        ):
            continue

        match = re.match(r"^第([一二三四五六七八九十百零]+)条", text)
        if match:
            if current_clause and current_content:
                legal_clauses[current_clause] = " ".join(current_content).strip()

            clause_number = match.group(1)
            current_clause = f"{law_name} 第{clause_number}条"
            content = text[text.find("条") + 1 :].strip()
            current_content = [content] if content else []
            continue

        if current_clause:
            current_content.append(text)

    if current_clause and current_content:
        legal_clauses[current_clause] = " ".join(current_content).strip()

    return legal_clauses


def main() -> None:
    output_dir = "data"
    os.makedirs(output_dir, exist_ok=True)

    all_results = []
    for law_name, url in URLS:
        print(f"正在抓取: {law_name} ...")
        clauses = extract_legal_clauses(law_name, url)
        all_results.append(clauses)
        print(f"{law_name} 共提取 {len(clauses)} 条法律条款。")

    output_file = os.path.join(output_dir, "all_legal_clauses.json")
    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(all_results, file, ensure_ascii=False, indent=2)

    print(f"全部抓取完成，结果已保存到 {output_file}")


if __name__ == "__main__":
    main()
