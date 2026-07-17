import re
from dataclasses import dataclass

import pandas as pd


ASPECT_NAMES = {
    "Location#Transportation": "位置交通",
    "Location#Downtown": "商圈便利",
    "Location#Easy_to_find": "是否易找",
    "Service#Queue": "排队等位",
    "Service#Hospitality": "服务态度",
    "Service#Parking": "停车服务",
    "Service#Timely": "上菜速度",
    "Price#Level": "价格水平",
    "Price#Cost_effective": "性价比",
    "Price#Discount": "优惠活动",
    "Ambience#Decoration": "装修",
    "Ambience#Noise": "噪声",
    "Ambience#Space": "空间",
    "Ambience#Sanitary": "卫生",
    "Food#Portion": "菜量",
    "Food#Taste": "口味",
    "Food#Appearance": "菜品外观",
    "Food#Recommend": "菜品推荐",
}

RISK_PATTERNS = {
    "辱骂攻击": re.compile(r"垃圾|傻[逼比]|脑残|去死|妈的|操你|恶心死|黑店"),
    "广告引流": re.compile(
        r"加(?:我|微|微信)|vx|v信|薇信|联系(?:电话|我)|代理|兼职|刷单|"
        r"(?:qq|QQ)[:：]?\s*\d{5,}|1[3-9]\d{9}"
    ),
    "隐私联系方式": re.compile(
        r"(?:电话|手机|微信|vx|qq|QQ)[:：]?\s*[A-Za-z0-9_-]{5,}|1[3-9]\d{9}"
    ),
}

GENERIC_TEXT = re.compile(r"^(好|很好|不错|一般|差|很差|满意|不满意|还行|可以)[！!。.]*$")
REPEATED_CHAR = re.compile(r"(.)\1{5,}")
EXCESSIVE_PUNCT = re.compile(r"[!！?？]{4,}")


@dataclass
class GovernanceResult:
    quality_score: int
    quality_level: str
    quality_reasons: str
    risk_level: str
    risk_types: str
    risk_reason: str
    audit_action: str


def detect_aspect_columns(df: pd.DataFrame) -> list[str]:
    return [column for column in ASPECT_NAMES if column in df.columns]


def analyze_review(text: object, row: pd.Series, aspect_columns: list[str]) -> GovernanceResult:
    content = "" if pd.isna(text) else str(text).strip()
    length = len(content)
    mentioned = sum(row.get(column, -2) != -2 for column in aspect_columns)
    reasons: list[str] = []
    score = 30

    if length >= 100:
        score += 22
        reasons.append("信息充分")
    elif length >= 40:
        score += 15
        reasons.append("长度适中")
    elif length >= 15:
        score += 8
    else:
        score -= 12
        reasons.append("文本过短")

    score += min(mentioned * 5, 25)
    if mentioned >= 3:
        reasons.append(f"覆盖{mentioned}个体验维度")
    elif mentioned == 0:
        score -= 15
        reasons.append("未形成明确反馈维度")

    if re.search(r"因为|但是|不过|所以|尤其|比如|而且|虽然|建议|希望", content):
        score += 8
        reasons.append("包含原因或建议")
    if re.search(r"\d+(?:\.\d+)?(?:元|分钟|小时|人|份|次|折)", content):
        score += 6
        reasons.append("包含可验证细节")
    if GENERIC_TEXT.fullmatch(content):
        score -= 20
        reasons.append("泛化评价")
    if REPEATED_CHAR.search(content):
        score -= 12
        reasons.append("字符重复")

    risk_types = [name for name, pattern in RISK_PATTERNS.items() if pattern.search(content)]
    if REPEATED_CHAR.search(content) or EXCESSIVE_PUNCT.search(content):
        risk_types.append("低质灌水")

    if "广告引流" in risk_types or "隐私联系方式" in risk_types:
        risk_level = "高风险"
        risk_reason = "命中联系方式或站外引流规则"
    elif "辱骂攻击" in risk_types:
        risk_level = "中风险"
        risk_reason = "命中人身攻击或侮辱表达规则"
    elif "低质灌水" in risk_types:
        risk_level = "低风险"
        risk_reason = "命中重复字符或异常标点规则"
    else:
        risk_level = "正常"
        risk_reason = "未命中当前风险规则"

    score = max(0, min(100, score))
    quality_level = "优质" if score >= 86 else "合格" if score >= 55 else "低质"

    if risk_level == "高风险":
        action = "拦截并人工复核"
    elif risk_level == "中风险":
        action = "折叠并人工复核"
    elif risk_level == "低风险" or quality_level == "低质":
        action = "降权或提醒修改"
    elif quality_level == "优质":
        action = "放行并推荐"
    else:
        action = "正常放行"

    return GovernanceResult(
        quality_score=score,
        quality_level=quality_level,
        quality_reasons="、".join(reasons) or "基础有效评论",
        risk_level=risk_level,
        risk_types="、".join(dict.fromkeys(risk_types)) or "无",
        risk_reason=risk_reason,
        audit_action=action,
    )


def enrich_reviews(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    text_column = next(
        (column for column in ("review", "text", "content") if column in result.columns),
        None,
    )
    if text_column is None:
        raise ValueError("数据中未找到评论文本列（review/text/content）")

    aspects = detect_aspect_columns(result)
    analyzed = [
        analyze_review(text, row, aspects)
        for text, (_, row) in zip(result[text_column], result.iterrows())
    ]
    extra = pd.DataFrame([item.__dict__ for item in analyzed], index=result.index)
    result["review_text"] = result[text_column].astype(str)
    return pd.concat([result, extra], axis=1)
