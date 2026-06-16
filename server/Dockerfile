FROM python:3.11-slim

# 支持通过 build arg 指定运行用户 UID/GID
ARG UID=1000
ARG GID=1000

# 创建与宿主机同 UID/GID 的用户
RUN groupadd -g ${GID} appuser && \
    useradd -m -u ${UID} -g ${GID} appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .

# 设置目录权限
RUN chown -R ${UID}:${GID} /app && \
    mkdir -p /data/knowledge-base /data/config && \
    chown -R ${UID}:${GID} /data

USER appuser

EXPOSE 8396

CMD ["python3", "server.py"]
