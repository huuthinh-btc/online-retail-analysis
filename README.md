# 📊 Online Retail Analysis System

Hệ thống phân tích dữ liệu bán lẻ trực tuyến với Streamlit.

## Tính năng

- 📈 Data Overview & Cleaning
- 🔍 Exploratory Data Analysis (EDA)
- 💰 Revenue Analysis
- 👥 RFM Segmentation
- 📊 Cohort Analysis

## Cấu trúc dự án

```
.
├── app.py              # Ứng dụng Streamlit chính
├── DATASET.xlsx        # Dữ liệu Online Retail
├── requirements.txt    # Python dependencies
└── README.md           # File này
```

## Cách chạy local

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy lên Streamlit Cloud

1. Đẩy code lên GitHub repository
2. Truy cập https://share.streamlit.io
3. Đăng nhập bằng GitHub
4. Chọn repository và branch
5. Nhập: `app.py` làm file chính
6. Click "Deploy"

## Yêu cầu

- Python 3.8+
- File DATASET.xlsx phải có trong cùng thư mục với app.py
