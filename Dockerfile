# Fix weird run-time bug: https://stackoverflow.com/questions/74884770/python-exec-usr-local-bin-python3-exec-format-error-on-docker-while-using-ap
FROM python:3.12.3 as build

WORKDIR /app
COPY requirements.lock ./
RUN PYTHONDONTWRITEBYTECODE=1 pip install --no-cache-dir -r requirements.lock

COPY scraper.py .
WORKDIR /out
ENV PYTHONPATH=/usr/local/lib/python3.12/site-packages
ENTRYPOINT ["python", "/app/scraper.py"]

