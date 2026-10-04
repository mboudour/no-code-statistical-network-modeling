#!/usr/bin/env Rscript
# Explicit bootstrap only: the Streamlit app never installs statistical software silently.

library_path <- Sys.getenv("R_LIBS_USER", unset = file.path(Sys.getenv("HOME"), ".local", "R", "library"))
dir.create(library_path, recursive = TRUE, showWarnings = FALSE)
.libPaths(c(library_path, .libPaths()))

repositories <- c(CRAN = "https://cloud.r-project.org")
required <- c("network", "ergm", "jsonlite", "Rglpk")
missing <- required[!vapply(required, requireNamespace, quietly = TRUE, FUN.VALUE = logical(1))]
if (length(missing)) {
  install.packages(missing, lib = library_path, repos = repositories, dependencies = TRUE)
}
if (!all(vapply(required, requireNamespace, quietly = TRUE, FUN.VALUE = logical(1)))) {
  stop("One or more required R packages could not be installed.")
}
message("Static ERGM R engine is ready in ", library_path)
