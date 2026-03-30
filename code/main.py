from fastapi import FastAPI, Query
from pydantic import BaseModel
from utils.load import load_model_client, Provider
import re
import json

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

# 固定配置：使用 OpenAI GPT
PROVIDER = Provider.MINIMAX
MODEL_NAME = "MiniMax-M2.5"

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
        
        # 尝试解析 JSON
        try:
            # 提取 JSON 内容（可能被其他文本包围）
            json_match = re.search(r'\{.*\}', main_content, re.DOTALL)
            if json_match:
                profile_data = json.loads(json_match.group())
            else:
                # 如果没有找到 JSON，返回原始内容
                profile_data = {"raw_analysis": main_content}
        except json.JSONDecodeError:
            profile_data = {"raw_analysis": main_content}
        
        # 构建返回数据
        response_data = {"customer_profile": profile_data}
        if include_think and think_content:
            response_data["think"] = think_content
        
        return BaseResponse(code=200, msg="success", data=response_data)
    except Exception as e:
        return BaseResponse(code=500, msg=f"请求失败: {str(e)}", data={})
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
