#!/bin/bash
set -e

echo "========================================="
echo "  AI Shopping Guide - 一键部署"
echo "========================================="

cd /opt/ai-shopping-guide

echo "[1/6] 拉取最新代码..."
git fetch --all
git reset --hard origin/main
echo "代码拉取完成"

echo "[2/6] 配置环境变量..."
cat > .env << 'ENVEOF'
ZHIPU_API_KEY=739492d402424cb5a641bd0e67c2d349.bplKji28YmXqV7aZ
ZHIPU_LLM_MODEL=GLM-5.1
ZHIPU_LLM_MODEL_FAST=GLM-4.5-Air
ZHIPU_EMBEDDING_MODEL=embedding-3
SERVER_PORT=8000
CLIENT_PORT=3000
CHROMA_PATH=./data/chroma
PRODUCT_DATA_PATH=./data
IMAGE_DATA_PATH=./data
JWT_SECRET=change-me-in-production
JWT_EXPIRE_DAYS=7
CORS_ORIGINS=http://123.207.251.110:3000,http://localhost:3000
ENVEOF

echo "[3/6] 确保 next.config.mjs 有 standalone 输出..."
if ! grep -q "output:" client/next.config.mjs; then
  sed -i "s/const nextConfig = {/const nextConfig = {\n  output: 'standalone',/" client/next.config.mjs
fi

echo "[4/6] 停止旧容器..."
docker compose down 2>/dev/null || true

echo "[5/6] 构建并启动..."
docker compose build
docker compose up -d

echo "[6/6] 验证服务..."
sleep 10
echo ""
echo "容器状态:"
docker compose ps
echo ""
echo "后端健康检查:"
curl -s http://localhost:8000/api/health || echo "后端未响应"
echo ""
echo "前端检查:"
curl -s -o /dev/null -w "HTTP %{http_code}" http://localhost:3000 || echo "前端未响应"
echo ""
echo "========================================="
echo "  部署完成！"
echo "  前端: http://123.207.251.110:3000"
echo "  后端: http://123.207.251.110:8000"
echo "========================================="
