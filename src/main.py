from fastapi import FastAPI, Query, UploadFile, File, Form
from pydantic import BaseModel
from utils.load import load_model_client, Provider
from pypdf import PdfReader
import re
import json
import io
import os
from datetime import datetime

app = FastAPI(title="大模型客户端 API", description="使用 FastAPI 提供大模型问答服务")

class BaseResponse(BaseModel):
    code: int
    msg: str
    data: dict = {}

class AskWithSystemRequest(BaseModel):
    system_prompt: str
    question: str

class CRMProfileRequest(BaseModel):
    crm_profile: str

class CommunicationRecordRequest(BaseModel):
    communication_record: str

# 固定配置：使用 OpenAI GPT
PROVIDER = Provider.MINIMAX
MODEL_NAME = "MiniMax-M2.5"

BLOCKER_ANALYSIS_SYSTEM_PROMPT = """你是一位资深的 B2B 大客户销售与战略客户维系专家，拥有跨行业（消费电子、汽车电子、家电、医疗器械、机器人等）的软硬件产品线商务经验。你的核心任务是：根据客户沟通记录，精准识别当前真实的、演化后的技术/商业卡点（Blockers），并输出可执行的客户维系策略。

## 分析要求

### 1. 卡点（Blocker）识别规则
- **必须识别演化后的核心卡点**，而非对话初期的表面问题。客户的真实诉求往往在对话后半段才暴露。
- 注意区分：技术卡点（良率、算法、认证） vs 商业卡点（价格、交期、库存、备选供应商威胁）。
- 警惕客户的隐晦施压话术，例如：
  - "对方报价低于贵司 X 元" → 价格竞争力不足
  - "我司高层不支持维持当前份额" → 份额降级风险
  - "已有人提出退回传统方案" → 技术路线被替代的风险
  - "备选供应商已拜访/已引荐" → 切换供应商的威胁
  - "项目将自动触发降级机制" → 方案被淘汰的硬性死线
- 关注**软硬件业务形态转换**：当客户从纯硬件需求扩展到算法/软件/SDK层面时，卡点可能从硬件质量变为软件交付能力。
- 每个 Blocker 需包含：`type`（技术/商业/合规）、`category`（具体分类）、`description`（描述）、`severity`（高/中/低）、`deadline`（如有）、`evidence`（证据来源，引用聊天记录中的原话，格式如："客户在 14:15 提到：'易云管家报价比你们便宜一半'"）。

### 2. 维系策略（Retention Strategy）输出规则
- 策略必须包含**内部动作**（如高层协调供应链、调派研发攻坚），不能仅是销售话术。
- 策略需区分优先级：哪些是必须立即执行的，哪些是中长期规划的。
- 每个策略动作需包含：`action`（具体动作）、`owner`（执行责任人角色）、`urgency`（紧急/重要/常规）。

## 输出格式
请返回一个 JSON 格式的结果，包含以下字段：
{
    "summary": "一句话概述当前客户关系态势和核心矛盾",
    "risk_level": "红色/橙色/黄色",
    "blockers": [
        {
            "type": "技术/商业/合规",
            "category": "具体分类（如：价格竞争、交期弹性、算法交付、认证死线等）",
            "description": "卡点的详细描述，引用对话中的关键证据",
            "severity": "高/中/低",
            "deadline": "如有明确截止日期则填写，否则为 null",
            "evidence": "证据来源，引用聊天记录中的原话，格式如：'客户在 14:15 提到：\"易云管家报价比你们便宜一半\"'"
        }
    ],
    "retention_strategy": {
        "immediate_actions": [
            {
                "action": "具体动作",
                "owner": "执行责任人角色（如：销售经理、研发总监、高层领导）",
                "urgency": "紧急"
            }
        ],
        "internal_actions": [
            {
                "action": "内部协调动作",
                "owner": "执行责任人角色",
                "urgency": "紧急/重要"
            }
        ],
        "long_term_actions": [
            {
                "action": "中长期策略动作",
                "owner": "执行责任人角色",
                "urgency": "常规"
            }
        ]
    }
}

请确保返回有效的 JSON 格式。不要遗漏任何在对话中出现的关键施压信号或隐晦的商业威胁。"""

KEYWORD_EXTRACTION_PROMPT = """从以下文本中提取 5-10 个核心关键词，用逗号分隔返回，不要返回其他任何内容。关键词应涵盖文本中的核心主题、关键实体、技术术语和重要概念。"""

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")

