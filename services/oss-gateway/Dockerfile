FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY oss_gateway ./oss_gateway
RUN mkdir /data && useradd --uid 10001 --no-create-home gateway && chown gateway /data
USER gateway
EXPOSE 8080
CMD ["uvicorn", "oss_gateway.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8080", "--no-access-log"]
