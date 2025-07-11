FROM python:3.13

RUN apt-get update && apt-get install -y locales && rm -rf /var/lib/apt/lists/*
RUN sed -i '/de_DE.UTF-8/s/^# //g' /etc/locale.gen && locale-gen

ENV LANG=de_DE.UTF-8 \
    LANGUAGE=de_DE:de \
    LC_ALL=de_DE.UTF-8

WORKDIR /app
COPY requirements.txt .

RUN pip install --upgrade pip &&  pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir gunicorn 
#RUN pip install --pre torch==2.8.0.dev20250325+cu128 torchvision==0.22.0.dev20250325+cu128 torchaudio==2.6.0.dev20250325+cu128 --index-url https://download.pytorch.org/whl/nightly/cu128
RUN pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu128

RUN python -c "import nltk; nltk.download('stopwords'); nltk.download('punkt'); nltk.download('punkt_tab')"

COPY . .

COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

EXPOSE 9000

CMD ["/app/start.sh"]