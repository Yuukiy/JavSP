FROM python:3.8.18-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN git clone http://oauth2:b425ce21165015a9dba060a1ca8c274b81df0dbf@113.205.142.106:9117/wayne/JavSP.git .

RUN pip3 install -r requirements.txt

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["streamlit", "run", "webui/scraper_setting.py", "--server.port=8501", "--server.address=0.0.0.0"]