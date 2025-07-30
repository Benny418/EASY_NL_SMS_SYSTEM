from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
import uvicorn
import logging
import asyncio
from datetime import datetime
from typing import List, Optional
import os
import json

# 導入模組
from modules.db_handler import db_handler
from modules.sms_gateway import sms_gateway
from modules.ai_service import ai_service
from config.settings import settings

# 設定日誌
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(settings.LOG_FILE),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用程式生命週期管理"""
    # 啟動時執行
    logger.info("簡訊發送系統啟動")
    task = asyncio.create_task(scheduled_task())
    
    yield
    
    # 關閉時執行
    logger.info("簡訊發送系統關閉")
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

# 建立FastAPI應用程式
app = FastAPI(
    title="簡訊發送系統",
    description="一頁式簡訊發送應用程式",
    version="1.0.0",
    lifespan=lifespan
)

# 設定靜態檔案和模板
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """主頁面"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/generate-sms")
async def generate_sms(
    prompt: str = Form(...),
    max_length: int = Form(70)
):
    """AI生成簡訊內容"""
    try:
        if max_length > settings.SMS_MAX_LENGTH_EXTENDED:
            max_length = settings.SMS_MAX_LENGTH_EXTENDED
        
        sms_content = await ai_service.generate_sms(prompt, max_length)
        
        # 檢查是否為超出範圍的回應
        if sms_content == "超出範圍無法回答":
            return {
                "success": False,
                "message": "超出範圍無法回答",
                "content": ""
            }
        
        # 計算字數
        char_info = ai_service.validate_sms_length(sms_content, max_length)
        
        return {
            "success": True,
            "content": sms_content,
            "char_count": char_info['count'],
            "is_valid": char_info['is_valid'],
            "max_length": max_length,
            "remaining": char_info['remaining']
        }
        
    except Exception as e:
        logger.error(f"生成簡訊錯誤: {e}")
        return {
            "success": False,
            "message": str(e),
            "content": ""
        }

@app.post("/api/validate-sms")
async def validate_sms(
    content: str = Form(...),
    max_length: int = Form(70)
):
    """驗證簡訊長度"""
    try:
        if max_length > settings.SMS_MAX_LENGTH_EXTENDED:
            max_length = settings.SMS_MAX_LENGTH_EXTENDED
        
        char_info = ai_service.validate_sms_length(content, max_length)
        
        return {
            "success": True,
            "char_count": char_info['count'],
            "is_valid": char_info['is_valid'],
            "max_length": max_length,
            "remaining": char_info['remaining']
        }
        
    except Exception as e:
        logger.error(f"驗證簡訊長度錯誤: {e}")
        return {
            "success": False,
            "message": str(e)
        }

@app.post("/api/parse-query")
async def parse_query(
    query: str = Form(...)
):
    """解析自然語言查詢"""
    try:
        sql_query = await ai_service.parse_natural_language_query(query)
        
        # 檢查是否為超出範圍的回應
        if sql_query == "超出範圍無法回答":
            return {
                "success": False,
                "message": "超出範圍無法回答",
                "sql": ""
            }
        
        return {
            "success": True,
            "sql": sql_query
        }
        
    except Exception as e:
        logger.error(f"解析查詢錯誤: {e}")
        return {
            "success": False,
            "message": str(e),
            "sql": ""
        }

@app.post("/api/query-customers")
async def query_customers(
    sql_query: str = Form(...)
):
    """執行客戶查詢"""
    try:
        results = db_handler.get_customers_by_query(sql_query)
        
        return {
            "success": True,
            "data": results,
            "count": len(results)
        }
        
    except Exception as e:
        logger.error(f"查詢客戶錯誤: {e}")
        return {
            "success": False,
            "message": str(e),
            "data": [],
            "count": 0
        }

@app.post("/api/schedule-sms")
async def schedule_sms(
    message_class: str = Form(...),
    message_body: str = Form(...),
    extra_recipients: str = Form(""),
    selected_customer_ids: str = Form("[]"),
    schedule_date: Optional[str] = Form(None)
):
    """排程簡訊發送"""
    try:        
        # 驗證簡訊長度
        char_info = ai_service.validate_sms_length(message_body)
        if not char_info['is_valid']:
            return {
                "success": False,
                "message": f"簡訊長度超過限制（{char_info['max_length']}字）"
            }
        
        # 解析客戶ID和額外收件人
        try:
            customer_ids = json.loads(selected_customer_ids)
            #customer_ids = [int(id) for id in customer_ids]
        except:
            customer_ids = []
        
        # 取得選擇客戶的電話號碼
        customer_phones = db_handler.get_phone_numbers_by_customer_ids(customer_ids)
        
        # 處理額外收件人
        extra_phones = []
        if extra_recipients.strip():
            extra_phones = sms_gateway.format_phone_list(extra_recipients)
        
        # 合併所有電話號碼並去重
        all_phones = list(set(customer_phones + extra_phones))
        
        if not all_phones:
            return {
                "success": False,
                "message": "沒有有效的收件人"
            }
        
        # 驗證電話號碼
        is_valid, valid_phones = sms_gateway.validate_phone_numbers(all_phones)
        
        if not valid_phones:
            return {
                "success": False,
                "message": "沒有有效的電話號碼"
            }
        
        # 解析排程日期
        schedule_dt = None
        if schedule_date:
            try:
                schedule_dt = datetime.fromisoformat(schedule_date.replace('T', ' '))
            except ValueError:
                return {
                    "success": False,
                    "message": "排程日期格式錯誤"
                }
        
        # 批次處理：每20筆為一組
        batch_size = 20
        sms_keys = []
        
        for i in range(0, len(valid_phones), batch_size):
            batch_phones = valid_phones[i:i+batch_size]
            formatted_recipients = ','.join(batch_phones)
            
            # 插入資料庫
            sms_key = db_handler.insert_sms_message(
                message_class=message_class,
                message_body=message_body,
                recipient_no=formatted_recipients,
                schedule_date=schedule_dt
            )
            sms_keys.append(sms_key)
        
        logger.info(f"簡訊已排程: sms_keys={sms_keys}")
        
        return {
            "success": True,
            "message": f"簡訊已成功排程（{len(sms_keys)}批次）",
            "sms_keys": sms_keys
        }
        
    except Exception as e:
        logger.error(f"排程簡訊錯誤: {e}")
        return {
            "success": False,
            "message": str(e)
        }

