FROM python:3.10 as builder
WORKDIR /app/

ENV CARGO_REGISTRIES_CRATES_IO_PROTOCOL=sparse

RUN apt-get update && \
    apt-get install -y gcc git libtiff5-dev libjpeg62-turbo-dev libopenjp2-7-dev zlib1g-dev \
    libfreetype6-dev liblcms2-dev libwebp-dev tcl8.6-dev tk8.6-dev python3-tk \
    libharfbuzz-dev libfribidi-dev libxcb1-dev \
    build-essential libssl-dev libffi-dev libudev-dev libssl3 \
    python3-dev cargo pkg-config


RUN --mount=type=tmpfs,target=/root/.cargo pip install poetry
COPY pyproject.toml poetry.lock /app/
RUN poetry export -f requirements.txt --without-hashes > requirements.txt && \
    pip wheel --wheel-dir=/root/wheels -r requirements.txt



FROM python:3.10-slim

WORKDIR /app/

COPY --from=builder /app/requirements.txt /app/requirements.txt
COPY --from=builder /root/wheels /root/wheels

RUN pip install \
      --no-index \
      --find-links=/root/wheels \
      -r requirements.txt && \
    pip install \
      --no-index \
      --find-links=/root/wheels \
      rpi-bme280 -I

COPY . /app/

CMD ["python", "main.py"]