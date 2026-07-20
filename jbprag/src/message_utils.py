from typing import List, Union, Dict, Any
import logging
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage, AIMessage
from src.api_models import ChatMessage
from src.utils import get_visual_llm

logger = logging.getLogger(__name__)

def openai_to_langchain(messages: List[Union[ChatMessage, Dict[str, Any]]]) -> List[AnyMessage]:
    lc_messages = []
    for msg in messages:
        if isinstance(msg, dict):
            role = msg.get("role", "user")
            content = msg.get("content")
            if content is None:
                content = ""
        else:
            role = msg.role
            content = msg.content
            if content is None:
                content = ""
            
        if role == "system":
            lc_messages.append(SystemMessage(content=content))
        elif role == "user":
            lc_messages.append(HumanMessage(content=content))
        elif role in ["assistant", "ai"]:
            lc_messages.append(AIMessage(content=content))
        else:
            lc_messages.append(HumanMessage(content=content))
    return lc_messages

async def preprocess_multimodal_messages(messages: List[AnyMessage]) -> List[AnyMessage]:
    """Preprocess messages: if any HumanMessage contains an image_url,
    invoke the visual LLM to convert the image to a text description,
    and replace the message content with a text-only representation.
    """
    preprocessed = []
    for msg in messages:
        is_human = isinstance(msg, HumanMessage)
        content = getattr(msg, "content", "")
        
        if is_human and isinstance(content, list):
            has_image = False
            text_parts = []
            image_parts = []
            for part in content:
                if isinstance(part, dict):
                    if part.get("type") == "image_url":
                        has_image = True
                        image_parts.append(part)
                    elif part.get("type") == "text":
                        text_parts.append(part.get("text", ""))
                else:
                    text_parts.append(str(part))
            
            if has_image:
                original_text = "\n".join(text_parts).strip()
                logger.info("Detected image in user query. Invoking visual LLM for description...")
                try:
                    vllm = get_visual_llm()
                    vllm_messages = [
                        SystemMessage(content=(
                            "你是一个专业的IC版图设计与DRC分析助手。请分析用户提供的图片（版图截图或DRC错误窗口），"
                            "识别并提取出所有可读的版图图层（如 M1, Metal1, Poly 等）、DRC 规则名称/规则代码（如 M1.SP.1 等）、"
                            "间距或宽度数值、坐标以及报错文本。请用中文提供一个详尽的视觉特征与错误描述摘要，"
                            "这将作为检索文本用于从数据库中召回匹配的DRC设计规则文档。请直接输出分析结果，不要有多余废话。"
                        )),
                        HumanMessage(content=content)
                    ]
                    response = await vllm.ainvoke(vllm_messages)
                    description = response.content.strip()
                    logger.info("Visual LLM description: %s", description)
                    
                    new_text = f"{original_text}\n\n[版图截图描述与DRC错误提取]:\n{description}"
                    msg.content = new_text
                except Exception as e:
                    logger.error("Failed to process image with visual LLM: %s", e, exc_info=True)
                    msg.content = original_text
            else:
                msg.content = "\n".join(text_parts).strip()
                
        preprocessed.append(msg)
    return preprocessed

def get_last_ai_content(messages: list) -> str:
    for msg in reversed(messages):
        msg_type = getattr(msg, "type", None)
        if msg_type == "ai" or msg.__class__.__name__ == "AIMessage":
            return msg.content
    return ""
