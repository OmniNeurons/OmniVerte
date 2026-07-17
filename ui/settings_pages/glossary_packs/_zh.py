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
            "起诉状", "答辩状", "反诉", "代理词", "上诉", "再审", "裁定",
            "判决", "支付令", "财产保全", "诉讼费用", "管辖权", "诉讼时效",
            "除斥期间", "司法鉴定", "原告", "被告", "第三人", "仲裁",
            "仲裁裁决", "强制执行", "举证责任", "送达", "开庭审理",
            # 合同
            "买卖合同", "租赁合同", "承揽合同", "服务合同", "要约", "承诺",
            "违约金", "定金", "保证", "担保", "债权转让", "债务转移",
            "解除合同", "违约", "迟延履行", "不可抗力", "损害赔偿",
            "可得利益损失", "授权委托书", "诚实信用原则", "质量保证",
            "情势变更",
            # 公司
            "公司章程", "股东会", "董事会", "法定代表人", "注册资本",
            "股权", "有限责任公司", "股份有限公司", "营业执照",
            "尽职调查", "统一社会信用代码", "民法典", "公司法",
        ],
        replacements=[],
        note="中国大陆法律术语（民法典、民事诉讼法、公司法）。",
    ),
    "medical": PackContent(
        terms=[
            # 病史 / 查体
            "主诉", "现病史", "既往史", "家族史", "体格检查", "听诊",
            "触诊", "叩诊", "鉴别诊断", "合并症", "病因", "发病机制",
            "预后", "后遗症", "出院小结", "病程记录",
            # 症状 / 体征
            "呼吸困难", "心动过速", "心动过缓", "心律失常", "发绀",
            "水肿", "红斑", "血尿", "咯血", "肌痛", "晕厥", "黄疸",
            "面色苍白", "高血压", "低血压", "缺氧", "发热", "低热",
            "未见异常",
            # 检查
            "心电图", "脑电图", "核磁共振", "CT", "超声检查", "X线检查",
            "血常规", "尿常规", "生化检查", "活检", "内镜检查",
            "超声心动图",
            # 治疗
            "禁忌症", "预防用药", "空腹", "静脉注射", "肌肉注射",
            "皮下注射", "口服", "必要时", "急诊", "随访",
            # 解剖
            "近端", "远端", "外侧", "内侧", "双侧", "单侧",
        ],
        # Latin abbreviations only — see the module docstring on homophones.
        replacements=[
            ("ct", "CT"),
        ],
    ),
    "it": PackContent(
        # Chinese developers speak Chinese and write tool names in Latin — the
        # same split as every other IT pack.
        terms=[
            # 流程
            "分支", "提交", "合并", "回滚", "发布", "构建", "部署",
            "代码审查", "技术债务", "重构", "回归", "故障", "测试环境",
            "生产环境", "灰度发布", "预发布环境",
            # 架构
            "微服务", "单体架构", "负载均衡", "延迟", "吞吐量",
            "内存泄漏", "竞态条件", "容错", "可扩展性", "向后兼容",
            "消息队列", "缓存", "接口", "幂等",
            # 数据
            "数据库", "索引", "迁移", "事务", "锁", "复制", "分片",
            # 运维
            "监控", "日志", "链路追踪", "指标", "单元测试", "集成测试",
            "测试覆盖率", "压力测试", "告警",
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
            "应付账款", "应收账款", "权责发生制", "折旧", "摊销",
            "资产负债表", "利润表", "现金流量表", "总账", "毛利率",
            "净利率", "营业费用", "对账", "计提", "核销", "发票",
            "会计年度", "财务报表", "专用发票",
            # 指标
            "营运资金", "现金流", "自由现金流", "盈利能力", "盈亏平衡点",
            "流动性", "偿债能力", "杠杆", "折现率", "净现值",
            "内部收益率", "EBITDA", "ROI",
            # 资本运作
            "注册资本", "增资", "股权稀释", "估值", "融资轮次",
            "股东协议", "尽职调查", "分红", "对冲", "托管账户",
            # 税务 / 监管
            "增值税", "企业所得税", "审计报告", "会计准则",
            "国际财务报告准则", "纳税申报",
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
            "潜在客户", "销售线索", "商机", "销售漏斗", "销售阶段",
            "首次接触", "陌生拜访", "商务提案", "报价单", "演示",
            "概念验证", "试点项目", "谈判", "成交", "丢单",
            "销售周期", "销售预测", "销售目标", "转化率", "客单价",
            # 客户关系
            "异议", "异议处理", "决策人", "对接人", "痛点",
            "价值主张", "增购", "交叉销售", "续约", "客户维系",
            "流失率", "客户名单", "触点", "跟进", "客户开通",
            # 术语
            "CRM", "KPI", "NPS", "采购订单", "框架协议",
        ],
        replacements=[
            ("crm", "CRM"),
            ("kpi", "KPI"),
            ("nps", "NPS"),
        ],
    ),
}
