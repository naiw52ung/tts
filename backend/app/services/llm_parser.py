import json
import re
from dataclasses import dataclass

from openai import OpenAI

from app.core.config import settings


@dataclass
class DropRateInstruction:
    target_keyword: str
    change_percent: int


def _fallback_parse(req_text: str) -> DropRateInstruction:
    percent_match = re.search(r"(-?\d+)\s*%", req_text)
    change_percent = int(percent_match.group(1)) if percent_match else 10
    keyword_match = re.search(r"将(.+?)怪", req_text)
    target = keyword_match.group(1).strip() if keyword_match else "全部"
    return DropRateInstruction(target_keyword=target, change_percent=change_percent)


def parse_drop_requirement(req_text: str) -> DropRateInstruction:
    if not settings.deepseek_api_key:
        return _fallback_parse(req_text)

    client = OpenAI(api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url)
    prompt = (
        "你是传奇爆率指令解析器。输出JSON，字段：target_keyword(字符串), change_percent(整数)。"
        "如果是全局修改，target_keyword写'全部'。"
    )
    try:
        result = client.chat.completions.create(
            model=settings.deepseek_model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": req_text},
            ],
            temperature=0,
        )
        content = result.choices[0].message.content or "{}"
        data = json.loads(content)
        return DropRateInstruction(
            target_keyword=str(data.get("target_keyword", "全部")),
            change_percent=int(data.get("change_percent", 10)),
        )
    except Exception:
        return _fallback_parse(req_text)
