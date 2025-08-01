import google.generativeai as genai
import openai
from typing import Optional, Dict, Any
import logging
import re
from abc import ABC, abstractmethod
from config.settings import settings

logger = logging.getLogger(__name__)

class AIProvider(ABC):
    """AI提供者抽象基類"""
    
    @abstractmethod
    async def generate_content_async(self, prompt: str) -> str:
        """生成內容"""
        pass

class GeminiProvider(AIProvider):
    """Gemini AI提供者"""
    
    def __init__(self, api_key: str, model: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)
    
    async def generate_content_async(self, prompt: str) -> str:
        """使用Gemini生成內容"""
        response = await self.model.generate_content_async(prompt)
        return response.text.strip()

class OpenAIProvider(AIProvider):
    """OpenAI提供者"""
    
    def __init__(self, api_key: str, base_url: str, model: str):
        if not api_key:
            raise ValueError("OpenAI API key is required")
        self.client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model
    
    async def generate_content_async(self, prompt: str) -> str:
        """使用OpenAI生成內容"""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000
        )
        return response.choices[0].message.content.strip()

class AIService:
    """AI服務類別，提供簡訊生成和自然語言查詢功能"""
    
    def __init__(self):
        self.provider = self._create_provider()
    
    def _create_provider(self) -> AIProvider:
        """根據設定建立對應的AI提供者"""
        provider_type = settings.AI_PROVIDER.lower()
        
        if provider_type == "gemini":
            return GeminiProvider(
                api_key=settings.GEMINI_API_KEY,
                model=settings.GEMINI_MODEL
            )
        elif provider_type == "openai":
            return OpenAIProvider(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_API_BASE,
                model=settings.OPENAI_MODEL
            )
        else:
            raise ValueError(f"不支援的AI提供者: {provider_type}")
    
    async def generate_sms(self, prompt: str, max_length: int = 70) -> str:
        """使用AI生成簡訊內容"""
        try:
            # 檢查是否為銷售相關的提示
            sales_keywords = ['銷售', '促銷', '優惠', '折扣', '特價', '活動', '推廣', '行銷', '廣告', '推銷']
            is_sales_related = any(keyword in prompt.lower() for keyword in sales_keywords)
            
            if not is_sales_related:
                return "超出範圍無法回答"
            
            # 建立提示
            system_prompt = f"""你是一個專業的簡訊文案撰寫助手，請根據使用者的需求生成簡潔有力的促銷簡訊。
要求：
1. 簡訊長度不超過{max_length}個字（包含標點符號），但不得太簡短或少於{max_length-15}個字
2. 內容要有吸引力且符合台灣用語習慣
3. 必須是銷售或促銷相關內容
4. 不要包含任何個人資訊
5. 使用繁體中文
6. 必需包含公司品牌名稱【健康GG關心您】

使用者需求：{prompt}

請直接回應簡訊內容，不要包含其他說明。"""

            sms_content = await self.provider.generate_content_async(system_prompt)
            
            # 檢查長度
            if len(sms_content) > max_length:
                # 如果超過長度，要求重新生成
                retry_prompt = f"{system_prompt}\n\n請將以下內容縮短至{max_length}字以內：{sms_content}"
                sms_content = await self.provider.generate_content_async(retry_prompt)
            
            # 再次檢查長度
            if len(sms_content) > max_length:
                sms_content = sms_content[:max_length]
            
            return sms_content
            
        except Exception as e:
            logger.error(f"AI生成簡訊錯誤: {e}")
            return "生成簡訊時發生錯誤，請稍後再試"
    
    async def parse_natural_language_query(self, natural_query: str) -> str:
        """將自然語言轉換為SQL查詢"""
        try:
            # 檢查查詢是否超出範圍
            forbidden_keywords = ['刪除', '更新', '修改', '新增', '插入', '刪掉', '改掉', '增加']
            for keyword in forbidden_keywords:
                if keyword in natural_query:
                    return "超出範圍無法回答"
            
            # 建立提示
            system_prompt = """你是一個SQL查詢生成助手，請將使用者的自然語言查詢轉換為PostgreSQL查詢語句。

資料庫結構：
1. cust_info (客戶基本資料表):
   - cust_id: 客戶編號 (主鍵)
   - cust_name: 客戶姓名
   - gender: 性別
   - mobile_number: 行動電話
   - home_number: 住家電話
   - address: 地址
   - age: 年齡
   - birthday: 生日
   - refuse: 是否拒絕電話聯絡 (boolean)
   - create_date: 建立日期

2. order_master (訂單主檔):
   - order_no: 訂單編號 (主鍵)
   - order_date: 訂購日期
   - cust_id: 客戶編號 (外鍵)
   - amount: 訂單金額
   - pay_method: 付款方式 (1:現金, 2:信用卡, 3:轉帳)
   - delivery_address: 送貨地址
   - receiver: 收貨人
   - receiver_phone: 收貨人電話
   - order_type: 訂單類別 (1:一般, 2:預購)
   - taker_id: 接單人員編號
   - create_date: 建立日期

3. order_detail (訂單明細):
   - rowkey: 序號 (主鍵)
   - order_no: 訂單編號 (外鍵)
   - product_id: 產品編號
   - product_title: 產品名稱
   - unit_price: 單價
   - qty: 數量
   - batch_no: 批號

限制：
- 只能查詢上述三個表格
- 只能使用SELECT語句
- 必須返回客戶的電話號碼
- 查詢結果應包含客戶基本資訊
- 依照系統提示及使用者查詢的提示直接生成SQL查詢語句，勿做額外多餘的假設
- 查詢結果要避免同一個客戶若多筆資料

請直接回應SQL查詢語句，不要包含其他說明。

使用者查詢：""" + natural_query

            sql_query = await self.provider.generate_content_async(system_prompt)
            
            # 清理SQL查詢
            sql_query = sql_query.replace('```sql', '').replace('```', '').strip()
            
            # 基本驗證
            if not sql_query.upper().startswith('SELECT'):
                return "超出範圍無法回答"
            
            # 檢查是否只涉及允許的表格
            allowed_tables = ['cust_info', 'order_master', 'order_detail']
            for table in allowed_tables:
                if table not in sql_query and table.lower() not in sql_query.lower():
                    continue
            
            # 確保查詢包含電話號碼
            if 'mobile_number' not in sql_query:
                # 自動加入電話號碼
                if 'FROM cust_info' in sql_query:
                    sql_query = sql_query.replace('SELECT', 'SELECT mobile_number, ')
            
            return sql_query
            
        except Exception as e:
            logger.error(f"自然語言查詢錯誤: {e}")
            return "超出範圍無法回答"
    
    def count_sms_characters(self, text: str) -> int:
        """計算簡訊字數（中文、英文、標點都算1個字）"""
        return len(text)
    
    def validate_sms_length(self, text: str, max_length: int = 70) -> Dict[str, Any]:
        """驗證簡訊長度"""
        char_count = self.count_sms_characters(text)
        return {
            'count': char_count,
            'is_valid': char_count <= max_length,
            'max_length': max_length,
            'remaining': max(max_length - char_count, 0)
        }

# 建立全域實例
ai_service = AIService()
