"""
企业管理信息化领域词汇表
用于 MLX Whisper 初始提示词，提升专业术语转录准确率
"""

import re

# ── 内置词汇库（每次转录默认全量纳入） ───────────────────────

VOCABULARY = {
    "通用ERP": [
        "ERP", "企业资源计划", "数字化转型", "信息化", "上线", "实施", "部署",
        "集成", "接口", "迁移", "数据迁移", "主数据", "业务流程", "最佳实践",
        "行业解决方案", "SaaS", "PaaS", "私有云", "公有云", "混合云",
        "财务共享", "共享服务中心", "SSC", "GBS", "集团管控", "合并报表",
        "总账", "应收", "应付", "固定资产", "成本", "预算", "资金", "税务",
        "供应链", "采购", "库存", "仓储", "销售", "生产", "制造", "质量",
        "BI", "商业智能", "数据分析", "KPI", "仪表盘", "驾驶舱",
        "ROI", "TCO", "单点登录", "SSO", "API", "中台", "微服务", "低代码",
        "工作流", "审批流", "权限管理", "角色", "许可证", "License",
    ],
    "SAP产品": [
        "S4HANA", "S/4HANA", "ECC", "R3",
        "Business One", "ByDesign", "Ariba", "Concur",
        "SuccessFactors", "IBP", "BTP", "Analytics Cloud",
        "SAC", "Datasphere", "HANA", "Signavio", "LeanIX",
        "GRC", "MDG", "MDM", "SRM", "APO", "TM",
        "EWM", "CAR", "Commerce Cloud", "CX",
        "BDC", "Joule",
        "FI", "CO", "MM", "SD", "PP", "WM", "EWM", "HCM", "PM", "QM", "PS",
        "Fiori", "ABAP", "BASIS", "NetWeaver",
        "CO-PA", "PCA", "利润中心", "成本中心", "内部订单",
        "总账", "GL", "应收账款", "AR", "应付账款", "AP",
        "固定资产管理", "AA", "获利分析", "产品成本核算",
    ],
    "Oracle产品": [
        "EBS", "E-Business Suite", "Fusion",
        "Cloud ERP", "NetSuite",
        "JD Edwards", "PeopleSoft", "Siebel",
        "Hyperion", "HFM", "Hyperion Financial Management",
        "EPBCS", "FCCS", "ARCS", "PCMCS",
        "OAC", "OBIEE",
        "SCM Cloud", "HCM Cloud", "EPM Cloud", "Primavera",
        "OIC", "Exadata",
    ],
    "微软产品": [
        "Dynamics 365", "D365", "Business Central", "BC",
        "Dynamics AX", "Dynamics NAV", "Dynamics GP",
        "Power BI", "Power Platform", "Power Apps", "Power Automate",
        "Azure", "Copilot", "Teams", "SharePoint",
        "Office 365", "M365", "AI Builder",
        "Dynamics 365 Finance", "Dynamics 365 Supply Chain",
        "Dynamics 365 Commerce", "Dynamics 365 HR",
    ],
    "金蝶": [
        "金蝶", "Kingdee", "金蝶云", "星空", "金蝶云星空",
        "苍穹", "金蝶云苍穹", "K3", "金蝶K3", "EAS", "金蝶EAS",
        "BOS", "苍穹平台", "精斗云", "金蝶开发平台",
        "财务云", "供应链云", "人力云", "制造云", "协同云",
    ],
    "用友": [
        "用友", "Yonyou", "用友网络", "NC", "NCC", "用友NCC",
        "U8", "用友U8", "U9", "用友U9", "T系列", "用友T+", "用友T3",
        "YonBIP", "用友BIP", "iuap", "用友iuap",
        "用友云", "畅捷通", "UFO报表",
        "财务云", "供应链云", "制造云", "人力云",
    ],
    "其他厂商": [
        "Salesforce", "ServiceNow", "Workday", "Infor", "IFS", "Epicor",
        "Anaplan", "OneStream", "Planful", "Adaptive Insights",
        "BlackLine", "Blackline", "账务自动化",
        "Kyriba", "TMS", "资金管理系统",
        "MuleSoft", "Boomi", "Informatica",
        "Tableau", "Qlik", "Looker",
        "汉得", "浪潮", "远光软件", "久其软件", "华为云", "阿里云", "腾讯云",
    ],
    "财务术语": [
        "GAAP", "IFRS", "合并报表", "合并范围", "商誉", "减值测试",
        "内部控制", "SOX", "萨班斯", "FP&A", "财务规划与分析",
        "财务BP", "财务业务合作伙伴",
        "滚动预测", "Rolling Forecast", "零基预算", "弹性预算",
        "现金池", "现金流预测", "票据",
        "增值税", "VAT", "企业所得税", "个人所得税", "关税",
        "电子发票", "数电票", "转让定价", "TP",
        "Intercompany", "公司间交易", "关联交易",
        "科目表", "账套", "账期", "凭证", "摊销", "折旧", "资本化",
        "IFRS16", "ASC842", "租赁准则", "租赁资产",
        "应收账款", "应付账款", "期末结账", "月结", "年结",
        "资产负债表", "利润表", "现金流量表",
    ],
    "实施术语": [
        "蓝图", "Blueprint", "需求调研", "差距分析", "GAP分析",
        "客制化", "二次开发", "RICEFW",
        "UAT", "用户验收测试", "SIT", "系统集成测试",
        "上线", "割接", "Cut-over", "并行运行", "数据割接",
        "变更管理", "关键用户", "超级用户",
        "功能顾问", "技术顾问", "实施顾问",
    ],
    "零售行业": [
        "零售", "连锁", "门店", "加盟", "直营", "SKU", "商品", "品类",
        "促销", "会员", "POS", "收银", "电商", "全渠道", "O2O",
        "销售额", "客单价", "坪效", "库存周转", "毛利率",
        "供应商", "配送中心", "DC", "前置仓",
    ],
    "制造行业": [
        "MES", "制造执行系统", "SCADA", "PLM", "PDM",
        "精益生产", "Lean", "六西格玛", "Six Sigma", "TQM", "TPM",
        "BOM", "物料清单", "工艺路线", "工序", "工作中心", "产能",
        "质量管理", "检验", "返工", "报废",
        "设备管理", "预防性维护", "备件", "CMMS",
    ],
}

