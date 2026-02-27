# 飞书AI智能体 - 快速Demo

这是一个基于大语言模型(Claude)的飞书智能客服助手的最小可行版本(MVP)。

## 功能特性

- ✅ 接收飞书消息并自动回复
- ✅ 智能识别用户意图(问候、产品咨询、价格等)
- ✅ 基于产品知识库自动回答常见问题
- ✅ 支持多轮对话，维护上下文
- ✅ 集成Claude大语言模型生成自然回复

## 项目结构

```
demo/
├── app.py                      # FastAPI主应用
├── config.py                   # 配置管理和产品知识加载
├── feishu_connector.py         # 飞书连接模块
├── ai_engine.py                # AI对话引擎
├── dialog_router.py            # 对话路由器
├── product_knowledge.json      # 产品知识库
├── requirements.txt            # Python依赖
├── .env.example                # 环境变量模板
└── README.md                   # 本文件
```

## 快速开始

### 1. 环境准备

#### 1.1 安装Python依赖

```bash
cd demo
pip install -r requirements.txt
```

#### 1.2 配置环境变量

复制 `.env.example` 到 `.env` 并填写配置:

```bash
cp .env.example .env
```

编辑 `.env` 文件:

```env
# 飞书应用配置(在飞书开放平台获取)
FEISHU_APP_ID=cli_xxxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxx
FEISHU_VERIFICATION_TOKEN=xxxxxxxxxxxxx

# Claude API配置(在Anthropic控制台获取)
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxx
CLAUDE_MODEL=claude-3-sonnet-20240229

# 公司和产品信息(根据实际情况修改)
COMPANY_NAME=您的公司名称
PRODUCT_NAME=您的产品名称
BOT_NAME=小智
```

### 2. 配置飞书应用

#### 2.1 创建飞书应用

1. 访问 [飞书开放平台](https://open.feishu.cn/)
2. 点击"创建企业自建应用"
3. 填写应用名称和描述
4. 记录下 `App ID` 和 `App Secret`

#### 2.2 配置权限

在应用管理页面，添加以下权限:

- `im:message` - 获取与发送单聊、群组消息
- `im:message.group_at_msg` - 获取群组中@机器人的消息
- `im:message.p2p_msg` - 获取用户发给机器人的单聊消息

#### 2.3 配置事件订阅

1. 进入"事件订阅"页面
2. 设置请求地址: `https://your-domain.com/webhook/feishu`
   - 注意: 需要公网可访问的URL
   - 本地开发可使用ngrok等工具: `ngrok http 8000`
3. 添加事件: `接收消息 v2.0` (im.message.receive_v1)
4. 记录下"Verification Token"

### 3. 自定义产品知识

编辑 `product_knowledge.json` 文件,填写你的产品信息:

```json
{
  "product": {
    "name": "你的产品名称",
    "description": "产品描述...",
    "features": [...],
    ...
  },
  "faqs": [
    {
      "question": "常见问题1?",
      "answer": "答案1",
      "keywords": ["关键词1", "关键词2"]
    }
  ]
}
```

### 4. 启动服务

```bash
python app.py
```

服务将在 `http://0.0.0.0:8000` 启动。

### 5. 测试

#### 5.1 健康检查

```bash
curl http://localhost:8000/health
```

#### 5.2 在飞书中测试

1. 在飞书中搜索你的应用名称
2. 添加应用到会话
3. 发送消息测试:
   - "你好" - 测试问候
   - "介绍一下你们的产品" - 测试产品介绍
   - "多少钱?" - 测试价格咨询
   - "如何联系你们?" - 测试联系方式

## 核心模块说明

### 1. 飞书连接模块 (feishu_connector.py)

负责与飞书平台交互:
- 接收和解析飞书消息事件
- 发送文本和Markdown消息
- 验证webhook请求

```python
feishu = FeishuConnector()

# 发送消息
feishu.send_text_message(chat_id, "Hello!")

# 回复消息
feishu.reply_to_message(message_id, "回复内容")
```

### 2. AI对话引擎 (ai_engine.py)

调用Claude API生成回复:
- 维护多轮对话上下文
- 注入产品知识到prompt
- 意图识别

```python
ai_engine = AIEngine()

# 生成回复
response = ai_engine.generate_response(
    user_id="user123",
    message="产品有什么功能?",
    context="产品知识..."
)
```

### 3. 对话路由器 (dialog_router.py)

智能路由用户消息:
- 识别用户意图
- 决策处理策略
- 整合各模块功能

```python
router = DialogRouter()

# 处理消息
response = router.handle_message(
    user_id="user123",
    message="你好",
    chat_id="chat456"
)
```

### 4. 配置管理 (config.py)

- 加载环境变量
- 管理产品知识库
- 提供FAQ搜索

```python
from config import settings, product_knowledge

# 获取产品介绍
intro = product_knowledge.get_product_intro()

# 搜索FAQ
faqs = product_knowledge.search_faq("价格")
```

## 扩展功能

### 添加飞书文档搜索

在 `feishu_connector.py` 中实现 `search_documents` 方法:

```python
def search_documents(self, query: str, limit: int = 5) -> list:
    """搜索飞书文档"""
    # 调用飞书搜索API
    # 参考: https://open.feishu.cn/document/server-docs/docs/docs/search_v2/open-search
    pass
```

### 添加对话历史存储

使用SQLite或Redis存储对话历史:

```python
# 安装: pip install aiosqlite
import aiosqlite

async def save_message(user_id, message, response):
    async with aiosqlite.connect("conversations.db") as db:
        await db.execute(
            "INSERT INTO messages (user_id, message, response, timestamp) VALUES (?, ?, ?, ?)",
            (user_id, message, response, time.time())
        )
        await db.commit()
```

### 添加监控和日志

集成Prometheus和Grafana:

```python
from prometheus_client import Counter, Histogram

# 定义指标
message_counter = Counter('messages_total', 'Total messages')
response_time = Histogram('response_seconds', 'Response time')

# 使用指标
message_counter.inc()
with response_time.time():
    response = router.handle_message(...)
```

## 部署

### 使用Docker部署

创建 `Dockerfile`:

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "app.py"]
```

构建和运行:

```bash
docker build -t feishu-ai-agent .
docker run -p 8000:8000 --env-file .env feishu-ai-agent
```

### 使用systemd部署

创建 `/etc/systemd/system/feishu-ai-agent.service`:

```ini
[Unit]
Description=Feishu AI Agent
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/feishu-ai-agent
Environment="PATH=/opt/feishu-ai-agent/venv/bin"
ExecStart=/opt/feishu-ai-agent/venv/bin/python app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务:

