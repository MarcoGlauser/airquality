FROM python:3.8 as builder
WORKDIR /app/

RUN pip install poetry
COPY pyproject.toml poetry.lock /app/
RUN poetry export -f requirements.txt --without-hashes > requirements.txt && \
    pip wheel --wheel-dir=/root/wheels -r requirements.txt



FROM python:3.8-slim

WORKDIR /app/

COPY --from=builder /app/requirements.txt /app/requirements.txt
COPY --from=builder /root/wheels /root/wheels

RUN pip install \
      --no-index \
      --find-links=/root/wheels \
      -r requirements.txt

COPY . /app/

CMD ["python", "main.py"]