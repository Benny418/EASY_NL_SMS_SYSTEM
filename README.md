# 簡訊發送系統 (SMS System)

一個基於 FastAPI 的一頁式簡訊發送應用程式，支援 AI 生成簡訊、自然語言查詢客戶資料、預約發送等功能。此系統程式碼由Kimi K2生成。

## 系統特色

- 🤖 **AI 簡訊生成**：使用 Google Gemini API 或 OpenAI GPT 根據提示詞生成促銷簡訊
- 🔍 **自然語言查詢**：透過自然語言查詢客戶資料，自動轉換為 SQL
- 📱 **簡訊發送**：支援立即發送和預約發送
- 📊 **客戶管理**：整合客戶資料查詢與篩選
- 🔐 **個資保護**：自動隱碼處理敏感個資
- ⚡ **即時回饋**：即時字數統計與驗證
- 🔄 **定時任務**：自動處理排程簡訊

## 技術架構

- **後端**：FastAPI (Python)
- **資料庫**：PostgreSQL
- **前端**：HTML + HTMX + Alpine.js + Tailwind CSS
- **AI 服務**：Google Gemini API 或 OpenAI 相容API
- **簡訊服務**：外部 SMS Gateway

## 系統架構圖

```mermaid
graph TB
    subgraph "前端層"
        UI[一頁式介面]
        HTMX[HTMX]
        Alpine[Alpine.js]
    end
    
    subgraph "應用層"
        FastAPI[FastAPI Server]
        SMSAPI[簡訊發送API]
        QueryAPI[查詢API]
        AIAPI[AI生成API]
    end
    
    subgraph "服務層"
        DBService[資料庫服務]
        SMSService[簡訊服務]
        AIService[AI服務]
        Logger[日誌服務]
    end
    
    subgraph "資料層"
        PG[(PostgreSQL)]
        SMSGW[SMS Gateway]
        Gemini[Google Gemini]
    end
    
    UI --> HTMX
    HTMX --> FastAPI
    Alpine --> UI
    
    FastAPI --> SMSAPI
    FastAPI --> QueryAPI
    FastAPI --> AIAPI
    
    SMSAPI --> DBService
    SMSAPI --> SMSService
    QueryAPI --> DBService
    AIAPI --> Gemini
    
    DBService --> PG
    SMSService --> SMSGW
    AIService --> Gemini
    
    Logger -.-> FastAPI
    Logger -.-> DBService
    Logger -.-> SMSService
```

### 資料流程圖

```mermaid
flowchart TD
    A[使用者輸入] --> B{選擇模式}
    B -->|AI生成| C[輸入提示詞]
    B -->|自定義| D[輸入簡訊內容]
    C --> E[Gemini API]
    E --> F[生成簡訊]
    F --> G[字數檢查]
    D --> G
    G --> H[自然語言查詢]
    H --> I[LLM解析]
    I --> J[SQL查詢]
    J --> K[顯示客戶資料]
    K --> L[輸入預約時間]
    L --> M[確認發送]
    M --> N[存入smsMessage]
    N --> O[觸發發送API]
    O --> P[定時檢查]
    P --> Q[SMS Gateway]
    Q --> R[更新狀態]
```

## 時序圖

### 簡訊發送流程

```mermaid
sequenceDiagram
    participant U as 使用者
    participant Web as Web介面
    participant API as FastAPI
    participant DB as PostgreSQL
    participant SMS as SMS Gateway
    
    U->>Web: 輸入簡訊內容與查詢條件
    Web->>API: POST /generate-sms (AI模式)
    API->>Gemini: 請求生成簡訊
    Gemini-->>API: 返回簡訊內容
    API-->>Web: 返回簡訊內容
    
    Web->>API: POST /query-customers
    API->>Gemini: 解析自然語言查詢
    Gemini-->>API: 返回SQL查詢
    API->>DB: 執行SQL查詢
    DB-->>API: 返回客戶資料
    API-->>Web: 顯示客戶列表
    
    U->>Web: 確認發送
    Web->>API: POST /schedule-sms
    API->>DB: 存入smsMessage
    DB-->>API: 確認儲存
    API-->>Web: 返回成功訊息
    
    Note over API: 定時任務觸發
    
    API->>DB: 查詢待發送簡訊
    DB-->>API: 返回簡訊列表
    API->>SMS: 發送簡訊請求
    SMS-->>API: 返回發送結果
    API->>DB: 更新發送狀態
```

