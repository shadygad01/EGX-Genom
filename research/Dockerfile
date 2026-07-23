# AGX research runtime. Deployment target (cloud provider, orchestration,
# secrets) is a business decision -- this image is what that decision runs.
FROM python:3.11-slim

RUN pip install --no-cache-dir uv

WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY data/mock ./data/mock
RUN uv sync --frozen --no-dev

ENTRYPOINT ["uv", "run", "python", "-m", "agx_research.cli"]
CMD ["--help"]
