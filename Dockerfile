# syntax=docker/dockerfile:1

FROM python:3.12-slim

WORKDIR /app

# Install Poetry via pipx for reproducible builds
ENV PATH=/root/.local/bin:$PATH
RUN pip install --no-cache-dir pipx && \
    pipx install poetry && \
    apt-get update && apt-get install -y --no-install-recommends git cmake && \
    rm -rf /var/lib/apt/lists/*

# Copy project source code
COPY . .

# Initialize a git repository
RUN git init
RUN git config --global credential.helper store

# Install project dependencies inside an in-project virtualenv
RUN git clone --recursive https://github.com/shifei/slime-face.git && \
    pip install ./slime-face && \
    poetry self add poetry-dynamic-versioning && \
    poetry config virtualenvs.in-project true && \
    poetry install --no-interaction --no-ansi

# Clean up unnecessary data to keep image slim
RUN rm -rf .git

# Expose a volume for input videos and output metadata (optional)
VOLUME ["/video", "/output"]

# Default command – can be overridden at runtime
ENTRYPOINT ["/app/.venv/bin/javsp"]
CMD ["-i", "/video"]