#!/usr/bin/env Rscript
# Fit one documented binary static ERGM from a JSON network payload.
# The Streamlit interface constructs the payload only after validating support.

suppressPackageStartupMessages({
  library(jsonlite)
  library(network)
  library(ergm)
})

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 2L) {
  stop("Usage: Rscript fit_static_ergm.R INPUT.json OUTPUT.json")
}
input_path <- args[[1L]]
output_path <- args[[2L]]

write_result <- function(value) {
  jsonlite::write_json(value, output_path, auto_unbox = TRUE, pretty = TRUE, na = "null")
}

safe_message <- function(error) {
  conditionMessage(error)
}

as_character <- function(x) {
  as.character(unlist(x, use.names = FALSE))
}

build_network <- function(payload) {
  nodes <- as.data.frame(payload$nodes, stringsAsFactors = FALSE, check.names = FALSE)
  edges <- as.data.frame(payload$edges, stringsAsFactors = FALSE, check.names = FALSE)
  network_spec <- payload$network

  if (!"id" %in% names(nodes) || anyDuplicated(nodes$id)) {
    stop("Nodes must contain a unique id column.")
  }
  if (!all(c("source", "target") %in% names(edges))) {
    stop("Edges must contain source and target columns.")
  }
  ids <- as.character(nodes$id)
  edge_tail <- match(as.character(edges$source), ids)
  edge_head <- match(as.character(edges$target), ids)
  if (anyNA(edge_tail) || anyNA(edge_head)) {
    stop("Every edge endpoint must appear in the node table.")
  }
  if (any(edge_tail == edge_head)) {
    stop("Self-loops are not supported by this Session 1.1 binary static ERGM workflow.")
  }

  bipartite_count <- FALSE
  if (isTRUE(network_spec$bipartite)) {
    if (!"mode" %in% names(nodes)) {
      stop("A bipartite upload needs a mode column in the node table.")
    }
    mode_order <- unique(as.character(nodes$mode))
    if (length(mode_order) != 2L) {
      stop("A bipartite upload needs exactly two node modes.")
    }
    nodes <- nodes[order(match(as.character(nodes$mode), mode_order)), , drop = FALSE]
    ids <- as.character(nodes$id)
    edge_tail <- match(as.character(edges$source), ids)
    edge_head <- match(as.character(edges$target), ids)
    bipartite_count <- sum(as.character(nodes$mode) == mode_order[[1L]])
    if (any((edge_tail <= bipartite_count) == (edge_head <= bipartite_count))) {
      stop("Bipartite edges must run across the two declared modes.")
    }
  }

  nw <- network.initialize(
    n = nrow(nodes),
    directed = isTRUE(network_spec$directed),
    hyper = FALSE,
    loops = FALSE,
    multiple = FALSE,
    bipartite = bipartite_count
  )
  network.vertex.names(nw) <- ids
  network::add.edges(nw, tail = edge_tail, head = edge_head)

  for (column in setdiff(names(nodes), c("id", "mode"))) {
    network::set.vertex.attribute(nw, column, nodes[[column]])
  }
  if (isTRUE(network_spec$bipartite)) {
    network::set.vertex.attribute(nw, "mode", as.character(nodes$mode))
  }
  nw
}

