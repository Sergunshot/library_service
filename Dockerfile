FROM python:3.12-alpine
LABEL maintainer="urovsergej10@gmail.com"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . .

RUN adduser \
    --disabled-password \
