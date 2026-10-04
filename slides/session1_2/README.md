# Session 1.2 Beamer deck

- `session1_2.tex` is the complete source for **Session 1.2: Curved ERGMs, Fit, and Degeneracy**.
- `session1_2.pdf` is the compiled deck.
- `first_slide.pdf`, `second_slide.pdf`, and `last_slide.pdf` are the supplied repeating template assets.

## Build

```bash
cd slides/session1_2
pdflatex -interaction=nonstopmode -halt-on-error session1_2.tex
pdflatex -interaction=nonstopmode -halt-on-error session1_2.tex
```

The source contains **49 authored frames**, exceeding the 35-substantive-frame minimum. It defines curved ERGMs, geometrically weighted terms, convergence, degeneracy, standard support-specific goodness of fit, and the exact five Session 1.2 public computations. The fourth authored frame identifies the **Streamlit app hosted on Render** and links to it; the final discussion frame includes both Northwestern and Gmail contact addresses.
