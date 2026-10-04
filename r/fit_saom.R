#!/usr/bin/env Rscript
# Fit explicitly specified actor-oriented models and return source-transparent,
# simulation-based diagnostics. This script never installs packages and is run only
# in the pre-provisioned Docker image.

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

as_message <- function(error) conditionMessage(error)

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
      simulated_mean = mean(draws, na.rm = TRUE),
      simulated_lower_025 = as.numeric(stats::quantile(draws, 0.025, names = FALSE, na.rm = TRUE)),
      simulated_upper_975 = as.numeric(stats::quantile(draws, 0.975, names = FALSE, na.rm = TRUE))
    )
  })
  list(label = label, status = "ok", joint_p_value = joint$p, rows = rows)
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

# Custom sienaGOF functions receive either the observed end state (i = NULL) or
# the fitted simulation at the end of an observed period. They all use fixed-size
# vectors so that RSiena can compare observed and simulated statistics fairly.
network_matrix <- function(i, obsData, sims, period, groupName, varName) {
  as.matrix(RSiena:::sparseMatrixExtraction(i, obsData, sims, period, groupName, varName))
}

behavior_vector <- function(i, obsData, sims, period, groupName, varName) {
  as.numeric(RSiena:::behaviorExtraction(i, obsData, sims, period, groupName, varName))
}

previous_behavior_vector <- function(obsData, period, groupName, varName) {
  as.numeric(obsData[[groupName]]$depvars[[varName]][, , period])
}

behavior_levels <- function(obsData, groupName, varName) {
  bounds <- attr(obsData[[groupName]]$depvars[[varName]], "behRange")
  seq.int(as.integer(bounds[[1]]), as.integer(bounds[[2]]))
}

geodesic_distribution <- function(adjacency, max_distance = 6L) {
  n <- nrow(adjacency)
  counts <- stats::setNames(rep(0, max_distance + 1L), c(as.character(seq_len(max_distance)), paste0(">=", max_distance + 1L, " or unreachable")))
  for (source in seq_len(n)) {
    seen <- rep(FALSE, n)
    seen[[source]] <- TRUE
    frontier <- source
    for (distance in seq_len(max_distance)) {
      if (!length(frontier)) break
      candidates <- which(colSums(adjacency[frontier, , drop = FALSE]) > 0)
      new_nodes <- candidates[!seen[candidates]]
      if (length(new_nodes)) {
        counts[[as.character(distance)]] <- counts[[as.character(distance)]] + length(new_nodes)
        seen[new_nodes] <- TRUE
      }
      frontier <- new_nodes
    }
    counts[[max_distance + 1L]] <- counts[[max_distance + 1L]] + sum(!seen)
  }
  counts
}

weak_component_summary <- function(adjacency) {
  adjacency <- (adjacency + t(adjacency)) > 0
  n <- nrow(adjacency)
  seen <- rep(FALSE, n)
  sizes <- integer(0)
  for (source in seq_len(n)) {
    if (seen[[source]]) next
    component <- source
    seen[[source]] <- TRUE
    frontier <- source
    while (length(frontier)) {
      candidates <- which(colSums(adjacency[frontier, , drop = FALSE]) > 0)
      new_nodes <- candidates[!seen[candidates]]
      seen[new_nodes] <- TRUE
      component <- c(component, new_nodes)
      frontier <- new_nodes
    }
    sizes <- c(sizes, length(component))
  }
  c(
    isolates = sum(rowSums(adjacency) == 0),
    weak_components = length(sizes),
    largest_weak_component = max(sizes)
  )
}

NetworkStructuralAudit <- function(i, obsData, sims, period, groupName, varName) {
  adjacency <- network_matrix(i, obsData, sims, period, groupName, varName)
  geodesics <- geodesic_distribution(adjacency)
  shared <- adjacency %*% adjacency
  max_bin <- 3L
  per_dyad <- shared[row(adjacency) != col(adjacency)]
  shared_bins <- stats::setNames(
    c(vapply(0:max_bin, function(level) sum(per_dyad == level), numeric(1)), sum(per_dyad > max_bin)),
    c(paste0("closure/shared partners=", 0:max_bin), paste0("closure/shared partners>=", max_bin + 1L))
  )
  components <- weak_component_summary(adjacency)
  c(geodesics, shared_bins, components)
}

