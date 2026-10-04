from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="No-Code Statistical Network Modeling", page_icon="◌", layout="wide"
)
st.title("No-Code Statistical Network Modeling")
st.subheader("A computational companion to A Guide to Statistical Network Modeling")
st.markdown(
    "This public companion app makes documented network-model computations inspectable without requiring participants to write code. Each session page separates data support, model specification, computation, diagnostics, interpretation, and limits."
)
st.info(
    "Session 1.1 is available now: Foundations of Static Exponential-Family Random Graph Models. Use the sidebar to open the session page."
)
st.markdown("### Academic principles")
st.markdown(
    "- **Network support comes first:** directedness, bipartite structure, structural zeros, missingness, and boundaries define the model.\n- **No automatic causal language:** ERGM coefficients are conditional model-based associations unless a separate design warrants more.\n- **No silent recoding:** valued, temporal, multiplex, or incomplete data are not forced into a binary static ERGM workflow.\n- **Reproducibility:** public sources, formulas, MCMC settings, warnings, and limitations appear in a downloadable computation record."
)
