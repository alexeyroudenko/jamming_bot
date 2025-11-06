
FROM python:3.11-slim

WORKDIR /app

RUN pip install redis
RUN pip install eventlet

RUN pip install python-socketio=="5.11.4"
RUN pip install python-engineio=="4.10.1"
RUN pip install Flask-SocketIO=="5.4.1"
RUN pip install Flask-Cors
RUN pip install Flask
RUN pip install rq==1.16.2
RUN pip install rq-dashboard==0.6.1
RUN pip install gunicorn==23.0.0
RUN pip install click
RUN pip install sentry-sdk[flask]
RUN pip install requests

# Install modern spaCy and models compatible with Python 3.11
RUN python -m pip install --upgrade pip setuptools wheel \
    && pip install "spacy==3.8.2"
# Install spaCy v3 English models
RUN python -m spacy download en_core_web_sm
RUN python -m spacy download en_core_web_md

RUN pip install bs4
RUN pip install maxminddb