def extract_think_content(text: str) -> tuple:
    """
    从响应文本中提取思考内容和主要内容。
    
    Args:
        text: 完整的响应文本
        
    Returns:
        (think_content, main_content) 元组
    """
    think_pattern = r'<think>(.*?)</think>'
    match = re.search(think_pattern, text, re.DOTALL)
    
    if match:
        think_content = match.group(1).strip()
        main_content = re.sub(think_pattern, '', text, flags=re.DOTALL).strip()
        return think_content, main_content
    else:
        return None, text

@app.post("/ask", summary="向大模型提问", response_model=BaseResponse)
async def ask(question: str, include_think: bool = Query(False)):
    """
    向固定的大模型提问，返回结果。

    - **question**: 用户提问字符串
    - **include_think**: 是否返回模型的思考内容 (默认: false)
    """
    try:
        # 初始化客户端
        client = load_model_client(PROVIDER, MODEL_NAME)
        # 提问
        answer = client.ask(question)
        
        # 提取思考内容
        think_content, main_content = extract_think_content(answer)
        
        # 构建返回数据
        response_data = {"answer": main_content}
        if include_think and think_content:
            response_data["think"] = think_content
        
        return BaseResponse(code=200, msg="success", data=response_data)
    except Exception as e:
        return BaseResponse(code=500, msg=f"请求失败: {str(e)}", data={})

@app.post("/ask-with-system", summary="使用自定义提示词提问", response_model=BaseResponse)
async def ask_with_system(request: AskWithSystemRequest, include_think: bool = Query(False)):
    """
    使用自定义的系统提示词向大模型提问。

    - **system_prompt**: 自定义的系统提示词
    - **question**: 用户提问字符串
    - **include_think**: 是否返回模型的思考内容 (默认: false)
    """
    try:
        # 初始化客户端
        client = load_model_client(PROVIDER, MODEL_NAME)
        # 带系统提示词的提问
        answer = client.ask_with_system(request.system_prompt, request.question)
        
        # 提取思考内容
        think_content, main_content = extract_think_content(answer)
        
        # 构建返回数据
        response_data = {"answer": main_content}
        if include_think and think_content:
            response_data["think"] = think_content
        
        return BaseResponse(code=200, msg="success", data=response_data)
    except Exception as e:
        return BaseResponse(code=500, msg=f"请求失败: {str(e)}", data={})

@app.post("/analyze-customer-profile", summary="分析客户画像", response_model=BaseResponse)
async def analyze_customer_profile(request: CRMProfileRequest, include_think: bool = Query(False)):
    """
    根据 CRM 初始客户档案分析用户画像和历史标签。

    - **crm_profile**: CRM 初始客户档案内容
    - **include_think**: 是否返回模型的思考内容 (默认: false)
    
    返回结果为 JSON 格式，包含用户画像信息和历史标签。
    """
    system_prompt = """你是一个专业的客户关系管理专家。请根据提供的 CRM 初始客户档案信息，分析并生成用户画像信息和历史标签。

请返回一个 JSON 格式的结果，包含以下字段：
{
    "user_profile": {
        "company_name": "公司名称",
        "contacts": [{"name": "姓名", "position": "职位"}],
        "customer_grade": "客户评级",
        "cooperation_history": "历史合作项目综述",
        "key_characteristics": ["特征1", "特征2", ...]
    },
    "historical_tags": ["标签1", "标签2", ...]
}

请确保返回有效的 JSON 格式。"""

    customer_profile_question = f"请分析以下 CRM 初始客户档案信息：\n{request.crm_profile}"
    
    try:
        # 初始化客户端
        client = load_model_client(PROVIDER, MODEL_NAME)
        # 带系统提示词的提问
        answer = client.ask_with_system(system_prompt, customer_profile_question)
        
        # 提取思考内容
        think_content, main_content = extract_think_content(answer)

        # 剥离 markdown 代码块包裹 (```json ... ``` 或 ``` ... ```)
        cleaned = re.sub(r'^```(?:json)?\s*\n?', '', main_content.strip())
        cleaned = re.sub(r'\n?```\s*$', '', cleaned.strip())

        # 尝试解析 JSON
        try:
            # 提取 JSON 内容（可能被其他文本包围）
            json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
            if json_match:
                profile_data = json.loads(json_match.group())
            else:
                # 如果没有找到 JSON，返回原始内容
                profile_data = {"raw_analysis": cleaned}
        except json.JSONDecodeError:
            profile_data = {"raw_analysis": cleaned}
        
        # 构建返回数据
        response_data = {"customer_profile": profile_data}
        if include_think and think_content:
            response_data["think"] = think_content
        
        return BaseResponse(code=200, msg="success", data=response_data)
    except Exception as e:
        return BaseResponse(code=500, msg=f"请求失败: {str(e)}", data={})


