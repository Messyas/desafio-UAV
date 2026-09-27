# Protocol and feature sensitivity in a simulated UAV intrusion benchmark

**Working draft, 27 September 2026.** This is a manuscript base, not a submission-ready article. Every result below refers to the UAVIDS-2025 v1 CSV and the exploratory v4/v5/v6 analyses. It must be checked again after clean reproduction and expert review of the uncertainty analysis. No journal has been selected.

## Abstract

Performance estimates for flow-based intrusion classification can change with the way a benchmark is divided and with seemingly informative derived features. We audited the 122,171-flow UAVIDS-2025 dataset for a closed-set five-class task, excluding flow identifiers and network addresses from the predictor panel. We compared a stratified random split (S0), disjoint exact numeric signatures (S1), and disjoint source addresses (S2) using Random Forest and XGBoost. In the base 18-feature condition, out-of-fold macro F1 for XGBoost changed from 0.956326 in S0 to 0.952666 in S2. Four paired derived-feature conditions showed no general improvement; in S2, all eight conditional intervals for their differences from the base panel included zero. A proposed loss ratio was nearly identical to the supplied packet-drop rate, while throughput per hop was undefined for 38,501 rows and required train-fold imputation. The results show protocol sensitivity and limits of these feature transformations within a single simulated CSV. They do not establish performance on independent simulations, live detection, unknown attacks, or deployed UAV hardware.

## 1. Introduction

