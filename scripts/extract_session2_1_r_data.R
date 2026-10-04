#!/usr/bin/env Rscript
# Extract public temporal network panels bundled in Statnet-compatible packages.

suppressPackageStartupMessages({
  library(network)
  library(ergm)
  library(sna)
})

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 2L) {
  stop("Usage: Rscript extract_session2_1_r_data.R OUTPUT_DIRECTORY WINDSURFER_PANELS.rda")
}
output_dir <- args[[1L]]
windsurfer_path <- args[[2L]]
dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

append_network <- function(nw, wave, node_rows, edge_rows) {
  identifiers <- as.character(network.vertex.names(nw))
  if (!length(identifiers)) identifiers <- as.character(seq_len(network.size(nw)))
  node_rows[[length(node_rows) + 1L]] <- data.frame(
    wave = as.character(wave), id = identifiers, stringsAsFactors = FALSE
  )
  edge_matrix <- network::as.edgelist(nw)
  if (is.null(dim(edge_matrix)) || !nrow(edge_matrix)) {
    edge_rows[[length(edge_rows) + 1L]] <- data.frame(
      wave = character(0), source = character(0), target = character(0), stringsAsFactors = FALSE
    )
  } else {
    edge_rows[[length(edge_rows) + 1L]] <- data.frame(
      wave = as.character(wave),
      source = identifiers[edge_matrix[, 1L]],
      target = identifiers[edge_matrix[, 2L]],
      stringsAsFactors = FALSE
    )
  }
  list(nodes = node_rows, edges = edge_rows)
}

write_panels <- function(panels, prefix, waves) {
  node_rows <- list()
  edge_rows <- list()
  for (index in seq_along(panels)) {
    collected <- append_network(panels[[index]], waves[[index]], node_rows, edge_rows)
    node_rows <- collected$nodes
    edge_rows <- collected$edges
  }
  nodes <- do.call(rbind, node_rows)
  edges <- do.call(rbind, edge_rows)
  write.csv(nodes, file.path(output_dir, paste0(prefix, "_nodes.csv")), row.names = FALSE)
  write.csv(edges, file.path(output_dir, paste0(prefix, "_edges.csv")), row.names = FALSE)
  cat(prefix, "waves=", length(panels), "nodes_rows=", nrow(nodes), "edges=", nrow(edges), "\n", sep = "")
}

# Sampson: three longitudinal positive-affect/liking panels, never pooled.
data("samplk", package = "ergm")
write_panels(list(samplk1, samplk2, samplk3), "sampson_liking_temporal", c("1", "2", "3"))

# Coleman: two genuinely repeated directed binary sociometric nomination matrices.
data("coleman", package = "sna")
if (!identical(dim(coleman), c(2L, 73L, 73L))) {
  stop("Unexpected sna::coleman dimensions; expected 2 x 73 x 73.")
}
coleman_panels <- lapply(seq_len(dim(coleman)[1L]), function(index) {
  adjacency <- coleman[index, , ]
  nw <- network.initialize(73L, directed = TRUE, loops = FALSE, multiple = FALSE)
  network.vertex.names(nw) <- sprintf("C%02d", seq_len(73L))
  pairs <- which(adjacency != 0, arr.ind = TRUE)
  if (nrow(pairs)) network::add.edges(nw, tail = pairs[, 1L], head = pairs[, 2L])
  nw
})
write_panels(coleman_panels, "coleman_friendship_temporal", c("Fall1957", "Spring1958"))

# Windsurfers: public daily panel list.  The missing panel is represented as NA and is omitted.
load(windsurfer_path)
if (!exists("beach", inherits = FALSE)) {
  stop("The public windsurferPanels archive did not contain the expected `beach` object.")
}
if (!is.list(beach) || !length(beach)) stop("The public `beach` object is not a non-empty panel list.")
wind_panels <- list()
wind_waves <- character(0)
for (index in seq_along(beach)) {
  panel <- beach[[index]]
  if (length(panel) == 1L && is.na(panel)) next
  if (!inherits(panel, "network")) stop("A non-missing beach panel is not a network object.")
  wind_panels[[length(wind_panels) + 1L]] <- panel
  label <- names(beach)[[index]]
  if (is.null(label) || !nzchar(label)) label <- as.character(index)
  wind_waves <- c(wind_waves, as.character(label))
}
if (length(wind_panels) != 30L) {
  stop(sprintf("Unexpected number of observed windsurfer panels: %d (expected 30).", length(wind_panels)))
}
write_panels(wind_panels, "windsurfers_interaction_temporal", wind_waves)
