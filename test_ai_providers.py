#!/usr/bin/env python3
"""
測試 AI 提供者切換功能
"""

import asyncio
import os
import sys
from pathlib import Path

# 將專案根目錄加入 Python 路徑
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import settings
from modules.ai_service import AIService

async def test_ai_providers():
    """測試不同的 AI 提供者"""
    
    print("=== AI 提供者測試 ===")
    print(f"目前使用的 AI 提供者: {settings.AI_PROVIDER}")
    
    # 測試 Gemini
    print("\n1. 測試 Gemini 提供者:")
    try:
        # 暫時切換到 Gemini
        original_provider = settings.AI_PROVIDER
        settings.AI_PROVIDER = "gemini"
        
        ai_service_gemini = AIService()
        sms_result = await ai_service_gemini.generate_sms("夏季促銷活動，全館8折優惠")
        print(f"Gemini 簡訊生成結果: {sms_result}")
        
        query_result = await ai_service_gemini.parse_natural_language_query("查詢最近一個月有購買的客戶")
        print(f"Gemini 查詢生成結果: {query_result}")
        
    except Exception as e:
        print(f"Gemini 測試失敗: {e}")
    
    # 測試 OpenAI（如果有設定 API key）
    print("\n2. 測試 OpenAI 提供者:")
    if settings.OPENAI_API_KEY:
        try:
            settings.AI_PROVIDER = "openai"
            ai_service_openai = AIService()
            
            sms_result = await ai_service_openai.generate_sms("夏季促銷活動，全館8折優惠")
            print(f"OpenAI 簡訊生成結果: {sms_result}")
            
            query_result = await ai_service_openai.parse_natural_language_query("查詢最近一個月有購買的客戶")
            print(f"OpenAI 查詢生成結果: {query_result}")
            
        except Exception as e:
            print(f"OpenAI 測試失敗: {e}")
    else:
        print("未設定 OPENAI_API_KEY，跳過 OpenAI 測試")
    
    # 恢復原始設定
    settings.AI_PROVIDER = original_provider

if __name__ == "__main__":
    asyncio.run(test_ai_providers())