The [UAVIDS-2025 record](https://zenodo.org/records/15336998) makes a simulated flow-level intrusion dataset publicly accessible. A high score on a random split of such a dataset can be useful for benchmarking, but the test population must be described precisely. Different flows can share identifiers, addresses and even exact predictor vectors. Flow-level metrics also leave open whether the features are available at the time a defender must decide.

The [original dataset paper](https://www.researchgate.net/publication/396599699_UAVIDS-2025_A_Benchmark_Dataset_for_Intrusion_Detection_in_UAV_Networks_Using_Machine_Learning_Techniques) benchmarked several classifiers with a stratified 80/20 division. Subsequent work examined Blackhole/Wormhole confusion under stratified evaluation ([Zarkadis and Douligeris, 2026](https://arxiv.org/html/2605.13922)). Source-disjoint evaluation, identifier controls, and source-rate features have also been studied for a distinct zero-day Sybil task ([Demir and Gumus, 2026](https://www.mdpi.com/2079-9292/15/17/3966)). Thus neither a high RF/XGBoost score nor the mere act of withholding source identities is novel. Our narrower question is how the reported closed-set five-class result changes under three explicit split populations and whether three proposed flow ratios add useful signal to the same training pipeline. We report negative feature results and errors by class rather than select the best single condition.

## 2. Data and methods

The canonical CSV is UAVIDS-2025 Zenodo v1, DOI 10.5281/zenodo.15336998, SHA-256 `d50d339f68be7b23f0bf089dd438b20a1835c13182d8641220538121440164d0`. It has 122,171 rows, 23 columns and five labels: Normal Traffic, Blackhole Attack, Flooding Attack, Sybil Attack and Wormhole Attack. `FlowID`, `SrcAddr`, `DstAddr` and constant `Protocol` are excluded from the base predictor panel. The 18 retained attributes are enumerated in `configs/feature_ablation_v4.json`; source addresses and exact numeric signatures are used only to construct and diagnose partitions.

S0 uses stratified random folds, S1 withholds exact 18-feature signatures, and S2 withholds source-address strings. All use five folds. S1 does not identify simulation sessions; S2 does not identify physical aircraft or fresh simulator executions. In particular, destinations and some signatures can overlap between S2 training and test. All five classes are represented in each fitted and evaluated fold. The folds were already known when the revised feature question was posed, so all inferential language is exploratory.

We fit Random Forest and XGBoost with the fixed parameters in `configs/feature_ablation_v4.json`, four threads and seed 20260907. The base condition A0 uses the 18 original predictors. A1 adds `LostPackets/TxPackets`, A2 adds `RxBytes/TxBytes`, A3 adds `Throughput/Kbps/AverageHopCount`, and A4 adds all three. Invalid ratios are represented as missing and imputed from training-fold statistics within the pipeline. No identifiers enter the main models. A second complete S2 grid repeats both models and all five conditions with three seeds; a separate sensitivity analysis clips `PacketDropRate` to [0,1]. Predictions and model configurations are saved per fold with checksums.

The primary measure is out-of-fold macro F1 over the five original labels. We also report class precision/recall/F1, confusion counts, attack-to-normal misses, and normal-to-attack false alarms. Paired intervals resample groups over fixed out-of-fold predictions: source addresses in S0/S2 and exact numeric signatures in S1. They do not include model-training uncertainty, new runs or new scenarios; multiple exploratory comparisons are unadjusted. Exact split rules, preprocessing, parameters, seeds and interval implementation are in `protocol/feature_ablation_v4.md` and the archived analysis manifests.

## 3. Results

| Split | RF A0 macro F1 | XGBoost A0 macro F1 |
|---|---:|---:|
| S0: stratified random | 0.955051 | 0.956326 |
| S1: disjoint exact signatures | 0.953986 | 0.954612 |
| S2: disjoint source addresses | 0.950677 | 0.952666 |

Source: `reports/feature_ablation_v4/pooled_metrics.csv`, seed 20260907, out-of-fold aggregation. The decrease from S0 to S2 describes sensitivity to this test population and training regime; it does not isolate address leakage as its sole cause.

For S2, none of the eight A1–A4 comparisons against A0 across the two models had a conditional interval excluding zero (`paired_comparisons.csv`). In the whole v4 grid, two of 24 unadjusted intervals were below zero, both in RF/S1; selective emphasis on those would overstate evidence. The three-seed S2 repetition yielded an average RF/A3 minus RF/A0 macro-F1 difference of 0.000509, about 0.051 percentage point, and an XGBoost/A3 average of 0.000060; the latter changed sign across seeds (`seed_variation.csv`). No predeclared operational relevance margin exists, and these observations do not support a general feature-gain claim.

The descriptive audit found `loss_ratio` close to `PacketDropRate` in 122,148/122,171 rows at the documented tolerance. `throughput_per_hop` was undefined in 38,501 rows because its denominator was not positive. Any A3 effect may therefore reflect imputation patterns as well as ratio values. The 81 `PacketDropRate` values above one were retained in the primary analysis. Clipping them in v6 changed S2 macro F1 by +0.000434 for RF and +0.000027 for XGBoost, with both conditional intervals including zero. These observations do not establish that the simulator output is erroneous.

S2/A0 XGBoost achieved Blackhole recall 0.861241, Blackhole F1 0.906405 and Wormhole F1 0.901753. Across its out-of-fold predictions, 281 attack flows were labeled normal and 231 normal flows were labeled as attacks (`confusion_counts.csv`). These errors matter even when aggregate macro F1 is high; their operational costs are not estimated by this dataset.

## 4. Discussion and limitations

This study makes a bounded methodological contribution: a reproducible within-benchmark comparison of three split populations and paired feature conditions for the original closed-set task, including negative results. It does not establish a superior architecture. Flow identifiers carry a strong artifact in this CSV and must not be used to claim realistic detection; the main panel excludes them. The observed S0/S1/S2 differences mix changes in training population and shared structure, so they are not a causal estimate of leakage by any one field.

The available CSV lacks explicit timestamps, simulation-run IDs, scenario IDs and collection code. The timing and exact simulator formulas of several flow attributes remain unverified (`protocol/feature_semantics_audit.csv`). Until a collection process and decision time are specified, the task should be described as classification of completed flow vectors, not online or onboard intrusion detection. The current S2 test is within a single simulated benchmark. Different seeds of the same CSV cannot replace an independent scenario, and none of these models was tested on unknown attack classes. The bootstrap is conditional on fixed predictions and is not a confidence interval for new simulation campaigns.

## 5. Conclusion

Within UAVIDS-2025 v1, the evaluated closed-set classifiers are sensitive to how folds are constructed, while the proposed derived ratios did not yield a convincing general improvement. A journal-level claim of transfer to other UAV networks would require independently identified simulations or another semantically compatible dataset, with the evaluation protocol fixed before examining it. The present evidence supports a critical benchmark study only if peer review judges the explicit split and negative-feature analysis to add enough beyond the recent literature.

## Availability and disclosure to complete

The [dataset record](https://zenodo.org/records/15336998) provides the CSV; its [record API](https://zenodo.org/api/records/15336998) identifies the license as CC BY 4.0. Code, frozen configurations, hashes and local bundles are in the repository; a public archive DOI and checks of third-party materials are still pending. No public upload or journal submission is implied by this draft. AI assistance and human verification must be disclosed according to the selected journal's current policy; see `provenance/ai_assistance.md`.