```bash
sudo systemctl daemon-reload
sudo systemctl start feishu-ai-agent
sudo systemctl enable feishu-ai-agent
```

## 常见问题

### Q: 收不到飞书消息?

检查:
1. webhook URL是否配置正确且公网可访问
2. 飞书应用权限是否配置完整
3. 事件订阅是否启用
4. 查看应用日志: `tail -f app.log`

### Q: AI回复质量不好?

优化方法:
1. 完善 `product_knowledge.json` 中的产品信息
2. 调整 `ai_engine.py` 中的系统提示词
3. 增加FAQ数量和质量
4. 考虑使用更强大的模型(如claude-3-opus)

### Q: API调用成本太高?

优化策略:
1. 添加对话缓存(相似问题直接返回缓存答案)
2. 限制对话历史长度
3. 对简单问题使用规则回复而不是LLM
4. 使用更便宜的模型处理简单问题

### Q: 如何支持多个飞书应用?

修改代码支持多租户:
1. 配置文件支持多个app_id
2. webhook路由区分不同应用
3. 独立的产品知识库

## 进阶功能

### 1. 添加向量检索

使用FAISS或Qdrant提升知识库检索准确度:

```bash
pip install faiss-cpu sentence-transformers
```

### 2. 接入更多渠道

- 企业微信
- 钉钉
- Slack
- Web客服插件

### 3. 添加用户画像

记录用户行为,提供个性化服务:
- 对话历史分析
- 兴趣标签
- 推荐相关产品

### 4. 多语言支持

检测用户语言并返回对应语言的回复:

```python
from langdetect import detect

lang = detect(message)  # 'zh-cn', 'en', etc
```

## 性能指标

### MVP版本性能

- 响应延迟: 2-5秒 (取决于LLM API)
- 并发处理: 10-50 QPS (单实例)
- 内存占用: ~100MB
- 适合场景: 日活100-500用户

### 优化后性能

- 响应延迟: 0.5-2秒 (缓存命中时)
- 并发处理: 100-500 QPS (多实例+负载均衡)
- 内存占用: ~500MB (含向量数据库)
- 适合场景: 日活5000+用户

## 技术支持

如有问题,请参考:
- [飞书开放平台文档](https://open.feishu.cn/document/)
- [Claude API文档](https://docs.anthropic.com/)
- [FastAPI文档](https://fastapi.tiangolo.com/)

## License

MIT License
