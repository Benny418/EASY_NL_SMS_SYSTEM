import pytest
import psycopg2
from modules.db_handler import DatabaseHandler
from config.settings import settings

class TestDatabaseHandler:
    """測試資料庫處理器"""
    
    @pytest.fixture
    def db_handler(self):
        """建立測試用的資料庫處理器"""
        return DatabaseHandler()
    
    def test_connection(self, db_handler):
        """測試資料庫連線"""
        try:
            with db_handler.get_connection() as conn:
                assert conn is not None
        except Exception as e:
            pytest.fail(f"資料庫連線失敗: {e}")
    
    def test_execute_query(self, db_handler):
        """測試執行查詢"""
        try:
            results = db_handler.execute_query("SELECT 1 as test")
            assert len(results) == 1
            assert results[0]['test'] == 1
        except Exception as e:
            pytest.fail(f"查詢執行失敗: {e}")
    
    def test_insert_sms_message(self, db_handler):
        """測試插入簡訊記錄"""
        try:
            sms_key = db_handler.insert_sms_message(
                message_class="TEST",
                message_body="測試簡訊",
                recipient_no="0912345678",
                schedule_date=None
            )
            assert sms_key is not None
            assert sms_key > 0
            
            # 清理測試資料
            db_handler.execute_update(
                "DELETE FROM public.\"smsMessage\" WHERE smskey = %s",
                (sms_key,)
            )
        except Exception as e:
            pytest.fail(f"插入簡訊記錄失敗: {e}")
    
    def test_get_pending_sms_messages(self, db_handler):
        """測試取得待發送簡訊"""
        try:
            # 插入測試資料
            sms_key = db_handler.insert_sms_message(
                message_class="TEST",
                message_body="待發送測試",
                recipient_no="0912345678",
                schedule_date=None
            )
            
            pending = db_handler.get_pending_sms_messages()
            assert isinstance(pending, list)
            
            # 清理測試資料
            db_handler.execute_update(
                "DELETE FROM public.\"smsMessage\" WHERE smskey = %s",
                (sms_key,)
            )
        except Exception as e:
            pytest.fail(f"取得待發送簡訊失敗: {e}")
    
    def test_update_sms_status(self, db_handler):
        """測試更新簡訊狀態"""
        try:
            # 插入測試資料
            sms_key = db_handler.insert_sms_message(
                message_class="TEST",
                message_body="狀態更新測試",
                recipient_no="0912345678",
                schedule_date=None
            )
            
            # 更新狀態
            affected = db_handler.update_sms_status(
                sms_key,
                "00000",
                "發送成功",
                "MSG123"
            )
            assert affected == 1
            
            # 清理測試資料
            db_handler.execute_update(
                "DELETE FROM public.\"smsMessage\" WHERE smskey = %s",
                (sms_key,)
            )
        except Exception as e:
            pytest.fail(f"更新簡訊狀態失敗: {e}")
    
    def test_get_customers_by_query(self, db_handler):
        """測試客戶查詢"""
        try:
            # 測試基本查詢
            results = db_handler.get_customers_by_query(
                'SELECT "CustId", "CustName", "MobileNumber" FROM public."custInfo" LIMIT 5'
            )
            assert isinstance(results, list)
            
            # 測試個資隱碼
            if results:
                customer = results[0]
                if 'CustName' in customer and customer['CustName']:
                    # 檢查姓名是否已隱碼
                    assert '*' in customer['CustName']
                if 'MobileNumber' in customer and customer['MobileNumber']:
                    # 檢查電話是否已隱碼
                    assert '*' in customer['MobileNumber']
                    
        except Exception as e:
            pytest.fail(f"客戶查詢失敗: {e}")
    
    def test_security_check(self, db_handler):
        """測試安全性檢查"""
        try:
            # 測試禁止的關鍵字
            with pytest.raises(ValueError):
                db_handler.get_customers_by_query('DROP TABLE public."custInfo"')
            
            with pytest.raises(ValueError):
                db_handler.get_customers_by_query('DELETE FROM public."custInfo"')
                
        except Exception as e:
            pytest.fail(f"安全性檢查失敗: {e}")
    
    def test_get_sms_statistics(self, db_handler):
        """測試取得簡訊統計"""
        try:
            stats = db_handler.get_sms_statistics()
            assert isinstance(stats, dict)
            assert 'total_count' in stats
            assert 'sent_count' in stats
            assert 'pending_count' in stats
            assert 'success_count' in stats
        except Exception as e:
            pytest.fail(f"取得簡訊統計失敗: {e}")