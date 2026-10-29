# ==============================================================================
# Google Cloud Run 배포용 Dockerfile
# Python 3.11 경량 슬림 이미지를 기반으로 컨테이너를 구성합니다.
# ==============================================================================

FROM python:3.11-slim

# 표준 출력/에러 버퍼링 비활성화 (로그가 Cloud Run에 즉시 기록되도록 보장)
ENV PYTHONUNBUFFERED=1

# Cloud Run에서 기본 주입하는 포트 환경변수(PORT) 기본값 설정
ENV PORT=8080

# 컨테이너 내 작업 디렉터리 설정
WORKDIR /app

# 캐시 효율성을 위해 requirements.txt를 먼저 복사 후 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 애플리케이션 소스 코드 전체 복사
COPY . .

# Cloud Run 기본 포트 노출
EXPOSE 8080

# Gunicorn WSGI 서버 실행
# Cloud Run 환경에 최적화: 1개 워커 프로세스, 8개 스레드, 무제한 타임아웃
CMD exec gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 0 main:app

