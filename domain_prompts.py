"""
企业管理信息化领域词汇表
用于 MLX Whisper 初始提示词，提升专业术语转录准确率
"""

# ── 预设提示词（用于 GUI 下拉选择） ──────────────────────────

PRESET_PROMPTS: list[tuple[str, str]] = [
    ("无", ""),
    ("SAP 财务", "SAP,S4HANA,FI,CO,总账,应收,应付,固定资产,成本中心,利润中心,凭证,科目表,合并报表,Fiori,ABAP"),
    ("SAP 供应链", "SAP,S4HANA,MM,SD,WM,EWM,MRP,采购订单,收货,发票核验,BOM,工单,销售订单,Ariba,库存,仓储"),
    ("SAP 全模块", "SAP,S4HANA,ECC,FI,CO,MM,SD,PP,WM,EWM,HCM,PM,QM,PS,Fiori,ABAP,HANA,BTP,SuccessFactors,Ariba,Concur,IBP,APO"),
    ("Oracle ERP", "Oracle,EBS,Fusion,Oracle Cloud,NetSuite,Hyperion,HFM,EPBCS,OAC,GL,AP,AR,FA,Projects,PeopleSoft"),
    ("微软 Dynamics", "Microsoft,Dynamics 365,D365,Business Central,Power BI,Power Platform,Azure,Copilot,Finance,Supply Chain"),
    ("金蝶", "金蝶,星空,苍穹,金蝶云,EAS,K3,BOS,苍穹平台,财务云,供应链云,应收,应付,总账,成本,资产,预算,合并"),
    ("用友", "用友,NC,NCC,U8,U9,YonBIP,iuap,用友云,畅捷通,财务云,供应链云,制造云,人力云,UFO报表"),
    ("ERP 实施项目", "ERP,蓝图,GAP分析,配置,客制化,UAT,SIT,上线,数据迁移,割接,变更管理,关键用户,顾问,实施,接口,集成"),
    ("财务专业", "IFRS,合并报表,内部控制,SOX,FP&A,滚动预测,零基预算,资金管理,现金池,增值税,企业所得税,电子发票,数电票,转让定价,Intercompany"),
    ("零售行业", "零售,连锁,门店,加盟,直营,SKU,POS,电商,全渠道,O2O,会员,CRM,供应商,配送中心,库存周转,坪效"),
    ("制造行业", "MES,PLM,BOM,工艺路线,MRP,工单,质量管理,精益生产,Six Sigma,设备管理,预防性维护,SCADA,工作中心"),
]


# ── 完整词汇库（供参考或构建自定义提示词） ─────────────────

VOCABULARY = {
    "通用ERP": [
        "ERP", "企业资源计划", "数字化转型", "信息化", "上线", "实施", "部署",
        "集成", "接口", "迁移", "数据迁移", "主数据", "业务流程", "最佳实践",
        "行业解决方案", "SaaS", "PaaS", "私有云", "公有云", "混合云",
        "财务共享", "共享服务中心", "SSC", "GBS", "集团管控", "合并报表",
        "总账", "应收", "应付", "固定资产", "成本", "预算", "资金", "税务",
        "供应链", "采购", "库存", "仓储", "销售", "生产", "制造", "质量",
        "BI", "商业智能", "数据分析", "KPI", "仪表盘", "驾驶舱",
    ],
    "SAP产品": [
        "SAP", "S4HANA", "S/4HANA", "ECC", "R3", "SAP ERP",
        "SAP Business One", "SAP ByDesign", "SAP Ariba", "SAP Concur",
        "SAP SuccessFactors", "SAP IBP", "SAP BTP", "SAP Analytics Cloud",
        "SAC", "SAP Datasphere", "SAP HANA", "SAP Signavio",
        "FI", "CO", "MM", "SD", "PP", "WM", "EWM", "HCM", "PM", "QM", "PS",
        "Fiori", "ABAP", "BASIS", "NetWeaver", "SRM", "APO", "TM", "MDG",
    ],
    "Oracle产品": [
        "Oracle", "Oracle EBS", "Oracle Fusion", "Oracle Cloud ERP",
        "Oracle NetSuite", "NetSuite", "JD Edwards", "PeopleSoft",
        "Hyperion", "HFM", "EPBCS", "Oracle Analytics Cloud", "OAC",
        "Oracle SCM", "Oracle HCM", "Oracle EPM", "Primavera",
    ],
    "微软产品": [
        "Microsoft", "Dynamics 365", "D365", "Business Central",
        "Dynamics AX", "Dynamics NAV", "Power BI", "Power Platform",
        "Power Apps", "Power Automate", "Azure", "Copilot", "Teams",
    ],
    "金蝶": [
        "金蝶", "Kingdee", "金蝶云", "星空", "苍穹", "金蝶云苍穹",
        "K3", "EAS", "金蝶EAS", "BOS", "苍穹平台", "精斗云",
        "财务云", "供应链云", "人力云", "制造云",
    ],
    "用友": [
        "用友", "Yonyou", "用友网络", "NC", "NCC", "用友NCC",
        "U8", "U9", "T系列", "YonBIP", "用友BIP", "iuap",
        "用友云", "畅捷通", "UFO报表",
    ],
    "财务术语": [
        "GAAP", "IFRS", "合并报表", "合并范围", "商誉", "减值测试",
        "内部控制", "SOX", "萨班斯", "FP&A", "财务规划与分析",
        "滚动预测", "零基预算", "弹性预算", "现金池", "现金流预测",
        "增值税", "企业所得税", "电子发票", "数电票",
        "转让定价", "Intercompany", "公司间交易", "关联交易",
        "科目表", "账套", "账期", "凭证", "摊销", "折旧", "资本化",
        "IFRS16", "ASC842", "租赁准则",
    ],
    "实施术语": [
        "蓝图", "Blueprint", "需求调研", "差距分析", "GAP分析",
        "客制化", "二次开发", "RICEFW", "UAT", "用户验收测试",
        "SIT", "系统集成测试", "上线", "割接", "Cut-over",
        "数据割接", "变更管理", "关键用户", "超级用户",
        "功能顾问", "技术顾问", "实施顾问", "许可证", "License",
    ],
}
