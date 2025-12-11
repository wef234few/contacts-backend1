@echo off
echo 🔧 通讯录系统测试启动器
echo.
echo 请确保已经在一个PowerShell窗口中运行: python app.py
echo 这个批处理文件将运行API测试
echo.
pause

echo 正在检查后端是否运行...
timeout /t 3 /nobreak >nul

rem 检查端口5000是否在监听
netstat -ano | findstr :5000 >nul
if %errorlevel% equ 0 (
    echo ✅ 后端服务正在运行
) else (
    echo ❌ 后端服务未运行，请先运行: python app.py
    pause
    exit /b 1
)

echo.
echo 🚀 开始运行API测试...
python test_api.py

echo.
echo 📊 测试完成！
echo.
echo 下一步操作：
echo 1. 用浏览器打开 ..\contacts_frontend\index.html 测试前端
echo 2. 提交代码到GitHub: git add . && git commit -m "完成作业" && git push
echo 3. 撰写博客
echo.
pause