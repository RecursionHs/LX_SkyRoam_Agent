#!/bin/bash

# LX SkyRoam Agent 启动脚本

echo "🚀 启动 LX SkyRoam Agent..."

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装，请先安装 Docker"
    exit 1
fi

# 检查Docker Compose是否安装（使用插件命令 `docker compose`）
if ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose 未安装或不可用，请安装 Docker Desktop 或 Compose 插件"
    exit 1
fi

# 创建必要的目录
echo "📁 创建必要的目录..."
mkdir -p logs uploads

# 复制环境配置文件
if [ ! -f .env ]; then
    echo "📋 复制环境配置文件..."
    cp env.example .env
    echo "⚠️  请编辑 .env 文件，配置您的API密钥和其他设置"
fi

# 启动服务
echo "🐳 启动 Docker 服务..."
docker compose up -d --build

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 10

# 检查服务状态
echo "🔍 检查服务状态..."
docker compose ps

# 显示访问信息
echo ""
echo "✅ LX SkyRoam Agent 启动完成！"
echo ""
echo "📱 前端应用: http://localhost:3000"
echo "🔧 后端API: ${BACKEND_URL:-http://localhost:8001}"
echo "📚 API文档: http://localhost:8001/docs"
echo "🌸 Celery监控: http://localhost:5555"
echo ""
echo "📝 日志查看:"
echo "   docker compose logs -f backend"
echo "   docker compose logs -f frontend"
echo ""
echo "🛑 停止服务:"
echo "   docker compose down"
echo ""
