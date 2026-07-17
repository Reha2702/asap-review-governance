from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from governance import ASPECT_NAMES, detect_aspect_columns, enrich_reviews
from download_data import main as download_data
from prepare_data import main as prepare_data


st.set_page_config(page_title="大众点评评论治理分析台", layout="wide")

style_path = Path(__file__).parent / "style.css"
st.markdown(f"<style>{style_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

COLORS = {"red": "#C43D35", "green": "#1D7A5B", "yellow": "#D49A25", "ink": "#222222"}


@st.cache_data
def load_data() -> pd.DataFrame:
    path = Path(__file__).parent / "data" / "processed" / "reviews_enriched.csv"
    if not path.exists():
        with st.spinner("首次启动：正在下载并处理 ASAP 数据，预计需要 1-3 分钟..."):
            download_data()
            prepare_data()
    return pd.read_csv(path)


def aspect_summary(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for column in detect_aspect_columns(frame):
        mentioned = frame.loc[frame[column] != -2, column]
        if mentioned.empty:
            continue
        rows.append({"方面": ASPECT_NAMES[column], "提及量": len(mentioned), "负面率": (mentioned == -1).mean(), "正面率": (mentioned == 1).mean()})
    return pd.DataFrame(rows).sort_values("提及量", ascending=False)


data = load_data()
if data.empty:
    st.error("数据准备失败，请刷新页面后重试。")
    st.stop()

st.markdown(
    f"""
    <header class="archive-topbar">
      <div class="archive-brand"><span class="archive-brand-mark">评</span><span>评鉴志</span><small>中文评论治理档案库</small></div>
      <div class="dataset-status"><span class="status-dot"></span>ASAP 数据集已载入 <strong>{len(data):,}</strong> 条评论</div>
    </header>
    <section class="archive-intro">
      <p class="archive-eyebrow">REVIEW GOVERNANCE ARCHIVE</p>
      <h1>从一条评论，看见体验与风险</h1>
      <p>整理真实餐饮反馈，识别内容价值、用户问题与审核风险。</p>
    </section>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("评论检索")
    st.caption("按业务口径缩小分析范围")
    star_column = next((c for c in ("star", "rating", "stars") if c in data.columns), None)
    if star_column:
        stars = sorted(data[star_column].dropna().unique().tolist())
        selected_stars = st.multiselect("星级", stars, default=stars)
    else:
        selected_stars = []
    selected_risk = st.multiselect("风险等级", data["risk_level"].dropna().unique(), default=data["risk_level"].dropna().unique())
    selected_quality = st.multiselect("内容质量", data["quality_level"].dropna().unique(), default=data["quality_level"].dropna().unique())
    keyword = st.text_input("评论关键词")

filtered = data[data["risk_level"].isin(selected_risk) & data["quality_level"].isin(selected_quality)].copy()
if star_column and selected_stars:
    filtered = filtered[filtered[star_column].isin(selected_stars)]
if keyword:
    filtered = filtered[filtered["review_text"].str.contains(keyword, case=False, na=False)]

total = len(filtered)
risky = (filtered["risk_level"] != "正常").sum()
excellent = (filtered["quality_level"] == "优质").sum()
review_required = filtered["audit_action"].str.contains("复核").sum()

metrics = st.columns(4)
metrics[0].metric("评论量", f"{total:,}")
metrics[1].metric("风险命中率", f"{risky / total:.1%}" if total else "0%")
metrics[2].metric("优质内容率", f"{excellent / total:.1%}" if total else "0%")
metrics[3].metric("人工复核量", f"{review_required:,}")

st.markdown('<div class="section-index"><span>01</span><strong>治理分析</strong></div>', unsafe_allow_html=True)
feedback_tab, quality_tab, risk_tab, strategy_tab, explorer_tab = st.tabs(["用户反馈", "内容质量", "风险识别", "审核策略", "评论明细"])

with feedback_tab:
    summary = aspect_summary(filtered)
    left, right = st.columns(2)
    left.plotly_chart(px.bar(summary.head(12), x="提及量", y="方面", orientation="h", title="用户最关注的体验维度", color_discrete_sequence=[COLORS["green"]]).update_layout(yaxis={"categoryorder": "total ascending"}), use_container_width=True)
    right.plotly_chart(px.bar(summary.sort_values("负面率", ascending=False).head(12), x="负面率", y="方面", orientation="h", title="负面反馈集中维度", color_discrete_sequence=[COLORS["red"]]).update_layout(yaxis={"categoryorder": "total ascending"}, xaxis_tickformat=".0%"), use_container_width=True)
    st.dataframe(summary, use_container_width=True, hide_index=True)

with quality_tab:
    left, right = st.columns(2)
    left.plotly_chart(px.histogram(filtered, x="quality_score", color="quality_level", nbins=20, title="评论质量得分分布", color_discrete_map={"优质": COLORS["green"], "合格": COLORS["yellow"], "低质": COLORS["red"]}), use_container_width=True)
    quality_counts = filtered["quality_level"].value_counts().rename_axis("质量").reset_index(name="评论量")
    right.plotly_chart(px.pie(quality_counts, values="评论量", names="质量", hole=0.58, title="质量分层", color="质量", color_discrete_map={"优质": COLORS["green"], "合格": COLORS["yellow"], "低质": COLORS["red"]}), use_container_width=True)
    st.dataframe(filtered.nsmallest(30, "quality_score")[["review_text", "quality_score", "quality_level", "quality_reasons"]], use_container_width=True, hide_index=True)

with risk_tab:
    risk_data = filtered[filtered["risk_level"] != "正常"]
    counts = risk_data["risk_types"].value_counts().rename_axis("风险类型").reset_index(name="命中量")
    st.plotly_chart(px.bar(counts, x="风险类型", y="命中量", title="规则命中分布", color_discrete_sequence=[COLORS["red"]]), use_container_width=True)
    st.dataframe(risk_data[["review_text", "risk_level", "risk_types", "risk_reason", "audit_action"]].head(100), use_container_width=True, hide_index=True)

with strategy_tab:
    matrix = pd.crosstab(filtered["risk_level"], filtered["audit_action"]).reset_index()
    st.subheader("当前审核动作分布")
    st.dataframe(matrix, use_container_width=True, hide_index=True)
    action_counts = filtered["audit_action"].value_counts().rename_axis("审核动作").reset_index(name="评论量")
    st.plotly_chart(px.bar(action_counts, x="审核动作", y="评论量", color="审核动作", title="策略模拟结果"), use_container_width=True)
    st.info("当前版本为可解释规则基线。上线前应抽样人工标注，计算准确率、召回率和误杀率，再调整阈值。")

with explorer_tab:
    search_columns = ["review_text", *([star_column] if star_column else []), "quality_score", "quality_level", "risk_level", "risk_types", "audit_action"]
    st.dataframe(filtered[search_columns].head(500), use_container_width=True, hide_index=True)

st.divider()
st.markdown('<div class="section-index"><span>02</span><strong>单条评论即时诊断</strong></div>', unsafe_allow_html=True)
sample_text = st.text_area("输入评论", "味道不错，但是服务员态度很差，排队四十分钟。")
if st.button("分析这条评论", type="primary"):
    row = {column: -2 for column in ASPECT_NAMES}
    preview = pd.DataFrame([{"review": sample_text, **row}])
    result = enrich_reviews(preview).iloc[0]
    st.json({"质量得分": int(result["quality_score"]), "质量等级": result["quality_level"], "质量依据": result["quality_reasons"], "风险等级": result["risk_level"], "风险类型": result["risk_types"], "审核动作": result["audit_action"]}, expanded=True)
