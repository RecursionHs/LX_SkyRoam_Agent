@echo off
chcp 65001 >nul

echo 🚀 启动 LX SkyRoam Agent...

REM 检查Docker是否安装
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker 未安装，请先安装 Docker
    pause
    exit /b 1
)

REM 检查Docker Compose是否安装（使用插件命令 `docker compose`）
docker compose version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker Compose 未安装或不可用，请安装 Docker Desktop 或 Compose 插件
    pause
    exit /b 1
)

REM 创建必要的目录
echo 📁 创建必要的目录...
if not exist "logs" mkdir logs
if not exist "uploads" mkdir uploads

REM 检查容器环境配置文件（优先使用 .env.docker）
if not exist ".env.docker" (
    echo ⚠️  未检测到 .env.docker，默认将直接使用 compose 中的 environment 配置
    echo    如需自定义，请创建 .env.docker 并与 docker-compose.yml 对齐
)

REM 启动服务
echo 🐳 启动 Docker 服务...
docker compose up -d --build

REM 等待服务启动
echo ⏳ 等待服务启动...
timeout /t 10 /nobreak >nul

REM 检查服务状态
echo 🔍 检查服务状态...
docker compose ps

REM 显示访问信息
echo.
echo ✅ LX SkyRoam Agent 启动完成！
echo.
echo 📱 前端应用: http://localhost:3000
echo 🔧 后端API: http://localhost:8001
echo 📚 API文档: http://localhost:8001/docs
echo 🌸 Celery监控: http://localhost:5555
echo.
echo 📝 日志查看:
echo    docker compose logs -f backend
echo    docker compose logs -f frontend
echo.
echo 🛑 停止服务:
echo    docker compose down
echo.

pause
