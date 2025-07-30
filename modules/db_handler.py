import psycopg2
import psycopg2.extras
from typing import List, Dict, Any, Optional, Tuple
import logging
from contextlib import contextmanager
from config.settings import settings

logger = logging.getLogger(__name__)

class DatabaseHandler:
    """資料庫操作處理類別"""
    
    def __init__(self):
        self.connection_params = {
            'host': settings.DB_HOST,
            'port': settings.DB_PORT,
            'database': settings.DB_NAME,
            'user': settings.DB_USER,
            'password': settings.DB_PASSWORD
        }
    
    @contextmanager
    def get_connection(self):
        """取得資料庫連線的上下文管理器"""
        conn = None
        try:
            conn = psycopg2.connect(**self.connection_params)
            yield conn
        except Exception as e:
            logger.error(f"資料庫連線錯誤: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    
    @contextmanager
    def get_cursor(self, cursor_factory=None):
        """取得資料庫游標的上下文管理器"""
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=cursor_factory)
            try:
                yield cursor
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error(f"資料庫操作錯誤: {e}")
                raise
            finally:
                cursor.close()
    
    def execute_query(self, query: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
        """執行查詢並返回結果"""
        with self.get_cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()
    
    def execute_update(self, query: str, params: Optional[Tuple] = None) -> int:
        """執行更新操作並返回影響的筆數"""
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.rowcount
    
    def execute_insert(self, query: str, params: Optional[Tuple] = None) -> Optional[int]:
        """執行插入操作並返回插入的ID"""
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            cursor.execute("SELECT LASTVAL()")
            return cursor.fetchone()[0]
    
    def get_customers_by_query(self, sql_query: str) -> List[Dict[str, Any]]:
        """根據SQL查詢取得客戶資料"""
        try:
            # 檢查查詢是否只涉及允許的表格
            allowed_tables = ['cust_info', 'order_master', 'order_detail']
            query_lower = sql_query.lower()
            
            # 基本的安全檢查
            forbidden_keywords = ['drop ', 'delete ', 'update ', 'insert ', 'alter ', 'create ', 'truncate ']
            for keyword in forbidden_keywords:
                if keyword in query_lower:
                    raise ValueError(f"不允許的操作: {keyword}")
            
            # 執行查詢
            results = self.execute_query(sql_query)
            
            # 處理個資隱碼
            for row in results:
                if 'cust_name' in row and row['cust_name']:
                    name = row['cust_name']
                    if len(name) > 2:
                        row['cust_name'] = name[0] + '*' * (len(name) - 2) + name[-1]
                    else:
                        row['cust_name'] = name[0] + '*'
                
                if 'mobile_number' in row and row['mobile_number']:
                    phone = row['mobile_number']
                    if len(phone) >= 10:
                        row['mobile_number'] = phone[:3] + '****' + phone[-3:]
                
                if 'home_number' in row and row['home_number']:
                    home = row['home_number']
                    if len(home) >= 8:
                        row['home_number'] = home[:2] + '****' + home[-2:]
                
                if 'address' in row and row['address']:
                    address = row['address']
                    if len(address) > 6:
                        mid = len(address) // 2
                        mask_len = min(4, len(address) - 6)
                        row['address'] = address[:mid-2] + '*' * mask_len + address[mid+2:]
            
            return results
            
        except Exception as e:
            logger.error(f"查詢客戶資料錯誤: {e}")
            raise
    
    def insert_sms_message(self, message_class: str, message_body: str, 
                          recipient_no: str, schedule_date: Optional[str] = None, 
                          send_date: Optional[str] = None) -> int:
        """插入簡訊發送記錄"""
        query = """
            INSERT INTO public.sms_message 
            (create_date, message_class, message_body, recipient_no, schedule_date, send_date)
            VALUES (NOW(), %s, %s, %s, %s, %s)
            RETURNING smskey
        """
        params = (message_class, message_body, recipient_no, schedule_date, send_date)
        return self.execute_insert(query, params)
    
    def get_pending_sms_messages(self) -> List[Dict[str, Any]]:
        """取得待發送的簡訊"""
        query = """
            SELECT smskey, message_body, recipient_no, schedule_date
            FROM public.sms_message
            WHERE send_date IS NULL
            AND (schedule_date IS NULL OR schedule_date <= NOW())
            ORDER BY create_date ASC
        """
        return self.execute_query(query)
    
    def update_sms_status(self, smskey: int, return_code: str, 
                         return_message: str, message_id: Optional[str] = None):
        """更新簡訊發送狀態"""
        query = """
            UPDATE public.sms_message
            SET send_date = NOW(),
                return_code = %s,
                return_message = %s,
                message_id = %s
            WHERE smskey = %s
        """
        params = (return_code, return_message, message_id, smskey)
        self.execute_update(query, params)
    
    def get_sms_statistics(self) -> Dict[str, Any]:
        """取得簡訊發送統計"""
        query = """
            SELECT 
                COUNT(*) as total_count,
                COUNT(CASE WHEN send_date IS NOT NULL THEN 1 END) as sent_count,
                COUNT(CASE WHEN send_date IS NULL THEN 1 END) as pending_count,
                COUNT(CASE WHEN return_code = '00000' THEN 1 END) as success_count
            FROM public.sms_message
        """
        result = self.execute_query(query)
        return result[0] if result else {}
    
    def get_phone_numbers_by_customer_ids(self, customer_ids: List[int]) -> List[str]:
        """根據客戶ID列表取得電話號碼"""
        if not customer_ids:
            return []
        
        query = """
            SELECT mobile_number 
            FROM public.cust_info 
            WHERE cust_id = ANY(%s) 
            AND mobile_number IS NOT NULL 
            AND mobile_number != ''
            AND refuse != true
        """
        results = self.execute_query(query, (customer_ids,))
        return [row['mobile_number'] for row in results]
    
    def batch_insert_sms_messages(self, messages: List[Dict[str, Any]]) -> List[int]:
        """批次插入簡訊發送記錄"""
        if not messages:
            return []
        
        sms_keys = []
        with self.get_cursor() as cursor:
            for message in messages:
                query = """
                    INSERT INTO public.sms_message 
                    (create_date, message_class, message_body, recipient_no, schedule_date)
                    VALUES (NOW(), %s, %s, %s, %s)
                    RETURNING smskey
                """
                params = (
                    message['message_class'],
                    message['message_body'],
                    message['recipient_no'],
                    message.get('schedule_date')
                )
                cursor.execute(query, params)
                cursor.execute("SELECT LASTVAL()")
                sms_keys.append(cursor.fetchone()[0])
        
        return sms_keys

# 建立全域實例
db_handler = DatabaseHandler()