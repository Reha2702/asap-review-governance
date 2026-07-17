# 大众点评评论治理分析项目

[在线演示](https://asap-review-governance.streamlit.app/)

基于美团点评开源的 ASAP 中文餐饮评论数据集，覆盖四个业务问题：

- 用户反馈分析：18 个方面的提及量、正负面率和问题集中度
- 内容质量分析：信息量、具体性、反馈维度和表达质量评分
- 风险内容识别：辱骂攻击、广告引流、隐私联系方式、低质灌水
- 审核策略优化：放行、推荐、降权、折叠、人工复核和拦截

## 快速开始

```powershell
python -m pip install -r requirements.txt
python download_data.py
python prepare_data.py
python -m streamlit run app.py
```

应用在首次启动时也会自动下载并处理 ASAP 数据，因此可直接部署到 Streamlit Community Cloud；首次加载预计需要 1-3 分钟。

## 数据口径

ASAP 包含 46,730 条真实大众点评餐饮评论。每条评论包含 1-5 星评分，以及 18 个人工标注的方面情感标签：`1` 正面、`0` 中性、`-1` 负面、`-2` 未提及。

项目新增的质量、风险和审核动作是可解释规则生成的弱标签，不应冒充人工真值。建议从各策略层分层抽取 800-1,200 条评论进行双人标注，形成正式评测集。

## 推荐评估指标

- 风险识别：Precision、Recall、F1、误杀率
- 质量分层：与人工等级的一致率、加权 Kappa
- 审核策略：人工复核率、风险漏放率、优质内容推荐覆盖率
- 用户反馈：18 个方面的提及率、负面率、星级差异

数据来源与许可：[Meituan-Dianping/asap](https://github.com/Meituan-Dianping/asap)，Apache-2.0。
