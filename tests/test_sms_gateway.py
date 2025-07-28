import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from modules.sms_gateway import SMSGateway

class TestSMSGateway:
    """測試SMS Gateway"""
    
    @pytest.fixture
    def sms_gateway(self):
        """建立測試用的SMS Gateway"""
        return SMSGateway()
    
    def test_build_xml_request(self, sms_gateway):
        """測試建立XML請求"""
        recipients = ["0912345678", "0987654321"]
        message = "測試訊息"
        
        xml = sms_gateway._build_xml_request(recipients, message)
        
        assert "SmsSubmitReq" in xml
        assert "SysId" in xml
        assert "SrcAddress" in xml
        assert "0912345678" in xml
        assert "0987654321" in xml
        assert "測試訊息" not in xml  # 應該被base64編碼
        
    def test_parse_xml_response(self, sms_gateway):
        """測試解析XML回應"""
        xml_response = '''<?xml version="1.0" encoding="UTF-8"?>
<SubmitRes>
    <ResultCode>00000</ResultCode>
    <ResultText>Message accepted for processing.</ResultText>
    <MessageId>12340001</MessageId>
</SubmitRes>'''
        
        result = sms_gateway._parse_xml_response(xml_response)
        
        assert result['ResultCode'] == '00000'
        assert result['ResultText'] == 'Message accepted for processing.'
        assert result['MessageId'] == '12340001'
    
    @pytest.mark.asyncio
    async def test_send_sms_success(self, sms_gateway):
        """測試成功發送簡訊"""
        with patch('httpx.AsyncClient') as mock_client:
            # 模擬成功的HTTP回應
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.text = '''<?xml version="1.0" encoding="UTF-8"?>
<SubmitRes>
    <ResultCode>00000</ResultCode>
    <ResultText>Message accepted for processing.</ResultText>
    <MessageId>12340001</MessageId>
</SubmitRes>'''
            
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            success, result = await sms_gateway.send_sms(
                ["0912345678"], 
                "測試訊息"
            )
            
            assert success is True
            assert result['result_code'] == '00000'
            assert result['message_id'] == '12340001'
    
    @pytest.mark.asyncio
    async def test_send_sms_http_error(self, sms_gateway):
        """測試HTTP錯誤"""
        with patch('httpx.AsyncClient') as mock_client:
            # 模擬HTTP錯誤
            mock_response = AsyncMock()
            mock_response.status_code = 500
            mock_response.text = "Server Error"
            
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            success, result = await sms_gateway.send_sms(
                ["0912345678"], 
                "測試訊息"
            )
            
            assert success is False
            assert result['result_code'] == 'HTTP_ERROR'
    
    @pytest.mark.asyncio
    async def test_send_sms_network_error(self, sms_gateway):
        """測試網路錯誤"""
        with patch('httpx.AsyncClient') as mock_client:
            # 模擬網路錯誤
            mock_client.return_value.__aenter__.return_value.post.side_effect = Exception("Network error")
            
            success, result = await sms_gateway.send_sms(
                ["0912345678"], 
                "測試訊息"
            )
            
            assert success is False
            assert result['result_code'] == 'NETWORK_ERROR'
    
    def test_validate_phone_numbers(self, sms_gateway):
        """測試驗證電話號碼"""
        # 測試有效號碼
        valid_numbers = ["0912345678", "0987654321"]
        is_valid, phones = sms_gateway.validate_phone_numbers(valid_numbers)
        assert is_valid is True
        assert phones == valid_numbers
        
        # 測試無效號碼
        invalid_numbers = ["123456789", "091234567890", "abc123"]
        is_valid, phones = sms_gateway.validate_phone_numbers(invalid_numbers)
        assert is_valid is False
        assert phones == []
        
        # 測試混合號碼
        mixed_numbers = ["0912345678", "123456789", "0987654321"]
        is_valid, phones = sms_gateway.validate_phone_numbers(mixed_numbers)
        assert is_valid is False
        assert phones == ["0912345678", "0987654321"]
    
    def test_format_phone_list(self, sms_gateway):
        """測試格式化電話清單"""
        # 測試逗號分隔
        phone_string = "0912345678,0987654321"
        result = sms_gateway.format_phone_list(phone_string)
        assert result == ["0912345678", "0987654321"]
        
        # 測試分號分隔
        phone_string = "0912345678;0987654321"
        result = sms_gateway.format_phone_list(phone_string)
        assert result == ["0912345678", "0987654321"]
        
        # 測試混合分隔
        phone_string = "0912345678,0987654321;0923456789"
        result = sms_gateway.format_phone_list(phone_string)
        assert result == ["0912345678", "0987654321", "0923456789"]
        
        # 測試空白處理
        phone_string = " 0912345678 , 0987654321 "
        result = sms_gateway.format_phone_list(phone_string)
        assert result == ["0912345678", "0987654321"]
        
        # 測試空字串
        phone_string = ""
        result = sms_gateway.format_phone_list(phone_string)
        assert result == []