append_formula_terms <- function(payload, nw) {
  requested <- unique(as_character(payload$formula$terms))
  directed <- network::is.directed(nw)
  bipartite <- network::is.bipartite(nw)
  terms <- character(0)

  if ("edges" %in% requested) terms <- c(terms, "edges")
  if ("mutual" %in% requested) {
    if (!directed) stop("The mutual term is defined only for directed networks.")
    terms <- c(terms, "mutual")
  }
  if ("triangle" %in% requested) {
    if (directed || bipartite) stop("The triangle term in this introductory workflow requires an undirected one-mode network.")
    terms <- c(terms, "triangle")
  }
  if ("b1degree" %in% requested) {
    if (!bipartite) stop("b1degree is defined only for bipartite networks.")
    terms <- c(terms, "b1degree(1)")
  }
  if ("b2degree" %in% requested) {
    if (!bipartite) stop("b2degree is defined only for bipartite networks.")
    terms <- c(terms, "b2degree(1)")
  }

  match_attribute <- payload$formula$nodematch_attribute
  if (!is.null(match_attribute) && nzchar(match_attribute)) {
    if (!match_attribute %in% network::list.vertex.attributes(nw)) {
      stop("Selected nodematch attribute is not in the node table.")
    }
    terms <- c(terms, sprintf("nodematch(\"%s\")", match_attribute))
  }
  covariate_attribute <- payload$formula$nodecov_attribute
  if (!is.null(covariate_attribute) && nzchar(covariate_attribute)) {
    if (!covariate_attribute %in% network::list.vertex.attributes(nw)) {
      stop("Selected nodecov attribute is not in the node table.")
    }
    values <- network::get.vertex.attribute(nw, covariate_attribute)
    if (!is.numeric(values)) {
      stop("The selected nodecov attribute must be numeric.")
    }
    terms <- c(terms, sprintf("nodecov(\"%s\")", covariate_attribute))
  }
  if (!length(terms)) {
    stop("Select at least one supported ERGM term.")
  }
  terms
}

fit_model <- function(payload) {
  warnings <- character(0)
  nw <- build_network(payload)
  terms <- append_formula_terms(payload, nw)
  formula_text <- paste("nw ~", paste(terms, collapse = " + "))
  control_spec <- payload$controls
  burnin <- as.integer(control_spec$mcmc_burnin %||% 5000L)
  interval <- as.integer(control_spec$mcmc_interval %||% 1000L)
  maxit <- as.integer(control_spec$mcmle_maxit %||% 8L)
  control <- ergm::control.ergm(MCMC.burnin = burnin, MCMC.interval = interval, MCMLE.maxit = maxit, seed = as.integer(control_spec$seed %||% 20261028L))

  fitted <- withCallingHandlers(
    ergm::ergm(stats::as.formula(formula_text), control = control),
    warning = function(warning) {
      warnings <<- c(warnings, paste(conditionMessage(warning), collapse = ""))
      invokeRestart("muffleWarning")
    }
  )
  summary_table <- as.data.frame(summary(fitted)$coefficients)
  summary_table$term <- rownames(summary_table)
  rownames(summary_table) <- NULL
  names(summary_table) <- sub("Pr\\(>\\|z\\|\\)", "p_value", names(summary_table))
  names(summary_table) <- sub("Std. Error", "std_error", names(summary_table), fixed = TRUE)
  names(summary_table) <- sub("Estimate", "estimate", names(summary_table), fixed = TRUE)
  summary_table <- summary_table[, c("term", setdiff(names(summary_table), "term")), drop = FALSE]

  bipartite_size <- network::get.network.attribute(nw, "bipartite")
  possible_dyads <- if (network::is.bipartite(nw)) {
    bipartite_size * (network.size(nw) - bipartite_size)
  } else if (network::is.directed(nw)) {
    network.size(nw) * (network.size(nw) - 1L)
  } else {
    choose(network.size(nw), 2L)
  }

  list(
    status = "ok",
    formula = formula_text,
    terms = terms,
    network = list(
      vertices = network.size(nw),
      edges = network.edgecount(nw),
      directed = network::is.directed(nw),
      bipartite = network::is.bipartite(nw),
      density = network.edgecount(nw) / possible_dyads
    ),
    coefficients = summary_table,
    mcmc_settings = list(burnin = burnin, interval = interval, maxit = maxit, seed = as.integer(control_spec$seed %||% 20261028L)),
    warnings = unique(warnings),
    interpretation_note = "Coefficients are conditional log-odds contributions for the stated change statistics, support, and model specification. They are not marginal probabilities or causal effects."
  )
}

`%||%` <- function(left, right) if (is.null(left)) right else left

payload <- tryCatch(jsonlite::fromJSON(input_path, simplifyDataFrame = TRUE), error = function(error) error)
if (inherits(payload, "error")) {
  write_result(list(status = "error", message = safe_message(payload)))
  quit(status = 0L)
}
result <- tryCatch(fit_model(payload), error = function(error) list(status = "error", message = safe_message(error)))
write_result(result)
