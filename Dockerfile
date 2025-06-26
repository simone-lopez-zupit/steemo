FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    wget \
    curl \
    xorg libxrender1 libxext6 fontconfig libssl-dev \
    python3-pip \
    git

WORKDIR /app
RUN mkdir -p data

RUN pip install gdown

RUN gdown --id 1tQhXguzVyvwrlQz6ysLBkApFc7j7KiG_ -O data/english_stories_with_emb.json \
 && test -s data/english_stories_with_emb.json

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY startup.sh ./
RUN chmod +x startup.sh

EXPOSE 80

CMD ["./startup.sh"]