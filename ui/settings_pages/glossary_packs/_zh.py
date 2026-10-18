# file: ui/settings_pages/glossary_packs/_zh.py

"""Chinese (Simplified) pack content. See the package docstring for the rules
this data obeys, including the standing note that layer C's *fuzzy* pass is
inert on CJK — these terms reach the user through ASR bias, the LLM block and
the explicit replacement map.

Legal follows PRC practice (民法典 / 民事诉讼法 / 公司法), named in the pack's
note; Taiwan and Hong Kong practice diverges, as does the script.

**No homophone replacements are shipped**, though the CJK failure mode is the
homophone and the map is now able to fix it (``_heard_regex`` no longer demands
a word boundary that Chinese cannot have). Authoring 心电图/新电图-style pairs
demands a native ear to get right, and a wrong pair corrupts text that was
correct. The map here is limited to Latin abbreviations Chinese speakers embed
in speech and write in Latin (CT, K8s) — the one category that can be verified
from outside the language. A user who knows the homophones their dictation hits
can add them by hand, and now they will fire.
"""

from __future__ import annotations

from ._types import PackContent

LOCALE = "zh"

PACKS: dict[str, PackContent] = {
    "legal": PackContent(
        terms=[
            # 诉讼
            "起诉状", "答辩状", "反诉", "代理词", "支付令", "财产保全",
            "诉讼时效", "除斥期间", "举证责任",
            # 合同
            "承揽合同", "要约", "定金", "债权转让", "债务转移", "迟延履行",
            "可得利益损失", "情势变更",
            # 公司
            "尽职调查", "统一社会信用代码",
        ],
        replacements=[],
        note="中国大陆法律术语（民法典、民事诉讼法、公司法）。",
    ),
    "medical": PackContent(
        terms=[
            # 病史 / 查体
            "主诉", "现病史", "既往史", "叩诊", "鉴别诊断", "预后",
            # 症状 / 体征
            "心动过速", "心动过缓", "心律失常", "发绀", "咯血",
            # 检查
            "CT", "X线检查", "活检", "超声心动图",
            # 治疗
            "禁忌症",
            # 解剖
            "近端", "远端",
        ],
        # Latin abbreviations only — see the module docstring on homophones.
        replacements=[
            ("ct", "CT"),
        ],
    ),
    "it": PackContent(
        # Chinese developers speak Chinese and write tool names in Latin — the
        # same split as every other IT pack.
        # Only what speech recognition genuinely gets wrong: jargon, Latin tool
        # names, rare terms. Everyday words of the profession (branch, release,
        # task, database) are left out — the recognizer already knows them, and
        # every term spends a slot of a capped bias list (ElevenLabs: 50).
        terms=[
            # 语音识别容易出错的行话
            "灰度发布", "幂等", "链路追踪",
            # 用拉丁字母书写的工具与流程
            "merge request", "pull request", "commit", "rollback", "hotfix",
            "Kubernetes", "Docker", "PostgreSQL", "Redis", "Kafka", "nginx",
            "Git", "GitLab", "CI/CD", "API",
        ],
        replacements=[
            ("k8s", "Kubernetes"),
            ("kubernetes", "Kubernetes"),
            ("postgres", "PostgreSQL"),
            ("ci cd", "CI/CD"),
        ],
    ),
    "finance": PackContent(
        terms=[
            # 会计
            "权责发生制", "摊销", "计提", "核销",
            # 指标
            "营运资金", "折现率", "净现值", "内部收益率", "EBITDA", "ROI",
            # 资本运作
            "股权稀释", "尽职调查", "托管账户",
            # 税务 / 监管
            "国际财务报告准则",
        ],
        replacements=[
            ("ebitda", "EBITDA"),
            ("roi", "ROI"),
        ],
        note="中国大陆税务与会计术语（增值税、企业所得税）。",
    ),
    "sales": PackContent(
        terms=[
            # 漏斗
            "销售漏斗", "陌生拜访", "概念验证", "丢单", "客单价",
            # 客户关系
            "异议处理", "价值主张", "增购", "交叉销售", "触点",
            # 术语
            "CRM", "KPI", "NPS",
        ],
        replacements=[
            ("crm", "CRM"),
            ("kpi", "KPI"),
            ("nps", "NPS"),
        ],
    ),
}
