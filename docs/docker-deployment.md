# Docker deployment: Session 1.1 ERGM companion

## Why this deployment exists

The standard `ergm` R package is not shipped as a prebuilt Debian package in Streamlit Community Cloud. Installing it inside a running Streamlit app makes the first participant wait while compiled R code and dependencies are installed.

This repository's `Dockerfile` solves that problem correctly:

1. it uses the `rocker/r2u` base image, which supplies current CRAN packages as Ubuntu binaries;
2. it installs the prebuilt `r-cran-ergm`, `r-cran-network`, `r-cran-jsonlite`, and `r-cran-rglpk` packages while the image is built;
3. it verifies those packages in a Docker build step; and
4. it starts Streamlit only after the standard R/statnet engine is already present.

Therefore, users of the deployed Docker app should see **“Standard R/statnet ERGM engine is available”** immediately. They should not see an R-package installation task.

## Local validation

```bash
docker build --tag network-modeling-session11 .
docker run --rm -p 8501:8501 network-modeling-session11
```

Open <http://localhost:8501>, then select **Session 1.1 — Foundations of Static ERGMs** and **Five worked public networks**. The health endpoint is <http://localhost:8501/_stcore/health>.

## Render deployment

The repository includes `render.yaml`, a Docker blueprint. In Render:

1. Create a new **Blueprint** service from the GitHub repository.
2. Select the `main` branch and accept `render.yaml`.
3. Wait for the image build to complete. It installs prebuilt R/statnet binaries; no participant-facing CRAN compilation occurs.
4. Open the assigned public service URL and verify the R engine banner reads **available**.

The image reads Render's assigned `PORT` automatically and binds Streamlit to `0.0.0.0`. A new commit to `main` triggers a new image build and deployment. The application never installs R packages on behalf of a participant at runtime.
