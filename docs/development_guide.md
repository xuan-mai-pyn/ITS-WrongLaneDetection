# Development Guide

Hướng dẫn cài đặt môi trường, khởi chạy hệ thống và quy chuẩn mở rộng dự án **ITS-WrongLaneDetection**.

---

## 1. Local Setup (Cài đặt môi trường & Chạy Backend)

1. **Yêu cầu hệ thống:**
   - Cài đặt **Python 3.10+** trên máy.

2. **Tạo môi trường ảo (Virtual Environment) và cài đặt thư viện:**
   ```bash
   python -m venv venv
   # Kích hoạt trên Windows:
   venv\Scripts\activate
   # Kích hoạt trên macOS/Linux:
   source venv/bin/activate

   pip install -r requirements.txt