### AI查詢解析流程

```mermaid
sequenceDiagram
    participant U as 使用者
    participant Web as Web介面
    participant API as FastAPI
    participant Gemini as Google Gemini
    participant DB as PostgreSQL
    
    U->>Web: 輸入自然語言查詢
    Web->>API: POST /parse-query
    API->>Gemini: 發送查詢請求
    Note over Gemini: 限制只能查詢<br/>cust_info, order_master,<br/>order_detail三個表
    Gemini-->>API: 返回SQL查詢語句
    API->>DB: 執行SQL查詢
    DB-->>API: 返回查詢結果
    API->>API: 個資隱碼處理
    API-->>Web: 返回處理後的資料
```

## 資料庫設計

### 實體關係圖

```mermaid
erDiagram
    cust_info ||--o{ order_master : "has"
    order_master ||--o{ order_detail : "contains"
    
    cust_info {
        string cust_id PK
        string cust_name
        string gender
        string mobile_number
        string home_number
        string address
        int age
        date birthday
        boolean refuse
        timestamp create_date
    }
    
    order_master {
        string order_no PK
        timestamp order_date
        string cust_id FK
        real amount
        smallint pay_method
        string delivery_address
        string receiver
        string receiver_phone
        smallint order_type
        string taker_id
        timestamp create_date
    }
    
    order_detail {
        int rowkey PK
        string order_no FK
        string product_id
        string product_title
        real unit_price
        smallint qty
        string batch_no
    }
    
    sms_message {
        int smskey PK
        timestamp create_date
        string message_class
        string message_body
        string recipient_no
        timestamp schedule_date
        timestamp send_date
        string return_code
        string return_message
        string message_id
    }
```

## 快速開始

### 環境需求

- Python 3.8+
- PostgreSQL 12+
- Google Gemini API Key 或 OpenAI API Key

### 安裝步驟

1. **複製專案**
```bash
git clone <repository-url>
cd sms_system
```

2. **建立虛擬環境**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows
```

3. **安裝依賴**
```bash
pip install -r requirements.txt
```

4. **設定環境變數**
```bash
cp .env.example .env
# 編輯 .env 檔案，填入必要的設定
```

5. **設定資料庫**
```bash
# 建立資料庫
createdb sms_system

# 執行初始化腳本
psql -d sms_system -f init_database.sql

# 載入測試資料
psql -d sms_system -f sample_data.sql
```

6. **啟動系統**
```bash
python main.py
```

系統將在 http://localhost:8000 啟動

## 環境變數設定

複製 `.env.example` 為 `.env` 並設定以下參數：

```bash
# 資料庫設定
DB_HOST=localhost
DB_PORT=5432
DB_NAME=sms_system
DB_USER=postgres
DB_PASSWORD=your_password

# FastAPI設定
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false

# SMS Gateway設定
SMS_GATEWAY_URL=http://123.123.123.123:4321/mpsiweb/smssubmit
SMS_SYS_ID=ENT001
SMS_SRC_ADDRESS=01234500000000001234
SMS_DR_FLAG=true
SMS_FIRST_FAIL_FLAG=false

# Gemini API設定
GEMINI_API_KEY=your-gemini-api-key

# 日誌設定
LOG_LEVEL=INFO
LOG_FILE=logs/sms_system.log
LOG_MAX_SIZE=10485760
LOG_BACKUP_COUNT=5

