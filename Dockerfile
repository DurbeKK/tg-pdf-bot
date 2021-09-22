FROM python:3.9.6

RUN apt-get update
RUN apt-get install -y ghostscript
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get install -y libreoffice

# Set up a virtual environment
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

WORKDIR /app
COPY . /app
CMD ["python", "app.py"]