# 所有内置词汇的扁平集合（用于去重）
_BUILTIN_SET: set[str] = {
    term.strip()
    for terms in VOCABULARY.values()
    for term in terms
}

# 内置提示词字符串（一次性构建，按类别逗号拼接）
BUILTIN_PROMPT: str = ",".join(
    term
    for terms in VOCABULARY.values()
    for term in terms
)


def build_prompt(user_input: str | None = None) -> str:
    """
    构建最终提示词：内置词汇库 + 用户附加词汇（去重）。

    user_input 支持中英文逗号分隔，如 "星巴克，咖啡，Starbucks,latte"
    """
    if not user_input or not user_input.strip():
        return BUILTIN_PROMPT

    # 拆分用户输入（支持中英文逗号、顿号、空格）
    user_terms = [
        t.strip()
        for t in re.split(r"[,，、\s]+", user_input)
        if t.strip()
    ]

    # 去掉已在内置库中的词（大小写不敏感）
    builtin_lower = {t.lower() for t in _BUILTIN_SET}
    extra = [t for t in user_terms if t.lower() not in builtin_lower]

    if extra:
        return BUILTIN_PROMPT + "," + ",".join(extra)
    return BUILTIN_PROMPT


# ── 预设提示词（GUI 下拉，作为用户输入的快捷方式） ─────────────

PRESET_PROMPTS: list[tuple[str, str]] = [
    ("无附加词汇", ""),
    ("SAP 财务场景", "SAP财务,FI模块,CO模块,Fiori界面,期末结账,科目分配"),
    ("SAP 供应链场景", "SAP供应链,MM模块,SD模块,EWM仓储,MRP运行,Ariba采购"),
    ("SAP 全模块场景", "SAP全模块,S4HANA升级,系统迁移,Greenfield,Brownfield"),
    ("Oracle 场景", "Oracle实施,EBS升级,Fusion迁移,Hyperion合并,Cloud EPM"),
    ("微软 Dynamics 场景", "Dynamics实施,D365上线,Power Platform,Copilot集成"),
    ("金蝶场景", "金蝶实施,星空上线,苍穹平台,金蝶财务云,金蝶供应链"),
    ("用友场景", "用友实施,NC上线,YonBIP,用友财务云,用友供应链"),
    ("ERP 选型评估", "ERP选型,招标,RFP,评分标准,方案演示,TCO分析,实施周期"),
    ("财务数字化", "财务数字化,财务共享,智能财务,财务机器人,RPA,自动化对账"),
    ("零售连锁场景", "星巴克,连锁门店,加盟管理,收银系统,会员积分,全渠道"),
    ("制造供应链场景", "工厂管理,生产计划,MES上线,质量追溯,设备IoT,智能工厂"),
]
