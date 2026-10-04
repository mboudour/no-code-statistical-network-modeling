# Day 3 public SAOM data curation

## Scope

This curation covers the two Day 3 sessions:

- **Session 3.1 — SAOMs for Actor-Driven Network Dynamics**
- **Session 3.2 — SAOMs for Selection and Influence**

The research distinguishes a repeated network panel from a network–behavior panel. A selection-and-influence coevolution SAOM requires both a repeated network and a repeatedly measured actor behavior; a repeated network alone is not enough.

## Verified public sources

| Release / panel | Repeated network | Repeated actor behavior | Day 3 use | Public source |
|---|---|---|---|---|
| Knecht Dutch classroom / `klas12b` | Four directed friendship waves for 26 pupils | Delinquency at all four waves; alcohol at waves 2–4 | 3.1 and 3.2 | https://www.stats.ox.ac.uk/~snijders/siena/tutorial2010_data.htm |
| RSiena `s50` teaching excerpt | Three directed friendship waves for 50 girls | Alcohol and smoking measured at three waves | 3.1 and 3.2 | https://www.stats.ox.ac.uk/~snijders/siena/s50_data.zip |
| Teenage Friends and Lifestyle Study, full Glasgow release | Three directed friendship waves, with documented composition information | Alcohol, tobacco/smoking, cannabis, pocket money, romantic relationship, music taste, and leisure measures | 3.1 and 3.2 | https://www.stats.ox.ac.uk/~snijders/siena/Glasgow_data.htm |
| Coleman high school | Two directed friendship waves | No verified repeated behavior | 3.1 only | https://search.r-project.org/CRAN/refmans/sna/html/coleman.html |
| COW Formal Alliances v4.1 | Annual alliance records can be constructed into binary snapshots with explicit membership/support assumptions | No verified repeated behavior | Qualified 3.1 only | https://correlatesofwar.org/data-sets/formal-alliances/ |

## Required exclusions

- **Sampson liking** is retrospective rather than a truly longitudinal panel and has no verified repeated actor behavior; it is not used for Day 3 coevolution.
- **Windsurfers** is documented as one weighted network, not a repeated behavior-ready panel; it is not used for Day 3 SAOMs.
- **Coleman** and **COW** are not used in Session 3.2 because their public releases do not document a repeated actor behavior.

## Five Session 3.2 worked specifications

The public evidence supports three underlying coevolution releases, not five independent studies. To satisfy the seminar requirement for **five worked examples** without inventing data, the app and slides will label the following as five **public worked specifications**, explicitly stating when a base release is reused with a different repeatedly measured behavior:

1. Knecht friendship–delinquency (four waves).
2. Knecht friendship–alcohol (waves 2–4; wave 1 is unavailable by design).
3. Full Glasgow friendship–alcohol (three waves).
4. Full Glasgow friendship–cannabis (three waves).
5. RSiena `s50` friendship–smoking (three waves; numerical-teaching excerpt from the broader Glasgow study).

This is transparent reuse for distinct selection/influence specifications, not a claim of five independent public studies.

## Source limitations to state in every workflow

- The Knecht panel has documented nomination/attribute missingness and a pupil composition change.
- The full Glasgow release has composition changes; the `s50` subset is explicitly a numerical teaching excerpt, not a properly delineated population network.
- Alcohol in Knecht begins at wave 2.
- A coevolution SAOM distinguishes modeled selection and influence components but does not by itself establish causal peer influence.

## Verified downloadable archive contents

- `s50_data.zip` contains `s50-network1.dat` through `s50-network3.dat`, plus repeated alcohol, smoking, drugs/cannabis, sport, and family-event files.
- `klas12b.zip` contains four classroom network matrices, `klas12b-delinquency.dat`, `klas12b-alcohol.dat`, documented presence information, and source readme/script files.
- `Glasgow_data.zip` contains the full release's friendship, substances, lifestyle, demographic, geographic, selection, and composition-change RData files. The extraction pipeline must preserve the public release's coding and document every binary-response transformation.
