FROM python:3.11
WORKDIR /app
ENV DEBIAN_FRONTEND noninteractive

RUN sharing=private,target=/var/cache/apt apt-get update && apt install -y --no-install-recommends --reinstall xz-utils git wget && apt-get clean
RUN wget https://johnvansickle.com/ffmpeg/builds/ffmpeg-git-amd64-static.tar.xz -O ffmpeg.tar.xz && \
    tar -xvf ffmpeg.tar.xz
RUN cp -r ffmpeg*/ff* /usr/bin/ && rm -rf ffmpeg*

# Pip reqs
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && pip uninstall -y pydantic pydantic_core && pip install --no-cache-dir pydantic==1.10.13
