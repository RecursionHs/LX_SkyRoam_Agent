@echo off
setlocal enableextensions

REM 检查 Docker 是否安装
where docker >nul 2>&1
if %errorlevel% neq 0 (
  echo 未检测到 Docker，請先安裝 Docker Desktop。
  exit /b 1
)

REM 检查 docker compose 是否可用（现代语法）
docker compose version >nul 2>&1
if %errorlevel% neq 0 (
  echo 未检测到 docker compose，請更新到最新版 Docker Desktop。
  exit /b 1
)

REM 创建必要目录
if not exist logs mkdir logs
if not exist backend\logs mkdir backend\logs
if not exist backend\uploads mkdir backend\uploads

REM 环境文件提示（优先使用 .env.docker）
if not exist .env.docker (
  echo 提示：未找到 .env.docker，將使用默認環境變量。
)

REM 启动服务（含构建）
echo 啟動容器服務（含構建）...
docker compose up -d --build

REM 短暫等待
ping -n 5 127.0.0.1 >nul

echo 容器狀態：
docker compose ps

echo.
echo 服務已啟動：
echo - 前端（Web）：http://localhost:13000
echo - 高德 MCP HTTP：http://localhost:13002
echo - 小紅書 API：http://localhost:18002

echo.
echo 說明：
echo - 後端主 API、Postgres、Redis、Celery/Flower 僅在容器網絡內可訪問。
echo - 容器內互通使用服務名：backend:8001，amap-mcp-api:3002，xhs-api:8002。

echo.
echo 常用操作：
echo - 查看前端日志：docker compose logs -f frontend
echo - 查看後端日志：docker compose logs -f backend
echo - 查看 Amap MCP 日志：docker compose logs -f amap-mcp-api
echo - 查看 XHS API 日志：docker compose logs -f xhs-api
echo - 停止所有服務：docker compose down

echo.
endlocal
