import httpx
import base64
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional, Tuple
import logging
from config.settings import settings

logger = logging.getLogger(__name__)

class SMSGateway:
    """SMS Gateway 操作類別"""
    
    def __init__(self):
        self.gateway_url = settings.SMS_GATEWAY_URL
        self.sys_id = settings.SMS_SYS_ID
        self.src_address = settings.SMS_SRC_ADDRESS
        self.dr_flag = settings.SMS_DR_FLAG
        self.first_fail_flag = settings.SMS_FIRST_FAIL_FLAG
    
    def _build_xml_request(self, recipients: List[str], message: str) -> str:
        """建立XML格式的請求"""
        # 將訊息編碼為base64
        message_base64 = base64.b64encode(message.encode('utf-8')).decode('utf-8')
        
        # 建立XML結構
        xml_request = f'''<?xml version="1.0" encoding="UTF-8"?>
<SmsSubmitReq>
    <SysId>{self.sys_id}</SysId>
    <SrcAddress>{self.src_address}</SrcAddress>'''
        
        # 加入多個收件人
        for recipient in recipients:
            xml_request += f'''
    <DestAddress>{recipient.strip()}</DestAddress>'''
        
        xml_request += f'''
    <SmsBody>{message_base64}</SmsBody>
    <DrFlag>{str(self.dr_flag).lower()}</DrFlag>
    <FirstFailFlag>{str(self.first_fail_flag).lower()}</FirstFailFlag>
</SmsSubmitReq>'''
        
        return xml_request
    
    def _parse_xml_response(self, xml_response: str) -> Dict[str, str]:
        """解析XML格式的回應"""
        try:
            root = ET.fromstring(xml_response)
            
            result = {}
            for child in root:
                result[child.tag] = child.text
            
            return result
        except ET.ParseError as e:
            logger.error(f"XML解析錯誤: {e}")
            raise
    
    async def send_sms(self, recipients: List[str], message: str) -> Tuple[bool, Dict[str, str]]:
        """發送簡訊"""
        try:
            # 建立XML請求
            xml_request = self._build_xml_request(recipients, message)
            
            logger.info(f"發送簡訊請求: {recipients}")
            logger.debug(f"XML請求內容: {xml_request}")
            
            # 發送HTTP請求
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.gateway_url,
                    content=xml_request,
                    headers={'Content-Type': 'application/xml'}
                )
                
                if response.status_code == 200:
                    xml_response = response.text
                    logger.debug(f"XML回應內容: {xml_response}")
                    
                    # 解析回應
                    result = self._parse_xml_response(xml_response)
                    
                    # 檢查結果
                    result_code = result.get('ResultCode', '')
                    result_text = result.get('ResultText', '')
                    message_id = result.get('MessageId', '')
                    
                    success = result_code == '00000'
                    
                    logger.info(f"簡訊發送結果: {result_code} - {result_text}")
                    
                    return success, {
                        'result_code': result_code,
                        'result_text': result_text,
                        'message_id': message_id
                    }
                else:
                    logger.error(f"HTTP錯誤: {response.status_code}")
                    return False, {
                        'result_code': 'HTTP_ERROR',
                        'result_text': f'HTTP錯誤: {response.status_code}',
                        'message_id': ''
                    }
                    
        except httpx.RequestError as e:
            logger.error(f"網路請求錯誤: {e}")
            return False, {
                'result_code': 'NETWORK_ERROR',
                'result_text': f'網路請求錯誤: {str(e)}',
                'message_id': ''
            }
        except Exception as e:
            logger.error(f"發送簡訊錯誤: {e}")
            return False, {
                'result_code': 'SYSTEM_ERROR',
                'result_text': f'系統錯誤: {str(e)}',
                'message_id': ''
            }
    
    def validate_phone_numbers(self, phone_numbers: List[str]) -> Tuple[bool, List[str]]:
        """驗證電話號碼格式"""
        valid_numbers = []
        invalid_numbers = []
        
        for phone in phone_numbers:
            # 移除空白
            phone = phone.strip()
            
            # 檢查格式（台灣手機號碼）
            if phone.startswith('09') and len(phone) == 10 and phone.isdigit():
                valid_numbers.append(phone)
            else:
                invalid_numbers.append(phone)
        
        if invalid_numbers:
            logger.warning(f"無效的電話號碼: {invalid_numbers}")
        
        return len(invalid_numbers) == 0, valid_numbers
    
    def format_phone_list(self, phone_string: str) -> List[str]:
        """將電話字串格式化為清單"""
        # 支援逗號或分號分隔
        separators = [',', ';']
        phone_list = [phone_string]
        
        for sep in separators:
            new_list = []
            for phone in phone_list:
                new_list.extend(phone.split(sep))
            phone_list = new_list
        
        # 清理並過濾空白
        phone_list = [phone.strip() for phone in phone_list if phone.strip()]
        
        return phone_list

# 建立全域實例
sms_gateway = SMSGateway()