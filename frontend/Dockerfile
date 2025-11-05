FROM node:18-alpine

# 设置工作目录
WORKDIR /app

# 复制package.json和package-lock.json
COPY package*.json ./

# 安装依赖（开发镜像保留 devDependencies 方便热更新）
RUN npm ci

# 复制源代码
COPY . .

# 设置环境变量（CRA 默认端口 3000）
ENV PORT=3000
ENV HOST=0.0.0.0

# 暴露端口
EXPOSE 3000

# 启动命令（开发模式）
CMD ["npm", "start"]
