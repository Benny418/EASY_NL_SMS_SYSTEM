import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from modules.ai_service import AIService

class TestAIService:
    """測試AI服務"""
    
    @pytest.fixture
    def ai_service(self):
        """建立測試用的AI服務"""
        return AIService()
    
    @pytest.mark.asyncio
    async def test_generate_sms_success(self, ai_service):
        """測試成功生成簡訊"""
        with patch('google.generativeai.GenerativeModel') as mock_model:
            # 模擬成功的回應
            mock_instance = AsyncMock()
            mock_instance.generate_content_async.return_value.text = "限時優惠！全館8折起，立即選購！"
            mock_model.return_value = mock_instance
            
            result = await ai_service.generate_sms("幫我生成一個週年慶促銷活動的簡訊")
            
            assert result != "超出範圍無法回答"
            assert len(result) <= 70
    
    @pytest.mark.asyncio
    async def test_generate_sms_non_sales(self, ai_service):
        """測試非銷售相關的提示"""
        with patch('google.generativeai.GenerativeModel') as mock_model:
            result = await ai_service.generate_sms("今天天氣如何？")
            assert result == "超出範圍無法回答"
    
    @pytest.mark.asyncio
    async def test_generate_sms_length_limit(self, ai_service):
        """測試簡訊長度限制"""
        with patch('google.generativeai.GenerativeModel') as mock_model:
            # 模擬超過長度的回應
            mock_instance = AsyncMock()
            mock_instance.generate_content_async.return_value.text = "這是一個很長的簡訊內容，超過了70個字的限制，應該要被截斷或重新生成"
            mock_model.return_value = mock_instance
            
            result = await ai_service.generate_sms("測試長度限制", max_length=70)
            
            assert len(result) <= 70
    
    @pytest.mark.asyncio
    async def test_parse_natural_language_query_success(self, ai_service):
        """測試成功解析自然語言查詢"""
        with patch('google.generativeai.GenerativeModel') as mock_model:
            mock_instance = AsyncMock()
            mock_instance.generate_content_async.return_value.text = 'SELECT "CustId", "CustName", "MobileNumber" FROM public."custInfo" LIMIT 10'
            mock_model.return_value = mock_instance
            
            result = await ai_service.parse_natural_language_query("找出前10位客戶")
            
            assert result != "超出範圍無法回答"
            assert "SELECT" in result
            assert "custInfo" in result
    
    @pytest.mark.asyncio
    async def test_parse_natural_language_query_forbidden_keywords(self, ai_service):
        """測試禁止的關鍵字"""
        result = await ai_service.parse_natural_language_query("刪除所有客戶資料")
        assert result == "超出範圍無法回答"
    
    @pytest.mark.asyncio
    async def test_parse_natural_language_query_non_select(self, ai_service):
        """測試非SELECT查詢"""
        with patch('google.generativeai.GenerativeModel') as mock_model:
            mock_instance = AsyncMock()
            mock_instance.generate_content_async.return_value.text = 'DELETE FROM public."custInfo"'
            mock_model.return_value = mock_instance
            
            result = await ai_service.parse_natural_language_query("刪除資料")
            assert result == "超出範圍無法回答"
    
    def test_count_sms_characters(self, ai_service):
        """測試計算簡訊字數"""
        # 測試英文
        assert ai_service.count_sms_characters("Hello") == 5
        
        # 測試中文
        assert ai_service.count_sms_characters("你好") == 2
        
        # 測試混合
        assert ai_service.count_sms_characters("Hello你好") == 7
        
        # 測試標點符號
        assert ai_service.count_sms_characters("Hello, 你好！") == 10
    
    def test_validate_sms_length(self, ai_service):
        """測試驗證簡訊長度"""
        # 測試有效長度
        result = ai_service.validate_sms_length("Hello", 10)
        assert result['is_valid'] is True
        assert result['count'] == 5
        assert result['remaining'] == 5
        
        # 測試超過長度
        result = ai_service.validate_sms_length("Hello World", 5)
        assert result['is_valid'] is False
        assert result['count'] == 11
        assert result['remaining'] == 0
        
        # 測試剛好等於限制
        result = ai_service.validate_sms_length("Hello", 5)
        assert result['is_valid'] is True
        assert result['count'] == 5
        assert result['remaining'] == 0
    
    @pytest.mark.asyncio
    async def test_parse_natural_language_query_with_phone(self, ai_service):
        """測試查詢自動包含電話號碼"""
        with patch('google.generativeai.GenerativeModel') as mock_model:
            mock_instance = AsyncMock()
            mock_instance.generate_content_async.return_value.text = 'SELECT "CustName" FROM public."custInfo"'
            mock_model.return_value = mock_instance
            
            result = await ai_service.parse_natural_language_query("找出所有客戶姓名")
            
            # 應該自動加入電話號碼
            assert "MobileNumber" in result or "mobilenumber" in result.lower()