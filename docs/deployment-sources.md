# Deployment source references

The Docker deployment decisions are based on the following sources, accessed on 4 October 2026:

- [Render Blueprint YAML reference](https://render.com/docs/blueprint-spec): confirms `runtime: docker`, `healthCheckPath`, the `PORT` convention for web services, and `plan: free` for a zero-cost public web service.
- [Render Docker documentation](https://render.com/docs/docker): documents Dockerfile-based image builds on Render.
- [Streamlit Community Cloud dependency documentation](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies): describes its Python and external-package dependency model.
- [Rocker r2u Docker image](https://hub.docker.com/r/rocker/r2u): provides current CRAN packages as Ubuntu binaries. The image build was verified locally with prebuilt `ergm`, `network`, `jsonlite`, and `Rglpk` packages available to R.

The application image is deliberately based on r2u to avoid compiling the `ergm` R package after a participant opens the app.
