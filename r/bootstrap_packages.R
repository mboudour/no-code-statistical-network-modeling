#!/usr/bin/env Rscript
# Explicit bootstrap only: the Streamlit app never installs statistical software silently.

library_path <- Sys.getenv("R_LIBS_USER", unset = file.path(Sys.getenv("HOME"), ".local", "R", "library"))
dir.create(library_path, recursive = TRUE, showWarnings = FALSE)
.libPaths(c(library_path, .libPaths()))

# Install only runtime dependencies (Depends/Imports/LinkingTo), not Suggests packages.
# This is materially smaller than dependencies = TRUE and is sufficient for Session 1.1.
repositories <- c(CRAN = "https://cloud.r-project.org")
required <- c("network", "ergm", "jsonlite", "Rglpk")
missing <- required[!vapply(required, requireNamespace, quietly = TRUE, FUN.VALUE = logical(1))]
if (length(missing)) {
  workers <- max(1L, min(2L, parallel::detectCores(logical = FALSE)))
  install.packages(
    missing,
    lib = library_path,
    repos = repositories,
    dependencies = NA,
    Ncpus = workers
  )
}
if (!all(vapply(required, requireNamespace, quietly = TRUE, FUN.VALUE = logical(1)))) {
  stop("One or more required R packages could not be installed.")
}
message("Static ERGM R engine is ready in ", library_path)