@app.post("/api/send-sms-now")
async def send_sms_now(
    message_body: str = Form(...),
    extra_recipients: str = Form(""),
    selected_customer_ids: str = Form("[]")
):
    """立即發送簡訊"""
    try:
        # 驗證簡訊長度
        char_info = ai_service.validate_sms_length(message_body)
        if not char_info['is_valid']:
            return {
                "success": False,
                "message": f"簡訊長度超過限制（{char_info['max_length']}字）"
            }
        
        # 解析客戶ID和額外收件人
        try:
            customer_ids = json.loads(selected_customer_ids)
            #customer_ids = [int(id) for id in customer_ids]
        except:
            customer_ids = []
        
        # 取得選擇客戶的電話號碼
        customer_phones = db_handler.get_phone_numbers_by_customer_ids(customer_ids)
        
        # 處理額外收件人
        extra_phones = []
        if extra_recipients.strip():
            extra_phones = sms_gateway.format_phone_list(extra_recipients)
        
        # 合併所有電話號碼並去重
        all_phones = list(set(customer_phones + extra_phones))
        
        if not all_phones:
            return {
                "success": False,
                "message": "沒有有效的收件人"
            }
        
        # 驗證電話號碼
        is_valid, valid_phones = sms_gateway.validate_phone_numbers(all_phones)
        
        if not valid_phones:
            return {
                "success": False,
                "message": "沒有有效的電話號碼"
            }
        
        # 批次處理：每20筆為一組
        batch_size = 20
        sms_keys = []
        results = []
        
        for i in range(0, len(valid_phones), batch_size):
            batch_phones = valid_phones[i:i+batch_size]
            
            # 發送簡訊
            success, result = await sms_gateway.send_sms(batch_phones, message_body)
            results.append(result)
            
            if success:
                # 記錄發送結果
                formatted_recipients = ','.join(batch_phones)
                sms_key = db_handler.insert_sms_message(
                    message_class='IMMEDIATE',
                    message_body=message_body,
                    recipient_no=formatted_recipients,
                    schedule_date=None,
                    send_date=datetime.fromisoformat(datetime.now().replace('T', ' '))
                )
                sms_keys.append(sms_key)
                
                db_handler.update_sms_status(
                    sms_key,
                    result['result_code'],
                    result['result_text'],
                    result['message_id']
                )
                
                logger.info(f"簡訊已發送: sms_key={sms_key}")
        
        return {
            "success": True,
            "message": f"簡訊已發送（{len(sms_keys)}批次）",
            "sms_keys": sms_keys,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"立即發送簡訊錯誤: {e}")
        return {
            "success": False,
            "message": str(e)
        }

@app.get("/api/sms-statistics")
async def get_sms_statistics():
    """取得簡訊統計資訊"""
    try:
        stats = db_handler.get_sms_statistics()
        return {
            "success": True,
            "statistics": stats
        }
    except Exception as e:
        logger.error(f"取得統計資訊錯誤: {e}")
        return {
            "success": False,
            "message": str(e),
            "statistics": {}
        }

@app.post("/api/process-scheduled-sms")
async def process_scheduled_sms():
    """處理排程簡訊（定時任務調用）"""
    try:
        pending_messages = db_handler.get_pending_sms_messages()
        processed_count = 0
        
        for message in pending_messages:
            try:
                # 解析收件人
                recipients = message['RecipientNo'].split(',')
                
                # 發送簡訊
                success, result = await sms_gateway.send_sms(
                    recipients,
                    message['MessageBody']
                )
                
                # 更新狀態
                db_handler.update_sms_status(
                    message['smskey'],
                    result['result_code'],
                    result['result_text'],
                    result['message_id']
                )
                
                if success:
                    processed_count += 1
                    
            except Exception as e:
                logger.error(f"處理簡訊錯誤 (sms_key={message['smskey']}): {e}")
                continue
        
        logger.info(f"處理完成: {processed_count} 筆簡訊")
        
        return {
            "success": True,
            "processed_count": processed_count,
            "total_pending": len(pending_messages)
        }
        
    except Exception as e:
        logger.error(f"處理排程簡訊錯誤: {e}")
        return {
            "success": False,
            "message": str(e),
            "processed_count": 0
        }

# 定時任務
async def scheduled_task():
    """定時執行任務"""
    while True:
        try:
            await asyncio.sleep(settings.SCHEDULE_INTERVAL)
            await process_scheduled_sms()
        except Exception as e:
            logger.error(f"定時任務錯誤: {e}")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )
