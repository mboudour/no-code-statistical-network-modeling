#!/usr/bin/env Rscript
# Fit an explicitly specified actor-oriented network model with RSiena and return
# JSON-safe estimates plus simulation-based goodness-of-fit summaries. The script
# never installs packages and runs only in the pre-provisioned Docker image.

suppressPackageStartupMessages({
  library(RSiena)
  library(jsonlite)
})

arguments <- commandArgs(trailingOnly = TRUE)
if (length(arguments) != 2) stop("Usage: fit_saom.R input.json output.json")
input_path <- arguments[[1]]
output_path <- arguments[[2]]

write_result <- function(value) {
  jsonlite::write_json(value, output_path, auto_unbox = TRUE, pretty = TRUE, na = "null", null = "null")
}

as_message <- function(error) {
  conditionMessage(error)
}

safe_include <- function(effects, ..., notes) {
  result <- tryCatch(includeEffects(effects, ..., verbose = FALSE), error = identity)
  if (inherits(result, "error")) {
    notes[[length(notes) + 1L]] <- paste0("Requested effect was not included: ", as_message(result))
    return(list(effects = effects, notes = notes))
  }
  list(effects = result, notes = notes)
}

serialize_gof <- function(gof, label) {
  joint <- gof$Joint
  simulations <- as.matrix(joint$Simulations)
  observations <- as.numeric(joint$Observations)
  keys <- attr(joint, "key")
  if (is.null(keys)) keys <- as.character(seq_along(observations))
  if (ncol(simulations) != length(observations)) {
    return(list(label = label, status = "unavailable", reason = "Unexpected RSiena GOF matrix dimensions.", rows = list()))
  }
  rows <- lapply(seq_along(observations), function(index) {
    draws <- simulations[, index]
    list(
      statistic = as.character(keys[[index]]),
      observed = observations[[index]],
      simulated_mean = mean(draws),
      simulated_lower_025 = as.numeric(stats::quantile(draws, 0.025, names = FALSE)),
      simulated_upper_975 = as.numeric(stats::quantile(draws, 0.975, names = FALSE))
    )
  })
  list(
    label = label,
    status = "ok",
    joint_p_value = joint$p,
    rows = rows
  )
}

safe_gof <- function(fit, function_value, variable_name, label, iterations, notes) {
  result <- tryCatch(
    sienaGOF(fit, function_value, varName = variable_name, iterations = iterations, verbose = FALSE),
    error = identity
  )
  if (inherits(result, "error")) {
    notes[[length(notes) + 1L]] <- paste0(label, " GOF unavailable: ", as_message(result))
    return(list(result = list(label = label, status = "unavailable", reason = as_message(result), rows = list()), notes = notes))
  }
  list(result = serialize_gof(result, label), notes = notes)
}

