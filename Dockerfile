# syntax=docker/dockerfile:1
# r2u provides current CRAN packages as tested Ubuntu binaries.
# The image contains the complete R/statnet engine before Streamlit starts.
FROM rocker/r2u:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH=/opt/venv/bin:$PATH

WORKDIR /app

# Install Python plus prebuilt R binaries; no CRAN compilation occurs at app runtime.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        python3 \
        python3-pip \
        python3-venv \
        r-cran-ergm \
        r-cran-jsonlite \
        r-cran-network \
        r-cran-rglpk \
        r-cran-rsiena \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN python3 -m venv /opt/venv \
    && python -m pip install --upgrade pip \
    && python -m pip install -r /app/requirements.txt

COPY app /app/app
COPY data /app/data
COPY r /app/r

# Fail the image build if the required computation engine is absent.
RUN Rscript -e "stopifnot(requireNamespace('network', quietly=TRUE), requireNamespace('ergm', quietly=TRUE), requireNamespace('jsonlite', quietly=TRUE), requireNamespace('Rglpk', quietly=TRUE), requireNamespace('RSiena', quietly=TRUE)); cat('R/statnet and RSiena engines ready\n')"

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD curl --fail --silent http://127.0.0.1:${PORT:-8501}/_stcore/health || exit 1

CMD ["sh", "-c", "streamlit run app/app.py --server.address=0.0.0.0 --server.port=${PORT:-8501} --server.headless=true"]