@app.post("/analyze-blockers", summary="分析业务沟通中的卡点与维系策略", response_model=BaseResponse)
async def analyze_blockers(
    communication_record: str = Form(..., description="业务跟进沟通记录内容"),
    include_think: bool = Form(False, description="是否返回模型的思考内容")
):
    """
    根据业务跟进沟通记录，分析当前技术/商业卡点，并给出客户维系策略。

    - **communication_record**: 业务跟进沟通记录内容（支持多行文本）
    - **include_think**: 是否返回模型的思考内容 (默认: false)

    返回结果为 JSON 格式，包含卡点分析和维系策略。
    """
    record_text = communication_record
    if not record_text.strip():
        return BaseResponse(code=400, msg="communication_record 不能为空", data={})

    question = f"请分析以下业务跟进沟通记录：\n{record_text}"

    try:
        client = load_model_client(PROVIDER, MODEL_NAME)
        answer = client.ask_with_system(BLOCKER_ANALYSIS_SYSTEM_PROMPT, question)

        think_content, main_content = extract_think_content(answer)

        # 剥离 markdown 代码块包裹 (```json ... ``` 或 ``` ... ```)
        cleaned = re.sub(r'^```(?:json)?\s*\n?', '', main_content.strip())
        cleaned = re.sub(r'\n?```\s*$', '', cleaned.strip())

        try:
            json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
            if json_match:
                analysis_data = json.loads(json_match.group())
            else:
                analysis_data = {"raw_analysis": cleaned}
        except json.JSONDecodeError:
            analysis_data = {"raw_analysis": cleaned}

        response_data = {"blockers_analysis": analysis_data}
        if include_think and think_content:
            response_data["think"] = think_content

        return BaseResponse(code=200, msg="success", data=response_data)
    except Exception as e:
        return BaseResponse(code=500, msg=f"请求失败: {str(e)}", data={})


@app.post("/upload", summary="上传文件并提取关键词", response_model=BaseResponse)
async def upload_file(
    file: UploadFile = File(...),
    verbose: bool = Query(False, description="是否在终端输出解析原文")
):
    """
    上传 txt 或 pdf 文件，解析原文内容，提取关键词并保存至服务器。

    - **file**: 上传的文件（支持 .txt 和 .pdf 格式）
    - **verbose**: 是否在终端输出解析后的原文内容 (默认: false)
    """
    try:
        # 读取文件内容
        file_bytes = await file.read()
        filename = file.filename or "unknown"
        ext = os.path.splitext(filename)[1].lower()

        # 根据文件类型解析文本
        if ext == ".txt":
            text = file_bytes.decode("utf-8")
        elif ext == ".pdf":
            pdf_reader = PdfReader(io.BytesIO(file_bytes))
            text = "\n".join(page.extract_text() or "" for page in pdf_reader.pages)
        else:
            return BaseResponse(code=400, msg=f"不支持的文件格式: {ext}，仅支持 .txt 和 .pdf", data={})

        if not text.strip():
            return BaseResponse(code=400, msg="文件内容为空，无法解析", data={})

        # verbose 模式下在终端输出原文
        if verbose:
            print(f"\n{'='*60}")
            print(f"[UPLOAD] 文件: {filename}")
            print(f"{'='*60}")
            print(text)
            print(f"{'='*60}\n")

        # 调用大模型提取关键词
        client = load_model_client(PROVIDER, MODEL_NAME)
        raw_answer = client.ask_with_system(KEYWORD_EXTRACTION_PROMPT, text)
        _, keywords = extract_think_content(raw_answer)
        keywords = keywords.strip()

        # 生成带时间戳的文件名并保存
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        saved_filename = f"{timestamp}_{filename}"
        saved_path = os.path.join(UPLOAD_DIR, saved_filename)

        with open(saved_path, "w", encoding="utf-8") as f:
            f.write(f"## Keywords: {keywords}\n")
            f.write(text)

        return BaseResponse(code=200, msg="success", data={
            "filename": saved_filename,
            "keywords": keywords,
            "char_count": len(text)
        })
    except Exception as e:
        return BaseResponse(code=500, msg=f"文件上传失败: {str(e)}", data={})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
