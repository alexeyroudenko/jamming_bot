FROM python:3.11-slim-buster

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Install pip requirements
COPY requirements.txt .
RUN python -m pip install -r requirements.txt

# setup WORKDIR
ADD . /jamming_bot
WORKDIR /jamming_bot
# CMD ["python", "jamming_bot.py"]