run_fit <- function(payload) {
  actors <- as.character(unlist(payload$actors))
  waves <- as.character(unlist(payload$waves))
  if (length(actors) < 5L || length(waves) < 2L) stop("A Day 3 SAOM requires at least five balanced actors and two observed waves.")
  actor_index <- stats::setNames(seq_along(actors), actors)
  wave_index <- stats::setNames(seq_along(waves), waves)
  directed <- isTRUE(payload$directed)
  adjacency <- array(0L, dim = c(length(actors), length(actors), length(waves)))
  for (edge in payload$edges) {
    i <- actor_index[[as.character(edge$source)]]
    j <- actor_index[[as.character(edge$target)]]
    t <- wave_index[[as.character(edge$wave)]]
    if (is.null(i) || is.null(j) || is.null(t) || i == j) next
    adjacency[i, j, t] <- 1L
    if (!directed) adjacency[j, i, t] <- 1L
  }
  network <- sienaDependent(adjacency, type = "oneMode")
  behavior_name <- if (is.null(payload$behavior_name)) NULL else as.character(payload$behavior_name)
  data_arguments <- list(friendship = network)
  if (!is.null(behavior_name) && nzchar(behavior_name)) {
    values <- matrix(NA_real_, nrow = length(actors), ncol = length(waves))
    for (observation in payload$behavior) {
      i <- actor_index[[as.character(observation$id)]]
      t <- wave_index[[as.character(observation$wave)]]
      if (!is.null(i) && !is.null(t)) values[i, t] <- as.numeric(observation$value)
    }
    if (anyNA(values) || length(unique(as.vector(values))) < 2L) stop("The behavior payload is incomplete or constant after balancing.")
    data_arguments$behavior <- sienaDependent(values, type = "behavior")
  }
  data_object <- do.call(sienaDataCreate, data_arguments)
  effects <- getEffects(data_object)
  notes <- list()
  included <- safe_include(effects, density, name = "friendship", notes = notes)
  effects <- included$effects; notes <- included$notes
  if (directed) {
    included <- safe_include(effects, recip, name = "friendship", notes = notes)
    effects <- included$effects; notes <- included$notes
  }
  included <- if (directed) {
    safe_include(effects, transTrip, name = "friendship", notes = notes)
  } else {
    safe_include(effects, transTriads, name = "friendship", notes = notes)
  }
  effects <- included$effects; notes <- included$notes
  if (!is.null(behavior_name) && nzchar(behavior_name)) {
    included <- safe_include(effects, egoX, altX, simX, interaction1 = "behavior", name = "friendship", notes = notes)
    effects <- included$effects; notes <- included$notes
    included <- safe_include(effects, linear, quad, avSim, interaction1 = "friendship", name = "behavior", notes = notes)
    effects <- included$effects; notes <- included$notes
  }
  algorithm <- sienaAlgorithmCreate(
    projname = tempfile(pattern = "day3_saom_"),
    n3 = max(40L, min(as.integer(payload$n3), 2000L)),
    nsub = 2L,
    seed = as.integer(payload$seed),
    useStdInits = TRUE,
    silent = TRUE
  )
  fit <- siena07(algorithm, data = data_object, effects = effects, batch = TRUE, verbose = FALSE, returnDeps = TRUE)
  effect_names <- rownames(fit$covtheta)
  requested_effects <- as.data.frame(fit$requestedEffects)
  requested_effects <- requested_effects[requested_effects$include, , drop = FALSE]
  if (is.null(effect_names) || length(effect_names) != length(fit$theta)) {
    effect_names <- requested_effects$effectName
    if (length(effect_names) != length(fit$theta) && !is.null(behavior_name) && nzchar(behavior_name)) {
      network_effects <- requested_effects$effectName[requested_effects$name == "friendship"]
      behavior_effects <- requested_effects$effectName[requested_effects$name == "behavior"]
      effect_names <- c(
        paste0("friendship rate (period ", seq_len(length(waves) - 1L), ")"),
        network_effects,
        paste0(behavior_name, " rate (period ", seq_len(length(waves) - 1L), ")"),
        behavior_effects
      )
    }
  }
  if (length(effect_names) != length(fit$theta)) effect_names <- paste0("effect_", seq_along(fit$theta))
  if (!is.null(behavior_name) && nzchar(behavior_name)) effect_names <- gsub("behavior", behavior_name, effect_names, fixed = TRUE)
  coefficients <- lapply(seq_along(fit$theta), function(index) {
    list(
      effect = effect_names[[index]],
      estimate = fit$theta[[index]],
      standard_error = fit$se[[index]],
      convergence_t_ratio = fit$tstat[[index]]
    )
  })
  gof_iterations <- max(20L, min(as.integer(payload$gof_simulations), 200L))
  audits <- list()
  output <- safe_gof(fit, OutdegreeDistribution, "friendship", if (directed) "Out-degree distribution" else "Degree distribution", gof_iterations, notes)
  audits[[length(audits) + 1L]] <- output$result; notes <- output$notes
  if (directed) {
    output <- safe_gof(fit, IndegreeDistribution, "friendship", "In-degree distribution", gof_iterations, notes)
    audits[[length(audits) + 1L]] <- output$result; notes <- output$notes
    output <- safe_gof(fit, TriadCensus, "friendship", "Directed triad census", gof_iterations, notes)
    audits[[length(audits) + 1L]] <- output$result; notes <- output$notes
  }
  if (!is.null(behavior_name) && nzchar(behavior_name)) {
    output <- safe_gof(fit, BehaviorDistribution, "behavior", paste0(behavior_name, " distribution"), gof_iterations, notes)
    audits[[length(audits) + 1L]] <- output$result; notes <- output$notes
  }
  list(
    status = "ok",
    model_class = if (is.null(behavior_name) || !nzchar(behavior_name)) "RSiena network-only SAOM" else "RSiena joint network–behavior coevolution SAOM",
    data_label = payload$label,
    actors = length(actors),
    waves = length(waves),
    directed = directed,
    behavior_name = behavior_name,
    settings = list(n3 = algorithm$n3, gof_simulations = gof_iterations, seed = payload$seed),
    coefficients = coefficients,
    convergence = list(
      fit_ok = isTRUE(fit$OK),
      maximum_convergence_ratio = as.numeric(fit$tconv.max)[[1]],
      per_effect_t_ratios = lapply(seq_along(fit$tstat), function(index) list(effect = effect_names[[index]], t_ratio = fit$tstat[[index]]))
    ),
    goodness_of_fit = audits,
    notes = notes,
    interpretation_boundary = payload$model_boundary
  )
}

payload <- tryCatch(jsonlite::fromJSON(input_path, simplifyVector = FALSE), error = identity)
if (inherits(payload, "error")) {
  write_result(list(status = "error", message = as_message(payload)))
  quit(status = 1L)
}
result <- tryCatch(run_fit(payload), error = identity)
if (inherits(result, "error")) {
  write_result(list(status = "error", message = as_message(result)))
  quit(status = 1L)
}
write_result(result)