DirectedReciprocityAudit <- function(i, obsData, sims, period, groupName, varName) {
  adjacency <- network_matrix(i, obsData, sims, period, groupName, varName)
  mutual_dyads <- sum(adjacency * t(adjacency)) / 2
  c(
    mutual_dyads = mutual_dyads,
    reciprocal_tie_share = if (sum(adjacency) > 0) 2 * mutual_dyads / sum(adjacency) else 0
  )
}

TiedBehaviorMixingAudit <- function(i, obsData, sims, period, groupName, varName) {
  behavior <- behavior_vector(i, obsData, sims, period, groupName, "behavior")
  adjacency <- network_matrix(i, obsData, sims, period, groupName, "friendship")
  levels <- behavior_levels(obsData, groupName, "behavior")
  rows <- which(adjacency > 0, arr.ind = TRUE)
  mixing <- matrix(0, nrow = length(levels), ncol = length(levels), dimnames = list(levels, levels))
  if (nrow(rows)) {
    for (index in seq_len(nrow(rows))) {
      ego <- as.character(behavior[[rows[index, 1]]])
      alter <- as.character(behavior[[rows[index, 2]]])
      if (ego %in% rownames(mixing) && alter %in% colnames(mixing)) mixing[ego, alter] <- mixing[ego, alter] + 1
    }
  }
  output <- as.vector(mixing)
  names(output) <- as.vector(outer(rownames(mixing), colnames(mixing), function(ego, alter) paste0("ego=", ego, " | alter=", alter)))
  output
}

SelectionAssociationAudit <- function(i, obsData, sims, period, groupName, varName) {
  behavior <- behavior_vector(i, obsData, sims, period, groupName, "behavior")
  adjacency <- network_matrix(i, obsData, sims, period, groupName, "friendship")
  levels <- behavior_levels(obsData, groupName, "behavior")
  span <- max(levels) - min(levels)
  rows <- which(adjacency > 0, arr.ind = TRUE)
  similarity <- if (nrow(rows) && span > 0) mean(1 - abs(behavior[rows[, 1]] - behavior[rows[, 2]]) / span) else 0
  same_score <- if (nrow(rows)) mean(behavior[rows[, 1]] == behavior[rows[, 2]]) else 0
  ego_rates <- vapply(levels, function(value) {
    eligible <- which(behavior == value)
    if (!length(eligible)) return(0)
    sum(adjacency[eligible, , drop = FALSE]) / (length(eligible) * (nrow(adjacency) - 1))
  }, numeric(1))
  alter_rates <- vapply(levels, function(value) {
    eligible <- which(behavior == value)
    if (!length(eligible)) return(0)
    sum(adjacency[, eligible, drop = FALSE]) / (length(eligible) * (nrow(adjacency) - 1))
  }, numeric(1))
  differences <- 0:span
  difference_rates <- vapply(differences, function(difference) {
    mask <- outer(behavior, behavior, function(ego, alter) abs(ego - alter) == difference)
    diag(mask) <- FALSE
    if (!sum(mask)) return(0)
    sum(adjacency[mask]) / sum(mask)
  }, numeric(1))
  c(
    `joint tied-actor similarity` = similarity,
    `homophily same-score tie proportion` = same_score,
    stats::setNames(ego_rates, paste0("tie rate | ego=", levels)),
    stats::setNames(alter_rates, paste0("tie rate | alter=", levels)),
    stats::setNames(difference_rates, paste0("tie rate | absolute difference=", differences))
  )
}

