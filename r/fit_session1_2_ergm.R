#!/usr/bin/env Rscript
# Fit a support-aware Session 1.2 static ERGM and return standard MCMC and
# simulation-based goodness-of-fit diagnostics as structured JSON.

suppressPackageStartupMessages({
  library(jsonlite)
  library(network)
  library(ergm)
})

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 2L) {
  stop("Usage: Rscript fit_session1_2_ergm.R INPUT.json OUTPUT.json")
}
input_path <- args[[1L]]
output_path <- args[[2L]]

`%||%` <- function(left, right) if (is.null(left)) right else left

write_result <- function(value) {
  jsonlite::write_json(value, output_path, auto_unbox = TRUE, pretty = TRUE, na = "null")
}

safe_message <- function(error) conditionMessage(error)

as_character <- function(x) as.character(unlist(x, use.names = FALSE))

safe_numeric <- function(x) {
  values <- as.numeric(x)
  values[!is.finite(values)] <- NA_real_
  values
}

safe_quantile <- function(values, probability) {
  values <- values[is.finite(values)]
  if (!length(values)) return(NA_real_)
  as.numeric(stats::quantile(values, probs = probability, names = FALSE, type = 8))
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
    stop("Session 1.2 supports loopless graphs only.")
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

curve_call <- function(name, controls) {
  fixed <- isTRUE(controls$fixed_decay)
  decay <- as.numeric(controls$decay %||% 0.5)
  if (!is.finite(decay) || decay <= 0) {
    stop("The geometrically weighted decay must be a positive finite number.")
  }
  if (fixed) {
    sprintf("%s(%s, fixed=TRUE)", name, format(decay, trim = TRUE, scientific = FALSE))
  } else {
    sprintf("%s(fixed=FALSE)", name)
  }
}

append_formula_terms <- function(payload, nw) {
  requested <- unique(as_character(payload$formula$terms))
  directed <- network::is.directed(nw)
  bipartite <- network::is.bipartite(nw)
  controls <- payload$formula$curve_controls %||% list()
  terms <- character(0)

  if ("edges" %in% requested) terms <- c(terms, "edges")
  if ("mutual" %in% requested) {
    if (!directed) stop("The mutual term is defined only for directed networks.")
    terms <- c(terms, "mutual")
  }
  if ("gwdegree" %in% requested) {
    if (directed || bipartite) stop("gwdegree requires an undirected one-mode network.")
    terms <- c(terms, curve_call("gwdegree", controls))
  }
  if ("gwesp" %in% requested) {
    if (bipartite) stop("gwesp is not used for the original bipartite incidence support.")
    terms <- c(terms, curve_call("gwesp", controls))
  }
  if ("gwidegree" %in% requested) {
    if (!directed || bipartite) stop("gwidegree requires a directed one-mode network.")
    terms <- c(terms, curve_call("gwidegree", controls))
  }
  if ("gwodegree" %in% requested) {
    if (!directed || bipartite) stop("gwodegree requires a directed one-mode network.")
    terms <- c(terms, curve_call("gwodegree", controls))
  }
  if ("b1degree2" %in% requested) {
    if (!bipartite) stop("b1degree(2) is defined only for bipartite networks.")
    terms <- c(terms, "b1degree(2)")
  }
  if ("b2degree2" %in% requested) {
    if (!bipartite) stop("b2degree(2) is defined only for bipartite networks.")
    terms <- c(terms, "b2degree(2)")
  }

  if (!length(terms)) stop("Select at least one supported Session 1.2 ERGM term.")
  terms
}

network_adjacency <- function(nw) {
  adjacency <- as.matrix.network.adjacency(nw, matrix.type = "adjacency")
  storage.mode(adjacency) <- "numeric"
  bipartite_count <- network::get.network.attribute(nw, "bipartite")
  if (is.numeric(bipartite_count) && bipartite_count > 0) {
    full <- matrix(0, nrow = network.size(nw), ncol = network.size(nw))
    first <- seq_len(bipartite_count)
    second <- (bipartite_count + 1L):network.size(nw)
    full[first, second] <- adjacency
    full[second, first] <- t(adjacency)
    adjacency <- full
  }
  (adjacency != 0) * 1
}

component_sizes <- function(adjacency, directed) {
  n <- nrow(adjacency)
  if (!n) return(integer(0))
  support <- if (directed) ((adjacency + t(adjacency)) > 0) * 1 else adjacency
  visited <- rep(FALSE, n)
  sizes <- integer(0)
  for (start in seq_len(n)) {
    if (visited[[start]]) next
    queue <- start
    visited[[start]] <- TRUE
    size <- 0L
    while (length(queue)) {
      current <- queue[[1L]]
      queue <- queue[-1L]
      size <- size + 1L
      neighbours <- which(support[current, ] != 0)
      unseen <- neighbours[!visited[neighbours]]
      if (length(unseen)) {
        visited[unseen] <- TRUE
        queue <- c(queue, unseen)
      }
    }
    sizes <- c(sizes, size)
  }
  sort(sizes, decreasing = TRUE)
}

auxiliary_statistics <- function(nw) {
  adjacency <- network_adjacency(nw)
  directed <- network::is.directed(nw)
  bipartite_count <- network::get.network.attribute(nw, "bipartite")
  bipartite <- is.numeric(bipartite_count) && bipartite_count > 0
  components <- component_sizes(adjacency, directed)
  undirected_support <- if (directed) ((adjacency + t(adjacency)) > 0) * 1 else adjacency
  result <- list(
    edges = network.edgecount(nw),
    isolate_count = sum(rowSums(undirected_support) == 0),
    largest_component = if (length(components)) components[[1L]] else 0,
    component_count = length(components)
  )
  if (directed) {
    result$mutual_dyads <- sum(adjacency * t(adjacency)) / 2
  } else if (bipartite) {
    block <- adjacency[seq_len(bipartite_count), (bipartite_count + 1L):nrow(adjacency), drop = FALSE]
    first_overlap <- block %*% t(block)
    second_overlap <- t(block) %*% block
    first_pairs <- first_overlap[upper.tri(first_overlap)]
    second_pairs <- second_overlap[upper.tri(second_overlap)]
    result$mean_first_mode_overlap <- if (length(first_pairs)) mean(first_pairs) else 0
    result$mean_second_mode_overlap <- if (length(second_pairs)) mean(second_pairs) else 0
  } else {
    result$triangle_count <- sum(diag(adjacency %*% adjacency %*% adjacency)) / 6
  }
  result
}

summarize_auxiliary <- function(observed, simulated) {
  keys <- names(observed)
  lapply(keys, function(key) {
    draws <- vapply(simulated, function(item) as.numeric(item[[key]]), numeric(1L))
    list(
      statistic = key,
      observed = as.numeric(observed[[key]]),
      simulated_mean = mean(draws),
      lower_025 = safe_quantile(draws, 0.025),
      median = safe_quantile(draws, 0.5),
      upper_975 = safe_quantile(draws, 0.975)
    )
  })
}

mcmc_diagnostics <- function(fitted) {
  sample_matrix <- tryCatch(as.matrix(fitted$sample), error = function(error) NULL)
  if (is.null(sample_matrix) || !nrow(sample_matrix) || !ncol(sample_matrix)) {
    return(list(sample_size = 0L, statistics = list()))
  }
  sample_matrix <- as.matrix(sample_matrix)
  max_rows <- min(nrow(sample_matrix), 300L)
  selected_rows <- seq_len(max_rows)
  stats <- lapply(seq_len(ncol(sample_matrix)), function(column) {
    trace <- safe_numeric(sample_matrix[selected_rows, column])
    finite_trace <- trace[is.finite(trace)]
    if (length(finite_trace) > 2L && stats::sd(finite_trace) > 0) {
      acf_result <- stats::acf(finite_trace, plot = FALSE, lag.max = min(20L, length(finite_trace) - 1L), demean = TRUE)
      autocorrelation <- as.numeric(acf_result$acf)[-1L]
      lags <- as.integer(acf_result$lag)[-1L]
    } else {
      autocorrelation <- numeric(0)
      lags <- integer(0)
    }
    list(
      statistic = colnames(sample_matrix)[[column]],
      trace = trace,
      lags = lags,
      autocorrelation = autocorrelation,
      sample_mean = if (length(finite_trace)) mean(finite_trace) else NA_real_,
      sample_sd = if (length(finite_trace) > 1L) stats::sd(finite_trace) else NA_real_
    )
  })
  list(sample_size = nrow(sample_matrix), statistics = stats)
}

make_gof_table <- function(gof_object, suffix, title) {
  observed <- gof_object[[paste0("obs.", suffix)]]
  simulated <- gof_object[[paste0("sim.", suffix)]]
  if (is.null(observed) || is.null(simulated)) return(NULL)
  observed <- safe_numeric(observed)
  labels <- names(gof_object[[paste0("obs.", suffix)]])
  if (is.null(labels)) labels <- as.character(seq_along(observed))
  simulated <- as.matrix(simulated)
  if (!nrow(simulated)) return(NULL)
  list(
    title = title,
    labels = as.character(labels),
    observed = observed,
    simulated_mean = apply(simulated, 2L, mean),
    lower_025 = apply(simulated, 2L, safe_quantile, probability = 0.025),
    median = apply(simulated, 2L, safe_quantile, probability = 0.5),
    upper_975 = apply(simulated, 2L, safe_quantile, probability = 0.975)
  )
}

run_gof <- function(fitted, nw, controls, warnings) {
  directed <- network::is.directed(nw)
  bipartite <- network::is.bipartite(nw)
  nsim <- as.integer(controls$gof_nsim %||% 50L)
  nsim <- max(10L, min(nsim, 100L))
  seed <- as.integer(controls$seed %||% 20261028L) + 1001L
  if (bipartite) {
    gof_formula <- ~b1degree + b2degree + distance
    requested <- list(c("b1deg", "First-mode degree distribution"), c("b2deg", "Second-mode degree distribution"), c("dist", "Bipartite geodesic-distance distribution"))
  } else if (directed) {
    gof_formula <- ~idegree + odegree + distance + triadcensus
    requested <- list(c("ideg", "In-degree distribution"), c("odeg", "Out-degree distribution"), c("dist", "Directed geodesic-distance distribution"), c("triadcensus", "Directed triad census"))
  } else {
    gof_formula <- ~degree + distance + espartners + dspartners
    requested <- list(c("deg", "Degree distribution"), c("dist", "Geodesic-distance distribution"), c("espart", "Edgewise shared-partner distribution"), c("dspart", "Dyadwise shared-partner distribution"))
  }
  gof_warnings <- character(0)
  gof_object <- tryCatch(
    withCallingHandlers(
      ergm::gof(fitted, GOF = gof_formula, control = ergm::control.gof.ergm(nsim = nsim, seed = seed)),
      warning = function(warning) {
        gof_warnings <<- c(gof_warnings, conditionMessage(warning))
        invokeRestart("muffleWarning")
      }
    ),
    error = function(error) error
  )
  if (inherits(gof_object, "error")) {
    return(list(status = "unavailable", message = safe_message(gof_object), warnings = unique(gof_warnings), tables = list(), nsim = nsim))
  }
  tables <- lapply(requested, function(item) make_gof_table(gof_object, item[[1L]], item[[2L]]))
  tables <- Filter(Negate(is.null), tables)
  list(status = "ok", warnings = unique(gof_warnings), tables = tables, nsim = nsim)
}

fit_model <- function(payload) {
  warnings <- character(0)
  messages <- character(0)
  nw <- build_network(payload)
  terms <- append_formula_terms(payload, nw)
  formula_text <- paste("nw ~", paste(terms, collapse = " + "))
  controls <- payload$controls %||% list()
  burnin <- as.integer(controls$mcmc_burnin %||% 5000L)
  interval <- as.integer(controls$mcmc_interval %||% 1000L)
  maxit <- as.integer(controls$mcmle_maxit %||% 8L)
  seed <- as.integer(controls$seed %||% 20261028L)
  return_stats <- as.integer(controls$mcmc_return_stats %||% 128L)
  control <- ergm::control.ergm(
    MCMC.burnin = burnin,
    MCMC.interval = interval,
    MCMLE.maxit = maxit,
    MCMC.return.stats = return_stats,
    seed = seed
  )
  fitted <- withCallingHandlers(
    ergm::ergm(stats::as.formula(formula_text), control = control),
    warning = function(warning) {
      warnings <<- c(warnings, conditionMessage(warning))
      invokeRestart("muffleWarning")
    },
    message = function(message) {
      message_text <- conditionMessage(message)
      if (grepl("converg|degener|mix|fail|nonident", message_text, ignore.case = TRUE)) {
        messages <<- c(messages, message_text)
      }
      invokeRestart("muffleMessage")
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
  gof <- run_gof(fitted, nw, controls, warnings)
  simulation_warnings <- character(0)
  auxiliary_simulations <- tryCatch(
    withCallingHandlers(
      stats::simulate(fitted, nsim = gof$nsim, seed = seed + 2002L, output = "network"),
      warning = function(warning) {
        simulation_warnings <<- c(simulation_warnings, conditionMessage(warning))
        invokeRestart("muffleWarning")
      }
    ),
    error = function(error) error
  )
  observed_auxiliary <- auxiliary_statistics(nw)
  if (inherits(auxiliary_simulations, "error")) {
    auxiliary <- list(status = "unavailable", message = safe_message(auxiliary_simulations), warnings = unique(simulation_warnings), summaries = list())
  } else {
    if (inherits(auxiliary_simulations, "network")) auxiliary_simulations <- list(auxiliary_simulations)
    simulated_auxiliary <- lapply(auxiliary_simulations, auxiliary_statistics)
    auxiliary <- list(status = "ok", warnings = unique(simulation_warnings), summaries = summarize_auxiliary(observed_auxiliary, simulated_auxiliary))
  }

  diagnostic_flags <- unique(c(
    warnings,
    messages,
    gof$warnings,
    auxiliary$warnings
  ))
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
    mcmc_settings = list(burnin = burnin, interval = interval, maxit = maxit, return_stats = return_stats, seed = seed),
    estimation = list(
      mcmle_iterations = as.integer(fitted$iterations %||% NA_integer_),
      failure_flag = isTRUE(fitted$failure),
      diagnostic_rule = "Do not treat completion or a false failure flag as proof of convergence. Inspect the returned trace, autocorrelation, warnings, score-related messages, and repeated fits."
    ),
    warnings = unique(warnings),
    diagnostic_flags = diagnostic_flags,
    mcmc_diagnostics = mcmc_diagnostics(fitted),
    gof = gof,
    auxiliary_simulation_checks = auxiliary,
    interpretation_note = "This is a conditional graph-distribution model. MCMC behavior, simulation-based goodness of fit, and the stated support must be reviewed before interpreting coefficients. Neither coefficient signs nor apparent GOF establish causal effects or automatic model selection."
  )
}

payload <- tryCatch(jsonlite::fromJSON(input_path, simplifyDataFrame = TRUE), error = function(error) error)
if (inherits(payload, "error")) {
  write_result(list(status = "error", message = safe_message(payload)))
  quit(status = 0L)
}
result <- tryCatch(fit_model(payload), error = function(error) list(status = "error", message = safe_message(error)))
write_result(result)
