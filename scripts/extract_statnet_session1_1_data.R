#!/usr/bin/env Rscript
# Extract versioned public data bundled with the installed ergm package into app-ready CSV files.

suppressPackageStartupMessages({
  library(network)
  library(ergm)
})

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 1L) stop("Usage: Rscript extract_statnet_session1_1_data.R OUTPUT_DIRECTORY")
output_dir <- args[[1L]]
dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

extract_network <- function(nw, prefix, attributes = character(0)) {
  identifiers <- as.character(network.vertex.names(nw))
  nodes <- data.frame(id = identifiers, stringsAsFactors = FALSE, check.names = FALSE)
  available <- network::list.vertex.attributes(nw)
  for (attribute in attributes) {
    if (!attribute %in% available) next
    values <- network::get.vertex.attribute(nw, attribute)
    if (length(values) == length(identifiers)) nodes[[attribute]] <- values
  }
  edge_matrix <- network::as.edgelist(nw)
  edges <- data.frame(
    source = identifiers[edge_matrix[, 1L]],
    target = identifiers[edge_matrix[, 2L]],
    stringsAsFactors = FALSE
  )
  write.csv(nodes, file.path(output_dir, paste0(prefix, "_nodes.csv")), row.names = FALSE, na = "")
  write.csv(edges, file.path(output_dir, paste0(prefix, "_edges.csv")), row.names = FALSE)
  cat(prefix, "vertices=", network.size(nw), "edges=", network.edgecount(nw), "directed=", network::is.directed(nw), "\n", sep = "")
}

data("florentine", package = "ergm")
extract_network(flobusiness, "florentine_business", c("wealth", "priorates", "totalties"))

data("samplk", package = "ergm")
extract_network(samplk3, "sampson_liking_wave3", c("group", "cloisterville"))

data("kapferer", package = "ergm")
extract_network(kapferer, "kapferer_sociational", character(0))