BehaviorDynamicsAudit <- function(i, obsData, sims, period, groupName, varName) {
  current <- behavior_vector(i, obsData, sims, period, groupName, "behavior")
  previous <- previous_behavior_vector(obsData, period, groupName, "behavior")
  levels <- behavior_levels(obsData, groupName, "behavior")
  span <- max(levels) - min(levels)
  changes <- current - previous
  change_levels <- seq.int(-span, span)
  distribution <- vapply(change_levels, function(value) sum(changes == value, na.rm = TRUE), numeric(1))
  names(distribution) <- paste0("behavior change=", change_levels)
  distribution
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
    list(effect = effect_names[[index]], estimate = fit$theta[[index]], standard_error = fit$se[[index]], convergence_t_ratio = fit$tstat[[index]])
  })
  # For a network-only fit, RSiena stores period-specific opportunity rates in
  # `rate`/`vrate` rather than in the evaluation-effect theta vector. Preserve
  # them in the app output so the coefficient view never conceals rates.
  if ((is.null(behavior_name) || !nzchar(behavior_name)) && length(fit$rate)) {
    rate_se <- sqrt(pmax(as.numeric(fit$vrate), 0))
    network_rates <- lapply(seq_along(fit$rate), function(index) {
      list(
        effect = paste0("constant friendship rate (period ", index, ")"),
        estimate = as.numeric(fit$rate[[index]]),
        standard_error = rate_se[[index]],
        convergence_t_ratio = NA_real_
      )
    })
    coefficients <- c(network_rates, coefficients)
    notes[[length(notes) + 1L]] <- "RSiena returns network-only period rates separately from evaluation effects; their estimates and standard errors are shown, while the returned individual convergence t-ratios apply to the evaluation-effect vector."
  }
  gof_iterations <- max(20L, min(as.integer(payload$gof_simulations), 200L))
  audits <- list()
  output <- safe_gof(fit, OutdegreeDistribution, "friendship", if (directed) "Out-degree distribution" else "Degree distribution", gof_iterations, notes)
  audits[[length(audits) + 1L]] <- output$result; notes <- output$notes
  if (directed) {
    output <- safe_gof(fit, IndegreeDistribution, "friendship", "In-degree distribution", gof_iterations, notes)
    audits[[length(audits) + 1L]] <- output$result; notes <- output$notes
    output <- safe_gof(fit, TriadCensus, "friendship", "Directed triad census", gof_iterations, notes)
    audits[[length(audits) + 1L]] <- output$result; notes <- output$notes
    output <- safe_gof(fit, DirectedReciprocityAudit, "friendship", "Reciprocity count", gof_iterations, notes)
    audits[[length(audits) + 1L]] <- output$result; notes <- output$notes
  }
  output <- safe_gof(fit, NetworkStructuralAudit, "friendship", if (directed) "Geodesic, closure, and component structural audit" else "Geodesic, shared-partner closure, and component structural audit", gof_iterations, notes)
  audits[[length(audits) + 1L]] <- output$result; notes <- output$notes
  if (!is.null(behavior_name) && nzchar(behavior_name)) {
    output <- safe_gof(fit, BehaviorDistribution, "behavior", paste0(behavior_name, " distribution"), gof_iterations, notes)
    audits[[length(audits) + 1L]] <- output$result; notes <- output$notes
    output <- safe_gof(fit, BehaviorDynamicsAudit, "behavior", paste0(behavior_name, " change distribution"), gof_iterations, notes)
    audits[[length(audits) + 1L]] <- output$result; notes <- output$notes
    output <- safe_gof(fit, TiedBehaviorMixingAudit, "friendship", "Observed-versus-simulated tied-actor behavior mixing matrix", gof_iterations, notes)
    audits[[length(audits) + 1L]] <- output$result; notes <- output$notes
    output <- safe_gof(fit, SelectionAssociationAudit, "friendship", "Joint network-behavior association and selection audit", gof_iterations, notes)
    audits[[length(audits) + 1L]] <- output$result; notes <- output$notes
  }
  list(
    status = "ok",
    model_class = if (is.null(behavior_name) || !nzchar(behavior_name)) "RSiena network-only SAOM" else "RSiena joint network–behavior coevolution SAOM",
    data_label = payload$label,
    actors = length(actors), waves = length(waves), directed = directed, behavior_name = behavior_name,
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
