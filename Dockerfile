FROM python:3.11-slim-bookworm

RUN apt update
RUN apt install python3-dev gcc -y

WORKDIR /app

COPY src/requirements.txt ./
RUN python3 -m pip install --upgrade pip
RUN python3 -m pip install -r requirements.txt

COPY src /app

CMD [ "python", "main.py" ]