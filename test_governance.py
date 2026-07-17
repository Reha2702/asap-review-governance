import pandas as pd

from governance import ASPECT_NAMES, enrich_reviews


def review(text: str, **aspects: int) -> pd.Series:
    values = {column: -2 for column in ASPECT_NAMES}
    values.update(aspects)
    return enrich_reviews(pd.DataFrame([{"review": text, **values}])).iloc[0]


def test_specific_review_is_valuable() -> None:
    result = review(
        "周六晚排队40分钟，不过服务员会提前说明进度。两人点了三份菜共168元，"
        "口味清淡，分量足，环境也比较安静，建议错峰到店。",
        **{"Service#Queue": -1, "Food#Taste": 1, "Food#Portion": 1, "Ambience#Noise": 1},
    )
    assert result["quality_level"] in {"合格", "优质"}
    assert result["risk_level"] == "正常"
    assert result["audit_action"] in {"正常放行", "放行并推荐"}


def test_advertising_goes_to_manual_review() -> None:
    result = review("优惠代理加我微信 abc12345，长期合作。")
    assert result["risk_level"] == "高风险"
    assert result["audit_action"] == "拦截并人工复核"


def test_abuse_is_folded() -> None:
    result = review("服务员态度太差了，这就是一家垃圾黑店。")
    assert result["risk_level"] == "中风险"
    assert result["audit_action"] == "折叠并人工复核"


def test_spam_is_downranked() -> None:
    result = review("好好好好好好好！！！！")
    assert result["risk_level"] == "低风险"
    assert result["quality_level"] == "低质"
    assert result["audit_action"] == "降权或提醒修改"


if __name__ == "__main__":
    test_specific_review_is_valuable()
    test_advertising_goes_to_manual_review()
    test_abuse_is_folded()
    test_spam_is_downranked()
    print("4 governance checks passed")
