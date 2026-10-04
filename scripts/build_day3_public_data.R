#!/usr/bin/env Rscript
# Build app-ready CSV copies of documented public SAOM teaching panels.
# Source URLs and response-boundary decisions are recorded in
# docs/day3_public_data_research.md. No synthetic data are created.

options(stringsAsFactors = FALSE)
arguments <- commandArgs(trailingOnly = FALSE)
script_argument <- arguments[grepl("^--file=", arguments)]
script_path <- if (length(script_argument)) sub("^--file=", "", script_argument[[1]]) else "scripts/build_day3_public_data.R"
root <- normalizePath(file.path(dirname(script_path), ".."), mustWork = FALSE)
if (!dir.exists(file.path(root, "data"))) root <- getwd()
out_dir <- file.path(root, "data", "public")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
tmp <- file.path(tempdir(), "day3_saom_sources")
dir.create(tmp, recursive = TRUE, showWarnings = FALSE)

download_archive <- function(url, destination) {
  if (!file.exists(destination)) {
    utils::download.file(url, destination, mode = "wb", quiet = TRUE)
  }
}

write_network <- function(matrices, ids, prefix) {
  stopifnot(length(matrices) >= 2, length(ids) == nrow(matrices[[1]]))
  nodes <- do.call(rbind, lapply(seq_along(matrices), function(wave) {
    data.frame(wave = as.character(wave), id = ids)
  }))
  edges <- do.call(rbind, lapply(seq_along(matrices), function(wave) {
    mat <- matrices[[wave]]
    positions <- which(mat > 0 & row(mat) != col(mat), arr.ind = TRUE)
    data.frame(
      wave = as.character(wave),
      source = ids[positions[, 1]],
      target = ids[positions[, 2]]
    )
  }))
  utils::write.csv(nodes, file.path(out_dir, paste0(prefix, "_nodes.csv")), row.names = FALSE)
  utils::write.csv(edges, file.path(out_dir, paste0(prefix, "_edges.csv")), row.names = FALSE)
}

# --- RSiena s50 teaching excerpt ------------------------------------------------
s50_zip <- file.path(tmp, "s50_data.zip")
download_archive("https://www.stats.ox.ac.uk/~snijders/siena/s50_data.zip", s50_zip)
s50_dir <- file.path(tmp, "s50")
dir.create(s50_dir, showWarnings = FALSE)
utils::unzip(s50_zip, exdir = s50_dir)
read_matrix <- function(path) as.matrix(utils::read.table(path, header = FALSE))
s50_network <- lapply(1:3, function(w) read_matrix(file.path(s50_dir, paste0("s50-network", w, ".dat"))))
s50_ids <- sprintf("S%03d", seq_len(nrow(s50_network[[1]])))
write_network(s50_network, s50_ids, "saom_s50")
s50_alcohol <- read_matrix(file.path(s50_dir, "s50-alcohol.dat"))
s50_smoking <- read_matrix(file.path(s50_dir, "s50-smoke.dat"))
s50_cannabis <- read_matrix(file.path(s50_dir, "s50-drugs.dat"))
s50_behavior <- do.call(rbind, lapply(1:3, function(wave) {
  data.frame(
    wave = as.character(wave), id = s50_ids,
    alcohol = s50_alcohol[, wave], smoking = s50_smoking[, wave], cannabis = s50_cannabis[, wave]
  )
}))
utils::write.csv(s50_behavior, file.path(out_dir, "saom_s50_behaviors.csv"), row.names = FALSE)

# --- Knecht classroom panel ------------------------------------------------------
knecht_zip <- file.path(tmp, "klas12b.zip")
download_archive("https://www.stats.ox.ac.uk/~snijders/siena/klas12b.zip", knecht_zip)
knecht_dir <- file.path(tmp, "knecht")
dir.create(knecht_dir, showWarnings = FALSE)
utils::unzip(knecht_zip, exdir = knecht_dir)
# Restrict to actors present in every observed wave, matching the documented binary
# app panel and avoiding a silent treatment of absence as a non-tie.
existing_nodes <- utils::read.csv(file.path(out_dir, "knecht_friendship_temporal_nodes.csv"))
stable_ids <- Reduce(intersect, split(as.character(existing_nodes$id), existing_nodes$wave))
stable_ids <- stable_ids[order(stable_ids)]
actor_index <- as.integer(sub("K", "", stable_ids))
knecht_del <- read_matrix(file.path(knecht_dir, "klas12b-delinquency.dat"))
knecht_alc <- read_matrix(file.path(knecht_dir, "klas12b-alcohol.dat"))
knecht_behavior <- do.call(rbind, lapply(1:4, function(wave) {
  alcohol_column <- wave - 1L
  data.frame(
    wave = as.character(wave), id = stable_ids,
    delinquency = knecht_del[actor_index, wave],
    alcohol = if (alcohol_column >= 1L) knecht_alc[actor_index, alcohol_column] else NA_real_
  )
}))
utils::write.csv(knecht_behavior, file.path(out_dir, "saom_knecht_behaviors.csv"), row.names = FALSE, na = "")

# --- Full Glasgow release --------------------------------------------------------
glasgow_zip <- file.path(tmp, "Glasgow_data.zip")
download_archive("https://www.stats.ox.ac.uk/~snijders/siena/Glasgow_data.zip", glasgow_zip)
glasgow_dir <- file.path(tmp, "glasgow")
dir.create(glasgow_dir, showWarnings = FALSE)
utils::unzip(glasgow_zip, exdir = glasgow_dir)
load(file.path(glasgow_dir, "Glasgow-friendship.RData"))
load(file.path(glasgow_dir, "Glasgow-substances.RData"))
load(file.path(glasgow_dir, "Glasgow-selections.RData"))
keep <- which(selection129)
glasgow_ids <- sprintf("G%03d", keep)
glasgow_raw <- list(friendship.1, friendship.2, friendship.3)
glasgow_network <- lapply(glasgow_raw, function(x) {
  # The documented coding is 0=no friend, 1=best friend, 2=just friend,
  # and 10=structural absence. The app response is binary friendship presence:
  # both 1 and 2 are retained; 0 is a non-tie; the stable 129-actor panel
  # removes actors with structural absence across the three waves.
  y <- x[keep, keep, drop = FALSE]
  matrix(as.integer(y %in% c(1, 2)), nrow = nrow(y), ncol = ncol(y))
})
write_network(glasgow_network, glasgow_ids, "saom_glasgow")
glasgow_behavior <- do.call(rbind, lapply(1:3, function(wave) {
  data.frame(
    wave = as.character(wave), id = glasgow_ids,
    alcohol = alcohol[keep, wave], cannabis = cannabis[keep, wave], tobacco = tobacco[keep, wave]
  )
}))
utils::write.csv(glasgow_behavior, file.path(out_dir, "saom_glasgow_behaviors.csv"), row.names = FALSE)

cat("Built Day 3 public panels in", out_dir, "\n")