# 排程設定
SCHEDULE_INTERVAL=60
```

## 使用說明

### 1. AI 生成簡訊

1. 選擇「AI生成簡訊」模式
2. 輸入提示詞（例如：「週年慶促銷活動」）
3. 點擊「生成簡訊」
4. 系統會自動生成符合長度限制的促銷簡訊

支援兩種 AI 提供者：
- **Google Gemini**（預設）
- **OpenAI GPT**（需設定 OPENAI_API_KEY）

### 2. 自定義簡訊

1. 選擇「自定義簡訊」模式
2. 直接輸入簡訊內容
3. 系統會即時顯示字數統計

### 3. 客戶查詢

1. 在「客戶查詢」區塊輸入自然語言查詢
2. 例如：「找出最近一個月有購買的客戶」
3. 系統會自動轉換為 SQL 並顯示結果
4. 可勾選客戶加入收件人清單

### 4. 發送簡訊

1. 選擇「立即發送」或「預約發送」
2. 如選擇預約發送，設定發送時間
3. 確認收件人清單
4. 點擊「發送」按鈕

## API 文件

### 簡訊相關 API

#### 生成簡訊
```http
POST /api/generate-sms
Content-Type: application/x-www-form-urlencoded

prompt=週年慶促銷活動&max_length=70
```

#### 驗證簡訊長度
```http
POST /api/validate-sms
Content-Type: application/x-www-form-urlencoded

content=簡訊內容&max_length=70
```

#### 排程簡訊
```http
POST /api/schedule-sms
Content-Type: application/x-www-form-urlencoded

message_class=SCHEDULED&message_body=簡訊內容&recipient_no=0912345678&schedule_date=2024-01-01T10:00:00
```

### 查詢相關 API

#### 解析自然語言查詢
```http
POST /api/parse-query
Content-Type: application/x-www-form-urlencoded

query=找出最近一個月有購買的客戶
```

#### 執行客戶查詢
```http
POST /api/query-customers
Content-Type: application/x-www-form-urlencoded

sql_query=SELECT * FROM public.cust_info LIMIT 10
```

## 專案結構

```
sms_system/
├── config/
│   ├── settings.py          # 系統設定
│   └── database.py          # 資料庫連線設定
├── modules/
│   ├── db_handler.py        # 資料庫操作模組
│   ├── sms_gateway.py       # SMS Gateway模組
│   └── ai_service.py        # AI服務模組
├── templates/
│   └── index.html          # 主頁面模板
├── static/
│   ├── css/                # 樣式檔案
│   └── js/                 # JavaScript檔案
├── tests/
│   ├── test_db_handler.py  # 資料庫測試
│   ├── test_sms_gateway.py # SMS Gateway測試
│   └── test_ai_service.py  # AI服務測試
├── logs/                   # 日誌檔案
├── main.py                 # FastAPI主程式
├── requirements.txt        # 依賴套件
├── pytest.ini             # 測試設定
├── init_database.sql      # 資料庫初始化
├── sample_data.sql        # 測試資料
├── .env.example           # 環境變數範例
└── README.md             # 專案說明
```

## 測試

執行測試套件：

```bash
# 執行所有測試
pytest

# 執行特定測試
pytest tests/test_db_handler.py
pytest tests/test_sms_gateway.py
pytest tests/test_ai_service.py

# 執行測試並顯示詳細資訊
pytest -v

# 執行測試並產生覆蓋率報告
pytest --cov=modules tests/
```

## 部署

### Docker 部署（建議）

1. **建立 Dockerfile**
```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

2. **建立 docker-compose.yml**
```yaml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DB_HOST=db
      - DB_NAME=sms_system
      - DB_USER=postgres
      - DB_PASSWORD=postgres
    depends_on:
      - db
  
  db:
    image: postgres:13
    environment:
      - POSTGRES_DB=sms_system
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init_database.sql:/docker-entrypoint-initdb.d/init.sql
      - ./sample_data.sql:/docker-entrypoint-initdb.d/sample.sql

volumes:
  postgres_data:
```

3. **啟動服務**
```bash
docker-compose up -d
```

### 生產環境部署

1. **使用 Gunicorn**
```bash
pip install gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

2. **使用 systemd 服務**
```ini
# /etc/systemd/system/sms-system.service
[Unit]
Description=SMS System
After=network.target

[Service]
Type=exec
User=sms
WorkingDirectory=/opt/sms_system
Environment="PATH=/opt/sms_system/venv/bin"
ExecStart=/opt/sms_system/venv/bin/gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
Restart=always

[Install]
WantedBy=multi-user.target
```
## 授權

本專案採用 MIT 授權條款，詳見 [LICENSE](LICENSE) 檔案。
