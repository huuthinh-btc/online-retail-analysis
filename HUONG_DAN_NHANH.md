# 🚀 HƯỚNG DẪN NHANH - 5 BƯỚC DEPLOY

## BƯỚC 1️⃣: Tải files về máy
Download 5 files này về 1 thư mục:
- ✅ app.py
- ✅ DATASET.xlsx  
- ✅ requirements.txt
- ✅ README.md
- ✅ .gitignore

## BƯỚC 2️⃣: Tạo GitHub Repository
1. Vào https://github.com → Đăng nhập
2. Click nút **"+"** → **"New repository"**
3. Đặt tên: `online-retail-analysis`
4. Chọn **Public**
5. Click **"Create repository"**

## BƯỚC 3️⃣: Upload files lên GitHub
1. Trong repository vừa tạo
2. Click **"Add file"** → **"Upload files"**
3. Kéo thả tất cả 5 files vào
4. Ghi commit message: `Initial commit`
5. Click **"Commit changes"**
6. ⏳ Đợi upload xong (~2 phút)

## BƯỚC 4️⃣: Deploy lên Streamlit Cloud
1. Vào https://share.streamlit.io
2. Click **"Sign in with GitHub"**
3. Click **"New app"**
4. Chọn:
   - Repository: `online-retail-analysis`
   - Branch: `main`
   - Main file: `app.py`
5. Click **"Deploy!"**
6. ⏳ Đợi 3-5 phút

## BƯỚC 5️⃣: Lấy link và chia sẻ
✅ Xong! Link sẽ có dạng:
```
https://[tên-của-bạn]-online-retail-analysis-[random].streamlit.app
```

📤 **Copy link này và chia sẻ cho mọi người!**

---

## ❓ GẶP LỖI?

### Lỗi "ModuleNotFoundError"
→ Kiểm tra file `requirements.txt` có đầy đủ thư viện không

### Lỗi "File not found" 
→ Kiểm tra file `DATASET.xlsx` có trong repository không

### App chạy chậm
→ Đợi lần đầu load (cold start ~1-2 phút)

---

## 🔄 CẬP NHẬT CODE SAU NÀY

1. Vào GitHub repository
2. Click vào file cần sửa → Click ✏️
3. Sửa code → Commit
4. Streamlit tự động update app (~2 phút)

---

**🎉 CHÚC MỪNG! Ứng dụng của bạn đã online!**
