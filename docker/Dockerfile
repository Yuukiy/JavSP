FROM python:3.10-slim AS base
COPY requirements-linux.txt .
RUN pip install pip -U && \
    pip install --user --no-cache-dir -r requirements-linux.txt

FROM python:3.10-slim
COPY --from=base /root/.local /root/.local
COPY . /app/
COPY ./docker/config.ini /app/config.ini
WORKDIR /app
ENV PATH=/root/.local/bin:$PATH
ENTRYPOINT ["python", "/app/JavSP.py"]
CMD [ "python", "/app/JavSP.py", "-c", "/app/config.ini" ]
