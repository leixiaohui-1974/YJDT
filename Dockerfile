# YJDT Docker镜像
# 雅江水电梯级分层分布式智能控制系统

FROM python:3.10-slim

LABEL maintainer="Hydropower Research Team"
LABEL version="2.2.0"
LABEL description="雅江水电梯级分层分布式智能控制系统 (YJDT)"

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV YJDT_HOME=/app
ENV YJDT_DATA=/data
ENV YJDT_LOGS=/logs

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# 创建工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .
COPY pyproject.toml .

# 安装Python依赖
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 复制源代码
COPY src/ ./src/
COPY scripts/ ./scripts/

# 安装YJDT
RUN pip install -e .

# 创建数据和日志目录
RUN mkdir -p /data /logs /reports

# 暴露端口
EXPOSE 8000 8080

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/status || exit 1

# 默认命令
CMD ["python", "-m", "yjdt.cli.main", "serve", "--host", "0.0.0.0", "--port", "8000"]
