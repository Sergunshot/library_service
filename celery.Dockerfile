FROM python:3.12.4-slim
LABEL maintainer="urovsergej10@gmail.com"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY . .

CMD ["celery", "-A", "library_service", "worker", "--loglevel=info"]
