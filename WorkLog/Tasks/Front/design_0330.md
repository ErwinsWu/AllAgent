### 💻 前端开发任务书：客户全景图谱交互界面

**To: 软件研发负责人**
**From: PM**

#### 一、 核心目标与定位
本周你的核心任务是完成 **“全景蜘蛛网图（Structure）”** 的前端渲染与核心点击交互。
**注意：** 不要等待后端的真实 API！请直接使用我提供的 `Mock JSON` 数据（见附录）写死在前端代码里进行开发。我们本周五的验收目标是：用假数据跑通所有视觉动效和交互逻辑。

#### 二、 视觉与布局要求 (UI/UX)
我们将采用“中心发散式”的关系图谱（推荐使用 **ECharts 的关系图 Graph**，或 **AntV G6**，或 **React Flow**）。



**具体节点渲染规则（严格对照 JSON 字段）：**

1.  **中心节点 (Root)：** * **数据源：** `customer_profile.customer_name`
    * **视觉：** 最大的核心圆点（建议主色调蓝色/绿色），突出客户名称。
2.  **一级分类节点 (Level 1)：**
    * 从中心节点固定发散出 4 个分类节点：“客户画像”、“历史诉求”、“当前卡点”、“维系策略”。
3.  **二级数据节点 (Level 2 - 叶子节点)：**
    * **画像节点：** 渲染 `persona_tags` 里的标签。若 `risk_level` 为“高危流失”，该节点必须标红闪烁或高亮！
    * **诉求节点：** 渲染 `historical_needs`。若 `status` 为“未满足”，节点标橙色。
    * **卡点节点（重点）：** 渲染 `current_blockers`。若 `severity` 为“高”，节点标红色。
    * **策略节点：** 渲染 `retention_strategy`。突出显示“下一步动作”。

#### 三、 核心交互逻辑 (Interaction - Demo的灵魂)
老板看 Demo，看的就是“点按之间的顺滑感”和“信息的即时呈现”。必须实现以下两个核心交互：

1.  **Hover (悬停) 显示详情：**
    * 当鼠标悬停在“当前卡点”的具体节点上时，必须弹出一个 Tooltip，展示 JSON 中的 `details_summary`（卡点详情描述）。
2.  **Click (点击) 展开侧边抽屉/弹窗：**
    * **场景：** 业务员需要看具体文档。
    * **动作：** 当点击“历史诉求”或“维系策略”下带有文件的节点时，页面右侧滑出一个抽屉（Drawer）或弹窗，渲染 JSON 中的 `associated_docs` / `suggested_materials` 数组。
    * **呈现：** 变成一个清晰的文件列表（例如：📄 `私有化部署技术白皮书.pdf`），并带有一个【点击预览】或【一键发送】的假按钮。

#### 四、 附录：开发用 Mock JSON 数据
*(请直接将这个 JSON 复制进你的项目中作为 state/data 初始值，照着这个结构解析画图)*

```json
{
  "customer_profile": {
    "customer_name": "张总 (某建筑集团)",
    "value_tier": "高价值", 
    "risk_level": "高危流失", 
    "persona_tags": ["价格敏感", "看重售后", "决策慢"] 
  },
  "historical_needs": [
    {
      "need_id": "N001",
      "topic": "定制化报表功能",
      "status": "已满足",
      "associated_docs": [
        {"doc_name": "定制报表交付手册.pdf", "doc_type": "PDF"}
      ]
    },
    {
      "need_id": "N002",
      "topic": "系统并发响应速度",
      "status": "未满足",
      "associated_docs": [
        {"doc_name": "技术部延迟排查报告.pdf", "doc_type": "PDF"}
      ]
    }
  ],
  "current_blockers": [
    {
      "blocker_id": "B001",
      "topic": "今年预算缩减",
      "severity": "高",
      "details_summary": "客户提到老板今年卡预算，正在看便宜一半的竞品X"
    }
  ],
  "retention_strategy": {
    "strategy_type": "价值自证与降价挽留",
    "next_best_action": "发送竞品X的ROI对比表，并申请9折限时优惠",
    "suggested_materials": [
      {"doc_name": "与竞品X的ROI对比测算表.xlsx", "doc_type": "Excel"},
      {"doc_name": "9折优惠申请审批流SOP.txt", "doc_type": "TXT"}
    ],
    "auto_reply_script": "张总您好，理解您那边的预算压力。我特意拉了一份咱们系统和竞品X的长期投入产出比数据，其实拉长看咱们的综合成本更低。另外我也向领导申请了一个本月特批的9折名额，您看下午方便通个电话给您汇报下吗？"
  }
}
```

#### 五、 交付节点
* **1** 完成静态关系图的渲染，节点颜色能根据 Mock 数据的状态正确显示。
* **2** 完成 Hover 和 Click（弹出侧边文档列表）的交互动作。跑通纯前端的视觉 Demo。

***
