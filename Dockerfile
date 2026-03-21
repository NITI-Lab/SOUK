FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir ".[all]"

COPY cases/ cases/
COPY config.example.yaml config.example.yaml

ENTRYPOINT ["souk"]
CMD ["--help"]
