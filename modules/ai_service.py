import google.generativeai as genai
from typing import Optional, Dict, Any
import logging
import re
from config.settings import settings

logger = logging.getLogger(__name__)

class AIService:
    """AI服務類別，提供簡訊生成和自然語言查詢功能"""
    
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-pro')
    
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
1. 簡訊長度不超過{max_length}個字（包含標點符號）
2. 內容要有吸引力且符合台灣用語習慣
3. 必須是銷售或促銷相關內容
4. 不要包含任何個人資訊
5. 使用繁體中文

使用者需求：{prompt}

請直接回應簡訊內容，不要包含其他說明。"""

            response = await self.model.generate_content_async(system_prompt)
            sms_content = response.text.strip()
            
            # 檢查長度
            if len(sms_content) > max_length:
                # 如果超過長度，要求重新生成
                retry_prompt = f"{system_prompt}\n\n請將以下內容縮短至{max_length}字以內：{sms_content}"
                retry_response = await self.model.generate_content_async(retry_prompt)
                sms_content = retry_response.text.strip()
            
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
1. custInfo (客戶基本資料表):
   - CustId: 客戶編號 (主鍵)
   - CustName: 客戶姓名
   - Gender: 性別
   - MobileNumber: 行動電話
   - HomeNumber: 住家電話
   - Address: 地址
   - Age: 年齡
   - Birthday: 生日
   - Refuse: 是否拒絕電話聯絡 (boolean)
   - CreateDate: 建立日期

2. orderMaster (訂單主檔):
   - OrderNo: 訂單編號 (主鍵)
   - OrderDate: 訂購日期
   - CustId: 客戶編號 (外鍵)
   - Amount: 訂單金額
   - PayMethod: 付款方式 (1:現金, 2:信用卡, 3:轉帳)
   - DeliveryAddress: 送貨地址
   - Receiver: 收貨人
   - ReceiverPhone: 收貨人電話
   - OrderType: 訂單類別 (1:一般, 2:預購)
   - TakerId: 接單人員編號
   - CreateDate: 建立日期

3. orderDetail (訂單明細):
   - rowkey: 序號 (主鍵)
   - OrderNo: 訂單編號 (外鍵)
   - ProductId: 產品編號
   - ProductTitle: 產品名稱
   - UnitPrice: 單價
   - Qty: 數量
   - BatchNo: 批號

限制：
- 只能查詢上述三個表格
- 只能使用SELECT語句
- 必須返回客戶的電話號碼
- 查詢結果應包含客戶基本資訊

請直接回應SQL查詢語句，不要包含其他說明。

使用者查詢：""" + natural_query

            response = await self.model.generate_content_async(system_prompt)
            sql_query = response.text.strip()
            
            # 清理SQL查詢
            sql_query = sql_query.replace('```sql', '').replace('```', '').strip()
            
            # 基本驗證
            if not sql_query.upper().startswith('SELECT'):
                return "超出範圍無法回答"
            
            # 檢查是否只涉及允許的表格
            allowed_tables = ['custInfo', 'orderMaster', 'orderDetail']
            for table in allowed_tables:
                if table not in sql_query and table.lower() not in sql_query.lower():
                    continue
            
            # 確保查詢包含電話號碼
            if 'MobileNumber' not in sql_query and 'mobilenumber' not in sql_query.lower():
                # 自動加入電話號碼
                if 'FROM "custInfo"' in sql_query:
                    sql_query = sql_query.replace('SELECT', 'SELECT "MobileNumber", ')
                elif 'from custinfo' in sql_query.lower():
                    sql_query = sql_query.replace('select', 'SELECT "MobileNumber", ')
            
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