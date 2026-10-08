# References

Scope v2.1 and the reference implementation both make claims that trace to published work — algorithms named but not cited, thresholds stated as fact, methodological choices with a literature behind them. This page supplies the citations.

Entries marked **[implemented]** correspond to something in the codebase; **[claim]** backs a number or assertion in the scope; **[precedent]** is prior work the design either follows or should be measured against.

---

## 1. Tropical cyclone data

**Landsea, C. W., and J. L. Franklin, 2013:** Atlantic hurricane database uncertainty and presentation of a new database format. *Monthly Weather Review*, **141**(10), 3576–3592.
[doi:10.1175/MWR-D-12-00254.1](https://doi.org/10.1175/MWR-D-12-00254.1) · [PDF](https://www.nhc.noaa.gov/pdf/landsea-franklin-mwr2013.pdf)

**[implemented] The single most relevant paper to [Train/Serve Consistency](Train-Serve-Consistency).** It is both the HURDAT2 format reference and the quantification of best-track uncertainty, derived from a survey of the NHC Hurricane Specialists who build the tracks. Two things it establishes that the implementation depends on:

- <cite index="20-1">NHC best tracks are recorded at a precision of 5 kt for intensity, 1 mb for pressure, and 0.1° latitude/longitude — roughly 6 n mi</cite>. This is exactly the quantisation `emulate_working_fix()` applies, and `test_quantisation_can_leave_a_position_unchanged` pins.
- <cite index="11-1">A best track is a subjectively *smoothed* representation of a storm's history, based on a poststorm assessment of all available data</cite>, and <cite index="11-1">variations with periods shorter than 24 h are typically not captured</cite>. That smoothing is the leakage the working/final split exists to prevent — it is a property of the product, not an artefact.

**Torn, R. D., and C. Snyder, 2012:** Uncertainty of tropical cyclone best-track information. *Weather and Forecasting*, **27**(3), 715–729.
[doi:10.1175/WAF-D-11-00085.1](https://doi.org/10.1175/WAF-D-11-00085.1)

**[implemented] This is the paper to calibrate `WorkingTrackNoise` against.** It quantifies uncertainty by verifying Dvorak estimates against aircraft reconnaissance. Landsea and Franklin summarise its findings: <cite index="31-1">roughly 10 kt for tropical storms and 12 kt for category 1–2 and satellite-only major hurricanes, with pressure uncertainties near 7 mb for tropical storms, 10 mb for category 1–2, and 12 mb for major hurricanes</cite>.

That matters for the defaults. The implementation ships `intensity_rms_kt=5.0` and `pressure_rms_mb=3.0` as documented placeholders from the scope — **the literature suggests both are optimistic by roughly a factor of two**, and the pressure figure by more. The papers also find uncertainty is *intensity-dependent* (<cite index="29-1">position uncertainty decreases for more intense storms while intensity uncertainty increases with intensity</cite>), which the current scalar-RMS emulator does not represent. Worth folding in when `recalibrate_from_pairs()` runs against a real archive. See [Roadmap](Roadmap).

**Sampson, C. R., and A. J. Schrader, 2000:** The Automated Tropical Cyclone Forecasting System (version 3.2). *Bulletin of the American Meteorological Society*, **81**(6), 1231–1240.
[doi:10.1175/1520-0477(2000)081<1231:TATCFS>2.3.CO;2](https://doi.org/10.1175/1520-0477(2000)081%3C1231:TATCFS%3E2.3.CO;2)

The ATCF reference — the a-deck/b-deck format the working best-track ingestion will parse.

**HURDAT2 format documentation**, NHC: [Atlantic](https://www.nhc.noaa.gov/data/hurdat/hurdat2-format-atlantic.pdf) · [database](https://www.nhc.noaa.gov/data/hurdat/)

---

## 2. Reanalysis and operational analysis

**Hersbach, H., and Coauthors, 2020:** The ERA5 global reanalysis. *Quarterly Journal of the Royal Meteorological Society*, **146**(730), 1999–2049.
[doi:10.1002/qj.3803](https://doi.org/10.1002/qj.3803)

The Stage A pretraining dataset. Also documents the ERA5T preliminary product on which the [skew audit](Monitoring) depends.

---

## 3. Potential intensity

**Emanuel, K. A., 1995:** Sensitivity of tropical cyclones to surface exchange coefficients and a revised steady-state model incorporating eye dynamics. *Journal of the Atmospheric Sciences*, **52**(22), 3969–3976.
[doi:10.1175/1520-0469(1995)052<3969:SOTCTS>2.0.CO;2](https://doi.org/10.1175/1520-0469(1995)052%3C3969:SOTCTS%3E2.0.CO;2)

**Bister, M., and K. A. Emanuel, 1998:** Dissipative heating and hurricane intensity. *Meteorology and Atmospheric Physics*, **65**, 233–240.
[doi:10.1007/BF01030791](https://doi.org/10.1007/BF01030791)

**[implemented, both ways]** Scope §4.3 names "Kerry Emanuel's algorithm" for potential intensity. `features.potential_intensity()` remains an SST/OHC/shear regression standing in for it -- still the pipeline default. `features.emanuel_potential_intensity()` now implements the real closed form: `Vmax² = (Ck/Cd) · (Ts−T0)/T0 · Δk`, with `Δk` (the enthalpy disequilibrium between saturated-surface and boundary-layer air) from Bolton's (1980) saturation vapor pressure formula and standard specific-humidity conversion.

The citation to use is both papers, not just the 1995 one. Emanuel's own description of the operational algorithm notes it <cite index="2-1">generalises the 1995 treatment to an open-cycle heat engine and accounts for dissipative heating, which earlier treatments neglected — modifications described in Bister and Emanuel (1998)</cite>. Reference implementation: [Emanuel's `pcmin` code, MIT](https://emanuel.mit.edu/maximum-intensity-estimation/).

**Why the closed form isn't the pipeline default yet.** It needs a real boundary-layer/outflow sounding to be trustworthy. `GriddedFields` only carries 700 mb-level fields, no near-surface one, so `compare_potential_intensity_estimates()` feeds the closed form a climatological guess (a well-mixed marine boundary layer close to SST). That guess produces PI estimates running systematically hotter than the regression proxy across the whole SST range this system operates in -- a real equation fed fabricated inputs is not an improvement over an honestly-labeled proxy, it just relocates the uncertainty somewhere less visible. Wiring the closed form in for real is tracked with real `GriddedFields` (see [Roadmap](Roadmap) §1's Gridded fields row).

---

## 4. Rapid intensification

**Kaplan, J., and M. DeMaria, 2003:** Large-scale characteristics of rapidly intensifying tropical cyclones in the North Atlantic basin. *Weather and Forecasting*, **18**(6), 1093–1108.
[doi:10.1175/1520-0434(2003)018<1093:LCORIT>2.0.CO;2](https://doi.org/10.1175/1520-0434(2003)018%3C1093:LCORIT%3E2.0.CO;2)

**[implemented]** The source of `RI_THRESHOLD_KT = 30.0` and `RI_WINDOW_HOURS = 24`. Worth knowing where the number comes from: <cite index="74-1">RI is defined as approximately the 95th percentile of over-water 24-h intensity changes for Atlantic storms developing 1989–2000, which works out to a 30 kt increase</cite>. It is a percentile of a continuous distribution, not a physical discontinuity — <cite index="81-1">later work finds no discernible gap near 30 kt/24 h and describes the threshold as a statistical or practical choice</cite>.

So `ri_alert_probability: 0.3` in `monitoring.yaml` is a threshold on a threshold. Both are tunable, and neither is physics.

---

## 5. The cone of uncertainty

**NHC track forecast cone:** [Definition of the NHC Track Forecast Cone](https://www.nhc.noaa.gov/aboutcone.shtml) · [Forecast verification](https://www.nhc.noaa.gov/verification/)

**[implemented]** `CLIMATOLOGICAL_CONE_NM` carries the real current-season (2026) Atlantic radii. The construction: (cite index="85-1">circles are placed along the forecast track, each sized so that two-thirds of historical official forecast errors over a five-year sample fall within it</cite>. Radii are re-derived annually -- the table must be re-pulled from nhc.noaa.gov/aboutcone.shtml every season, not assumed to stay reasonable.

The 2026 Atlantic values (from 2021-25 errors), in n mi: 25 at 12 h, 39 at 24 h, 49 at 36 h, 62 at 48 h, 95 at 72 h, 134 at 96 h and 200 at 120 h. For comparison, the 2023 table (from 2018-22 errors) was 26/39/53/67/99/145/205 (tabulated by [Predicting Tropical Cyclone Track Forecast Errors using a Probabilistic Neural Network](https://arxiv.org/abs/2503.09840), appendix S5) -- the shrinking radii reflect continued NHC track-forecast skill improvement over that period.

**One thing that has changed and the scope does not reflect:** for the 2026 season <cite index="90-1">NHC is issuing an experimental cone graphic built from **ellipses rather than circles**, to account separately for the speed and directional components of forecast error</cite>. That maps directly onto the cross-track/along-track decomposition the implementation already computes in `metrics/track.py` — an elliptical `ConeSegment` is a natural extension and would align the product with where NHC is heading. See [Roadmap](Roadmap).

---

## 6. Machine learning weather prediction

The four papers that constitute the prior art for this system's architecture choices.

**Pathak, J., and Coauthors, 2022:** FourCastNet: A global data-driven high-resolution weather model using adaptive Fourier neural operators.
[arXiv:2202.11214](https://arxiv.org/abs/2202.11214)

**Kurth, T., S. Subramanian, P. Harrington, J. Pathak, M. Mardani, D. Hall, A. Miele, K. Kashinath, and A. Anandkumar, 2023:** FourCastNet: Accelerating global high-resolution weather forecasting using adaptive Fourier neural operators. *Proceedings of the Platform for Advanced Scientific Computing Conference (PASC '23)*, ACM, 1–11.
[doi:10.1145/3592979.3593412](https://doi.org/10.1145/3592979.3593412)

These are two distinct papers, not two versions of one. Pathak (2022) is the model; **Kurth (2023) is the peer-reviewed PASC paper on training and scaling it** — the one to cite when the question is engineering rather than architecture. Given that [Training Architecture](Training-Architecture) budgets 6–7 GPUs and 42–60 hours for a parallel cycle, Kurth is the more directly useful of the two.

**Bi, K., L. Xie, H. Zhang, X. Chen, X. Gu, and Q. Tian, 2023:** Accurate medium-range global weather forecasting with 3D neural networks. *Nature*, **619**(7970), 533–538.
[doi:10.1038/s41586-023-06185-3](https://doi.org/10.1038/s41586-023-06185-3)

Pangu-Weather. The precedent for the [Transformer](Model-Catalog) backbone.

**Lam, R., and Coauthors, 2023:** Learning skillful medium-range global weather forecasting. *Science*, **382**(6677), 1416–1421.
[doi:10.1126/science.adi2336](https://doi.org/10.1126/science.adi2336) · [arXiv:2212.12794](https://arxiv.org/abs/2212.12794) · [code](https://github.com/google-deepmind/graphcast)

GraphCast. **[precedent]** The direct precedent for the GNN component, and specifically for TC work: <cite index="34-1">it outperforms the most accurate operational deterministic systems on 90% of 1380 verification targets, with forecasts supporting better severe event prediction including tropical cyclone tracking</cite>.

**Price, I., and Coauthors, 2025:** Probabilistic weather forecasting with machine learning. *Nature*, **637**(8044), 84–90.
[doi:10.1038/s41586-024-08252-9](https://doi.org/10.1038/s41586-024-08252-9) · [arXiv:2312.15796](https://arxiv.org/abs/2312.15796)

GenCast. **[precedent] The closest published analogue to Anemoi-Spread** — a conditional diffusion model generating weather ensembles, and <cite index="53-1">the first probabilistic ML weather model to significantly outperform ECMWF's ENS at high resolution</cite>.

**It is also independent validation of the entire §4.6 train/serve policy.** GenCast was trained on ERA5, and <cite index="53-1">has since been fine-tuned on operationally available HRES-fc0 data as part of Google's WeatherNext family of operational models</cite> — the released repository <cite index="56-1">provides download links for both ERA5 and operational versions of the model weights</cite>.

That is exactly the Stage A / Stage B structure, arrived at independently by a team shipping an operational system. Pretrain on reanalysis for volume, fine-tune on the operational analysis for deployment, and keep the two sets of weights distinct. Worth citing in §4.6 directly: the policy is not a local invention, it is convergent practice.

---

## 6a. Fast generative sampling

**Song, Y., P. Dhariwal, M. Chen, and I. Sutskever, 2023:** Consistency models. *Proceedings of the 40th International Conference on Machine Learning*, PMLR **202**, 32211–32252.
[proceedings](https://proceedings.mlr.press/v202/song23a.html) · [arXiv:2303.01469](https://arxiv.org/abs/2303.01469)

**[precedent — and the principled fix for the diffusion budget]**

Anemoi-Spread's 13-minute stage budget is the binding constraint on ensemble size, and it is why [load shedding](Inference-Cycle) exists: when the cycle starts late, members get dropped. That is a blunt instrument — it trades tail resolution for punctuality.

Consistency models are the alternative. They (cite index="143-1">generate high-quality samples by directly mapping noise to data, supporting fast one-step generation by design while still allowing multistep sampling to trade compute for sample quality</cite>. Two properties matter here:

- **One-step generation collapses the sampling cost**, which is what the cosine-schedule step count in `build_diffusion` is currently trading against quality.
- **Multistep sampling is still available**, so quality can be dialled up when the schedule permits — a *graded* response to time pressure rather than a binary shed.

A consistency model can also be **distilled from a trained diffusion model**, so this need not be an architectural commitment made up front. Train Anemoi-Spread as a diffusion model, distil for the operational path if the budget binds.

Prior art exists for weather specifically: **Stock, J., T. Arcomano, and R. Kotamarthi, 2025:** SWIFT: An autoregressive consistency model for efficient weather forecasting. [arXiv:2509.25631](https://arxiv.org/abs/2509.25631)

This belongs on the [Roadmap](Roadmap) as the answer to "what if 13 minutes is not enough," ahead of shedding members.

---

## 7. Forecast verification

**Diebold, F. X., and R. S. Mariano, 1995:** Comparing predictive accuracy. *Journal of Business & Economic Statistics*, **13**(3), 253–263.
[doi:10.1080/07350015.1995.10524599](https://doi.org/10.1080/07350015.1995.10524599) · [PDF](https://www.sas.upenn.edu/~fdiebold/papers/paper68/pa.dm.pdf)

**[implemented]** `metrics.track.diebold_mariano`.

**Coroneo, L., and F. Iacone, 2024:** Testing for equal predictive accuracy with strong dependence.
[arXiv:2409.12662](https://arxiv.org/abs/2409.12662)

**[implemented — supports the docstring caveat]** The implementation warns that serially-correlated 6-hourly fixes must be aggregated to one case per storm first. This paper is why: <cite index="103-1">the power of the DM test decreases as dependence in the loss differential increases, and past a certain threshold the test has no power and the correct null is spuriously rejected</cite>. Applied naively to 6-hourly fixes from the same storm, the test would not merely be anti-conservative — it could reject in the wrong direction. `metrics.track.aggregate_by_storm()` collapses per-fix errors to one case per storm; call it before `diebold_mariano` on any multi-fix sample.

**Gneiting, T., and A. E. Raftery, 2007:** Strictly proper scoring rules, prediction, and estimation. *Journal of the American Statistical Association*, **102**(477), 359–378.
[doi:10.1198/016214506000001437](https://doi.org/10.1198/016214506000001437)

**[implemented]** The CRPS form used in `metrics.probabilistic.crps_ensemble` — `E|X − y| − ½E|X − X'|` — is the kernel representation from this paper. It also supplies the property the docstring relies on: for a deterministic forecast, CRPS reduces to absolute error.

Original CRPS: **Matheson, J. E., and R. L. Winkler, 1976:** Scoring rules for continuous probability distributions. *Management Science*, **22**(10), 1087–1096. [doi:10.1287/mnsc.22.10.1087](https://doi.org/10.1287/mnsc.22.10.1087)

**Hamill, T. M., 2001:** Interpretation of rank histograms for verifying ensemble forecasts. *Monthly Weather Review*, **129**(3), 550–560.
[doi:10.1175/1520-0493(2001)129<0550:IORHFV>2.0.CO;2](https://doi.org/10.1175/1520-0493(2001)129%3C0550:IORHFV%3E2.0.CO;2)

**[implemented]** `metrics.probabilistic.rank_histogram`. **Read this before drawing conclusions from one.** Its central point is that a U-shaped histogram does not uniquely indicate underdispersion — observation error and conditional biases produce the same signature. Since underdispersion is the failure mode Anemoi-Spread is most likely to exhibit, this is the paper that stops the diagnostic being over-read.

**Hersbach, H., 2000:** Decomposition of the continuous ranked probability score for ensemble prediction systems. *Weather and Forecasting*, **15**(5), 559–570.
[doi:10.1175/1520-0434(2000)015<0559:DOTCRP>2.0.CO;2](https://doi.org/10.1175/1520-0434(2000)015%3C0559:DOTCRP%3E2.0.CO;2)

Decomposing CRPS into reliability and resolution, useful when a CRPS regression needs diagnosing.

---

## 7a. Intensity predictability and the operational program

**Emanuel, K., and F. Zhang, 2016:** On the predictability and error sources of tropical cyclone intensity forecasts. *Journal of the Atmospheric Sciences*, **73**(9), 3739–3747.
[doi:10.1175/JAS-D-16-0100.1](https://doi.org/10.1175/JAS-D-16-0100.1)

**[claim — the most consequential paper on this page for how the system should be built]**

Two findings, and both change something.

**First, the framing.** (cite index="135-1">The skill of tropical cyclone intensity forecasts has improved slowly since such forecasts became routine, even though track forecast skill has increased markedly over the same period.</cite> Track and intensity are not two instances of one problem. Appendix B treats them symmetrically — same table, same structure of target and threshold — and the literature says they are not symmetric at all.

**Second, and this is the one that reaches into the code.** Using a perfect-model framework, they find that (cite index="135-1">error growth over approximately the first few days is dominated by errors in initial intensity, after which errors in forecasting the track and large-scale environment take over.</cite>

That is a direct statement about the [working-track noise emulator](Train-Serve-Consistency). `emulate_working_fix()` perturbs initial intensity, and the defaults ship at 5 kt when [Torn & Snyder](References) suggests 10–12 kt. If initial-intensity error dominates intensity error growth for the first few days, then:

- the emulator is not a fidelity nicety, it is **modelling the dominant error source** at the leads the promotion gates score;
- getting its magnitude wrong by a factor of two propagates straight into whether Stage B learns realistic intensity behaviour;
- recalibration moves from "worth doing" to **prerequisite**.

A follow-up sharpens it further: **Emanuel, K., and F. Zhang, 2017:** The role of inner-core moisture in tropical cyclone predictability and practical forecast skill. *J. Atmos. Sci.*, **74**(7), 2315–2324. [doi:10.1175/JAS-D-17-0008.1](https://doi.org/10.1175/JAS-D-17-0008.1) — intensity error growth is (cite index="138-1">at least as sensitive to the specification of inner-core moisture as to that of the wind field</cite>. Neither the feature set nor the emulator represents inner-core moisture at all. That is a gap worth naming rather than discovering later.

**DeMaria, M., C. R. Sampson, J. A. Knaff, and K. D. Musgrave, 2014:** Is tropical cyclone intensity guidance improving? *Bulletin of the American Meteorological Society*, **95**(3), 387–398.
[doi:10.1175/BAMS-D-12-00240.1](https://doi.org/10.1175/BAMS-D-12-00240.1)

**[claim]** The quantitative companion to the above, and the standard citation for the track/intensity asymmetry. Also the reference for why statistical-dynamical models like SHIPS remained competitive long after dynamical models had won on track — relevant to any argument that the LSTM baseline is merely a warm-start.

**Gall, R., J. Franklin, F. Marks, E. N. Rappaport, and F. Toepfer, 2013:** The Hurricane Forecast Improvement Project. *Bulletin of the American Meteorological Society*, **94**(3), 329–343.
[doi:10.1175/BAMS-D-12-00071.1](https://doi.org/10.1175/BAMS-D-12-00071.1)

**[precedent]** The HFIP program paper — the actual "HFIP overview" citation, distinct from DeMaria (2014), which is the guidance-assessment paper. HFIP set the error-reduction goals against which any new forecast system is implicitly measured, and its structure (a defined baseline, staged reduction targets, a stream for operational transition) is a reasonable template for how Anemoi-Core should present its own claims.

Also useful: **DeMaria, M., J. L. Franklin, M. J. Onderlinde, and J. Kaplan, 2021:** Operational forecasting of tropical cyclone rapid intensification at the National Hurricane Center. *Atmosphere*, **12**(6), 683. [doi:10.3390/atmos12060683](https://doi.org/10.3390/atmos12060683) — the RI-specific verification record, and the right yardstick for the RI flag rather than a raw hit rate.

---

## 8. Physics-informed networks

**Raissi, M., P. Perdikaris, and G. E. Karniadakis, 2019:** Physics-informed neural networks: A deep learning framework for solving forward and inverse problems involving nonlinear partial differential equations. *Journal of Computational Physics*, **378**, 686–707.
[doi:10.1016/j.jcp.2018.10.045](https://doi.org/10.1016/j.jcp.2018.10.045)

**[implemented]** The canonical PINN reference, and the one that settles the §3.6 correction recorded in the [Decision Log](Decision-Log): governing equations enter through the **loss**, not the forward pass. v2's §3.6 listed them under "Input".

**Karniadakis, G. E., and Coauthors, 2021:** Physics-informed machine learning. *Nature Reviews Physics*, **3**(6), 422–440.
[doi:10.1038/s42254-021-00314-5](https://doi.org/10.1038/s42254-021-00314-5)

---

## 9. Baselines and targets

**NHC Forecast Verification:** [verification homepage](https://www.nhc.noaa.gov/verification/) · [error database](https://www.nhc.noaa.gov/verification/verify7.shtml) · [GPRA history](https://www.nhc.noaa.gov/verification/pdfs/GPRA_history.pdf) · [2024 report](https://www.nhc.noaa.gov/verification/pdfs/Verification_2024.pdf) · [2025 preview](https://www.nhc.noaa.gov/pdf/NHC_Verification_Report_2025_Preview.pdf)

**[claim — and the numbers are worse for us than the scope admits]**

Scope Appendix B sets a 48 h track target of `< 75 nm` with a production threshold of `< 90 nm`, and notes that recent NHC performance "suggests the v2 absolute targets may trail the consensus baseline." That note understates it.

| Season | NHC official 48 h Atlantic track error |
|---|---|
| 2023 | 69 n mi (a difficult year) |
| 2024 | **45.4 n mi** — a record; <cite index="104-1">mean track errors at every forecast interval broke accuracy records</cite> |
| 2025 | **53.4 n mi** — <cite index="106-1">below the 2020–2024 means at every lead time</cite> |

NOAA's own GPRA target for 2026 is 51.0 n mi. So the operating baseline is roughly **45–55 nm at 48 h**, not the 55–65 the wiki previously stated, and not remotely close to 90.

**A system whose *production threshold* is 90 nm would be admitted to production while being twice as bad as the incumbent.** The beat-rate gate is the only thing preventing that, which is precisely why it is the primary criterion. The absolute thresholds should be re-derived from the verification database rather than adjusted by intuition. See [Verification Metrics](Verification-Metrics).

Two useful notes from the 2025 report for anyone building the backtest:

- <cite index="106-1">Atlantic 24–72 h track errors have fallen roughly 75% over about twenty years, with 60–70% reductions at 96–120 h</cite>. Any historical backtest spanning decades is scored against a **moving** baseline; a fixed threshold is meaningless across that span.
- <cite index="106-1">The report uses CLIPER5, a climatology-and-persistence model, to estimate baseline difficulty, and interprets 2025's larger intensity errors as evidence that the season was substantially harder to forecast than normal</cite>. A difficulty-normalised baseline belongs in the verification layer alongside raw error — a good year and an easy year are not the same thing, and the beat rate alone will not distinguish them.

**Cangialosi, J. P., and Coauthors, 2020:** Recent progress in tropical cyclone intensity forecasting at the National Hurricane Center. *Weather and Forecasting*, **35**(5), 1913–1922. [doi:10.1175/WAF-D-20-0059.1](https://doi.org/10.1175/WAF-D-20-0059.1)

---

## Unverified

**"Zhang et al. (2025) — AI-based hurricane intensity prediction with coupled ocean feedback"**

**Could not be located as cited.** Searching for this title, and for the topic, returns no matching paper. It may be a garbled or hallucinated citation; if it came from an LLM-generated reading list, that is the likely explanation. Do not cite it until a DOI is in hand.

Three real 2025 papers sit near that description, and the intended one is probably among them:

- **Zhang, G., M. Rao, J. Yuval, and M. Zhao, 2025:** Advancing seasonal prediction of tropical cyclone activity with a hybrid AI-physics climate model. *Environmental Research Letters*, **20**(9), 094031. [doi:10.1088/1748-9326/adf864](https://doi.org/10.1088/1748-9326/adf864) — matches the author and year, but it is NeuralGCM applied to *seasonal TC activity*, not intensity forecasting with ocean coupling.
- **Lai, and Coauthors, 2025:** Towards skillful tropical cyclone forecasting by AI-model-driven high-resolution regional coupled model. *Meteorological Applications*. [doi:10.1002/met.70109](https://doi.org/10.1002/met.70109) — matches the *description* closely: Pangu-Weather and AIFS driving the atmosphere–ocean–wave coupled UWIN-CM, with (cite index="113-1">a 34% reduction in track error and 20% reduction in intensity error compared with the IFS-driven configuration</cite>.
- **FuXi-TC, 2025:** [arXiv:2508.16168](https://arxiv.org/abs/2508.16168) — a diffusion framework for TC forecasts on a coupled ocean–atmosphere base model, where (cite index="154-1">explicit modeling of ocean feedback processes such as sea surface heat fluxes improves the representation of air–sea interactions</cite>. Architecturally the closest published analogue to Anemoi-Core+Anemoi-Spread as a whole.

Whichever was meant, the theme is worth taking seriously: **the implementation currently treats SST and OHC as static daily inputs persisted from the previous day.** A storm's own cold wake is a first-order intensity feedback and it is not represented anywhere in the feature set. See [Roadmap](Roadmap).

---

## What to do with this

Three of these are not just citations — they change something.

1. **Torn & Snyder (2012)** says the working-track noise defaults are optimistic and that the error is intensity-dependent. Recalibrating against it, or against a real archive, comes before Stage B is meaningful.
2. **GenCast's operational fine-tuning** is independent confirmation of §4.6 and should be cited in it. It also means the ERA5→operational two-stage pattern has a public reference implementation to compare against.
3. **NHC's 2024–25 verification numbers** make Appendix B's absolute thresholds untenable as written. They need re-deriving, not adjusting.

The 2026 experimental **elliptical cone** is a fourth, lower-priority item: it fits the cross/along-track decomposition already in the codebase.

Three more, from the second round:

4. **Emanuel & Zhang (2016)** promotes emulator recalibration from "worth doing" to prerequisite, because initial-intensity error is the dominant intensity error source at exactly the leads the promotion gates score. Their 2017 follow-up adds that inner-core moisture matters as much as the wind field — and nothing in the feature set represents it.
5. **Song et al. (2023)** offers a better answer than load shedding to a binding diffusion budget: distil to a consistency model and get graded quality-vs-time instead of a binary member drop.
6. **Ocean feedback** — whatever the intended Zhang citation was — points at a real omission. SST and OHC are persisted daily inputs; the storm's own cold wake is not modelled.

---

Related: [Verification Metrics](Verification-Metrics) · [Train/Serve Consistency](Train-Serve-Consistency) · [Decision Log](Decision-Log) · [Roadmap](Roadmap)
