FROM python:3
WORKDIR /app
ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update && apt install -y ffmpeg

# Pip reqs
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
