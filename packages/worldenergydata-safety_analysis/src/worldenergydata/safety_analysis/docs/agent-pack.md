# Safety analysis module knowledge pack

| Header | Value |
| --- | --- |
| Module | safety_analysis |
| Repository | worldenergydata |
| Path | `packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis` |
| Pack revision | 0 |
| Code revision | `55991b0def0f90708b3e0c396c0f57d9d1b7f7fb` |
| Analysis family | Data pipeline; AQG r0 §10 Python calculations |
| QA family | EC |
| Quality manager role | Calculations quality manager; provisional data pipeline coverage |
| Status | DRAFT |

## 1. Purpose and scope

The Python API loads tabular observation and incident records, maps source columns into typed records, classifies descriptions, aggregates severity and counts, and computes observation–incident lag correlations. [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/data/loaders.py:L16-L80] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/data/processors.py:L26-L70] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/data/processors.py:L126-L179] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/nlp/classification_pipeline.py:L232-L310] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/analysis/correlation.py:L52-L95]
Risk scoring has two separate routes: activity-level acute/chronic/compliance scores and a scenario-matrix route with an optional incident-frequency calibrator; these return different score scales. [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/risk_index/scorer.py:L134-L231] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/skill.py:L199-L218] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/calibrator.py:L378-L417]
The package also contains a source-code/keyword taxonomy, HTML reports and a bounded earthquake-observation client; earthquake retrieval does not establish offshore location or compute hazard or risk. [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/taxonomy/incident_classifier.py:L104-L136] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/reports/incident_report.py:L38-L96] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/geohazard/README.md:L3-L7]
The main entry-point CLI `classify` and `correlate` commands currently write summaries without calling the corresponding computation; a successful CLI exit is insufficient evidence of an analysis result (F1). [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/cli.py:L167-L190] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/cli.py:L238-L261]
The package metadata declares Alpha maturity and optional ML/BERT extras; no routing maturity is inferred from the inventory description. [packages/worldenergydata-safety_analysis/pyproject.toml:L15-L23] [packages/worldenergydata-safety_analysis/pyproject.toml:L49-L62]
UNVERIFIED: an independent basis for the scenario scores, source reliability weights, classification confidence constants and engineering applicability envelope remains unqualified; C1.

## 2. Inputs and outputs

### Inputs

| Name | Unit / allowed range | Default / source | Evidence |
| --- | --- | --- | --- |
| Tabular files | CSV, XLSX/XLS, Parquet/PQ; source units retained by pandas readers | Required path; first Excel sheet unless supplied | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/data/loaders.py:L19-L62] |
| `SchemaMapping` | Column names and string mappings; required name, asset, time and description column names | `source_type="observation"`; optional date format and extraction regex | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/core/schemas.py:L19-L84] |
| Observation record | `asset_id` string, `observed_at` datetime, nonblank `description`; enum observation type | Type UNKNOWN; optional action/observer and empty metadata | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/core/models.py:L20-L39] |
| Incident record | `occurred_at` datetime; severity enum; optional text/activity | Type OTHER; actual and potential severity NO_HURT | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/core/models.py:L42-L62] |
| Analysis settings | Frequencies are pandas offsets; windows and lags in bins | Default daily; window 10, step 1; lag −30 to 30, minimum observations 30 | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/config.py:L40-L70] |
| Time-series builder | Caller-supplied event timestamps and asset IDs; counts per bin | Builder frequency W-SUN, distinct from analysis default D | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/analysis/time_series.py:L21-L29] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/analysis/time_series.py:L82-L123] |
| NLP settings | Token lengths in characters; sample fractions dimensionless; no bounds declared on these configuration fields | Token lengths 2–50, lowercase, unigram; 5 folds, 50 evaluations, test fraction 0.2 | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/config.py:L18-L37] |
| Risk assembler | DataFrames keyed by `bsee`, `osha`, `marine_safety`, `phmsa`, `epa_tri`; fatalities/injuries are counts, release column is treated as lb | Invalid source rejected; empty source omitted | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/risk_index/data_assembler.py:L35-L51] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/risk_index/data_assembler.py:L102-L122] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/risk_index/data_assembler.py:L237-L265] |
| Risk parameters | Weights dimensionless; missing metric score in score points; depth thresholds in ft | Composite weights 0.50/0.25/0.25; acute 0.40/0.35/0.25; missing score 5.5; depth thresholds 500/5000 ft | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/risk_index/config_loader.py:L19-L53] |
| Scenario assessment | Enumerated `asset_type`, `scenario`; optional `risk_score_override` clamped to [0,1] | Static matrix unless override or fitted calibrator supplied | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/skill.py:L19-L59] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/skill.py:L268-L296] |
| Earthquake query | Aware start/end, start < end; latitude ±90°, box longitude ±360° or radius longitude ±180°; radius 0–20001.6 km; limit 1–20000 events | Caller supplies selection; timeout 30 s, maximum 60 s; response cap 5000000 bytes | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/geohazard/usgs.py:L148-L156] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/geohazard/usgs.py:L219-L231] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/geohazard/usgs.py:L255-L308] |

### Outputs

| Name | Unit / representation / defaults | Evidence |
| --- | --- | --- |
| Standardized tables and records | Datetime, categorical strings, source descriptions, asset IDs; optional metadata | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/data/processors.py:L41-L70] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/data/processors.py:L141-L179] |
| `ClassificationResult` | Label, model name, feature type and confidence in [0,1]; optional class probabilities | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/core/models.py:L65-L77] |
| Taxonomy result | Activity/subactivity codes, method, source and heuristic confidence; separate type from the NLP result | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/taxonomy/incident_classifier.py:L46-L80] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/taxonomy/incident_classifier.py:L104-L136] |
| Lag correlation | Dimensionless signed Pearson coefficient; peak chosen by absolute coefficient; lag in input bins | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/analysis/correlation.py:L17-L36] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/analysis/correlation.py:L78-L95] |
| Hurt index | Sum of mapped ordinal severity points, per group or time bin; unknown labels contribute 0 | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/analysis/incident_aggregation.py:L94-L125] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/analysis/incident_aggregation.py:L142-L171] |
| Activity risk | Dimension and composite scores 1–10 score points; category, incident count, confidence label, source IDs | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/risk_index/models.py:L30-L41] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/risk_index/models.py:L54-L95] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/risk_index/scorer.py:L237-L285] |
| Scenario risk | Score 0–1, categorical risk, fixed fault-chain and recommendation strings | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/skill.py:L176-L218] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/skill.py:L285-L296] |
| Reports | UTF-8 HTML with Plotly JSON and a CDN script dependency; summary counts and severity trends retain their input meaning | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/reports/base_report.py:L75-L119] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/reports/base_report.py:L173-L185] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/reports/incident_report.py:L57-L94] |
| Earthquake rows / manifest | UTC time, latitude/longitude in degrees, depth km, magnitude, nullable unknowns; manifest SHA-256 and byte count from exact payload bytes | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/geohazard/usgs.py:L48-L76] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/geohazard/usgs.py:L103-L122] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/geohazard/usgs.py:L311-L345] |

Observation/incident processors call pandas datetime parsing without forcing UTC; earthquake timestamps explicitly use UTC, and lag shifts move the second series by positive `lag` periods. [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/data/processors.py:L88-L95] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/data/processors.py:L199-L203] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/geohazard/usgs.py:L110-L115] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/analysis/correlation.py:L17-L36]
UNVERIFIED: a shared geodetic datum, vertical origin, phase convention, source timestamp zone and source-unit qualification have not been established across all inputs; C1.

## 3. Method and governing standards

| Method | Implementation, equation / criterion and limit | Evidence |
| --- | --- | --- |
| Schema processing | Required-column check, regex asset extraction, pandas datetime conversion and configurable category lookup; unknown severity falls back to NO_HURT | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/core/schemas.py:L77-L84] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/data/processors.py:L72-L84] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/data/processors.py:L194-L251] |
| Text classification | Whitespace cleaning and stop-word/length filtering; sklearn TF-IDF followed by random forest, logistic regression or optional XGBoost; stratified train/test split and weighted F1 | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/nlp/text_preprocessing.py:L96-L132] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/nlp/tfidf_vectorizer.py:L54-L105] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/nlp/classification_pipeline.py:L114-L130] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/nlp/classification_pipeline.py:L253-L298] |
| Hyperparameter search | Hyperopt search if available; otherwise random search capped at 20 trials; failed trials are caught and training can fall back to empty parameters | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/nlp/classification_pipeline.py:L150-L230] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/nlp/classification_pipeline.py:L272-L284] |
| BERT alternative | Pretrained tokenizer/model, CLS or masked-mean embeddings; sklearn classifier and persisted encoder; constructor can request model resources | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/nlp/bert_pipeline.py:L117-L193] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/nlp/bert_pipeline.py:L249-L330] |
| Binning and smoothing | Per-asset resampling and zero-fill; active-asset normalization divides total by active count, using 0 if none; first differences and rolling means | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/analysis/time_series.py:L95-L123] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/analysis/time_series.py:L153-L168] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/analysis/time_series.py:L184-L224] |
| Cross-correlation | `crosscorr(x,y,lag) = x.corr(y.shift(lag))`; search inclusive lag range; NaN becomes 0; peak retains sign | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/analysis/correlation.py:L17-L36] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/analysis/correlation.py:L72-L95] |
| Hurt aggregation | `compute_hurt_index`: sum of ordinal severity values per group; these are code conventions, not injury probabilities | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/constants.py:L27-L34] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/analysis/incident_aggregation.py:L94-L125] |
| Features | 18 statistical and 14 FFT feature columns; FFT drops the DC entry, energy divides sum of squares by configured window size | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/analysis/feature_engineering.py:L34-L70] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/analysis/feature_engineering.py:L128-L191] |
| Statistical inference | SciPy Welch/pooled t-test, one-way ANOVA, contingency chi-square, Pearson/Spearman and linear regression; implementation computes effect size and adjusted R² | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/analysis/statistical_tests.py:L15-L46] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/analysis/statistical_tests.py:L49-L142] |
| Seasonal decomposition | Optional statsmodels decomposition, additive by default; iterative residual extraction for supplied periods | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/analysis/decomposition.py:L16-L26] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/analysis/decomposition.py:L29-L85] |
| Activity taxonomy | Source-specific dispatch then code/keyword rules; keyword ties retain earlier activity order; unmatched subactivity uses first entry; default OTHER has confidence 0.10 | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/taxonomy/incident_classifier.py:L122-L136] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/taxonomy/incident_classifier.py:L361-L484] |
| Activity metric assembly | Rates are fatalities or injuries divided by incident rows, not worker exposure; source-weighted count is separate; `inc_rate` is initialized to 0 and must be populated externally | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/risk_index/data_assembler.py:L288-L350] |
| Risk normalization | Average tied ranks divided by valid sample count; score = clip(round(percentile × (high−low) + low−0.5), low, high); NaNs retained until scorer fills them | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/risk_index/normalizer.py:L44-L60] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/risk_index/normalizer.py:L77-L111] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/risk_index/scorer.py:L120-L128] |
| Composite index | Normalize five metrics, compute weighted acute score, take normalized release and non-compliance scores, then weighted composite; clamp scores to [1,10] | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/risk_index/scorer.py:L90-L118] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/risk_index/scorer.py:L134-L231] |
| Scenario matrix / calibration | Base × asset modifier clipped to [0,1]; calibration uses severity-weighted annual frequency, normalizes by maximum frequency, blends 0.6 data with 0.4 matrix score for counts ≥10, otherwise retains fallback | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/skill.py:L199-L205] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/calibrator.py:L166-L205] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/calibrator.py:L378-L417] |
| Earthquake ingestion | Count before query, refuse count above limit, preserve typed nulls, cap event/byte counts; manifest hashes exact bytes | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/geohazard/usgs.py:L125-L137] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/geohazard/usgs.py:L219-L253] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/geohazard/usgs.py:L311-L345] |

The source labels the scenario matrix as derived from industry data, but the executable definition is a literal matrix; it is not used here as an independently qualified reference. [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/skill.py:L13-L59]
UNVERIFIED: publication/edition/clauses and calculation-citation sidecars for the taxonomy and heuristic scoring basis remain unqualified; C1 and #361.

## 4. Validated worked examples

Validation scope: two elementary algebraic checks, with three regression examples; these do not qualify engineering risk predictions. [tests/unit/safety_analysis/test_statistical_tests.py:L59-L80] [tests/unit/safety_analysis/test_incident_aggregation.py:L64-L71] [tests/unit/safety_analysis/test_feature_engineering.py:L75-L82] [tests/unit/safety_analysis/geohazard/test_usgs.py:L216-L222]

| Case / class | Independent source or regression input | Expected result, unit and tolerance basis | Existing test node ID | Offline record |
| --- | --- | --- | --- | --- |
| VAL-1 validated: Pearson identity | Closed form: y=2x for x=[1,2,3,4,5]; centered sums Sxx=10, Syy=40, Sxy=20 give r=Sxy/√(Sxx×Syy)=1 | r=1.0 dimensionless, absolute error <1e-10; tolerance is the existing test assertion | `tests/unit/safety_analysis/test_statistical_tests.py::TestCorrelations::test_pearson_perfect` | PASS at BASE and after. [tests/unit/safety_analysis/test_statistical_tests.py:L59-L64] |
| VAL-2 validated: affine fit | Closed form on the same literal points: slope=Sxy/Sxx=2; intercept=mean(y)−2mean(x)=0; R²=1 | Slope 2.0 output-units/input-unit; intercept 0.0 output-units; R² 1.0 dimensionless; each absolute error <1e-10 | `tests/unit/safety_analysis/test_statistical_tests.py::TestLinearRegression::test_perfect_linear` | PASS at BASE and after. [tests/unit/safety_analysis/test_statistical_tests.py:L73-L80] |
| REG-1 regression: hurt sum | Synthetic severity fixture; ordinal mapping is the module convention | Sum 0+2+3=5.0 severity points, exact equality; this does not independently validate severity weights | `tests/unit/safety_analysis/test_incident_aggregation.py::TestAggregation::test_compute_hurt_index` | PASS at BASE and after. [tests/unit/safety_analysis/test_incident_aggregation.py:L15-L44] [tests/unit/safety_analysis/test_incident_aggregation.py:L64-L71] |
| REG-2 regression: feature schema | Seeded count windows, window size 10 bins and step 5 bins; expected schema derived from module lists | 32 feature columns, exact integer equality; no accuracy claim for individual features | `tests/unit/safety_analysis/test_feature_engineering.py::TestFeatureEngineer::test_compute_all_features` | PASS at BASE and after. [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/analysis/feature_engineering.py:L34-L70] [tests/unit/safety_analysis/test_feature_engineering.py:L75-L82] |
| REG-3 regression: provenance bytes | Existing geohazard payload and provenance fixtures; module-generated manifest is a regression reference | 0 differing bytes against committed manifest, exact equality | `tests/unit/safety_analysis/geohazard/test_usgs.py::test_manifest_reproduction` | PASS at BASE and after. [tests/unit/safety_analysis/geohazard/test_usgs.py:L216-L222] |

Offline audit record: ordinary `uv run python -m pytest tests/unit/safety_analysis -q -rA -p no:cacheprovider`, with scratch basetemp, JUnit XML and coverage destinations, plus `--allow-existing-tree-changes`; configured addopts retained, no `--no-sources`, no addopts override; code pin is the header revision.
BASE and after collection: 635 cases each, 618 executed/passed, 0 failed, 17 skipped, 0 NOT_RUN; 0 node-status differences; the independent centered-sum calculation was also executed outside the module's formulas.
UNVERIFIED: independent source-labelled risk/taxonomy benchmarks and optional-backend qualification remain outstanding; C1 and C2.

## 5. QA gates

Gate selection is the Python calculations row of AQG r0 §10, with G5 required under §9; the following are executable review criteria, rather than declarations of engineering clearance. (AQG r0, §§9–11.)

| Gate | Applicability / reason | Defined checks |
| --- | --- | --- |
| G0 | Applicable: tabular schemas, score bounds, query ranges | IN-1, IN-2, IN-3 |
| G1 | Applicable: Python imports and offline tests; target route is the installed workspace Python API and pytest, not a model loader | LOAD-1, LOAD-2 |
| G2 | Applicable: independent algebraic calculation on literal statistical inputs | REF-1, REF-2 |
| G3 | NOT_APPLICABLE: this gate set does not require short dynamics for Python calculations | AQG r0 §10 |
| G4 | NOT_APPLICABLE: this gate set does not require diffraction QA for Python calculations | AQG r0 §10 |
| G5 | Applicable: reproducible evidence and exact provenance records | EVID-1, EVID-2 |

| ID | Module-specific execution | Numeric pass criterion and unit | Evidence / gate |
| --- | --- | --- | --- |
| IN-1 | `ObservationProcessor.process` with only `wrong_col`; run `tests/unit/safety_analysis/test_processors.py::TestObservationProcessor::test_missing_required_column` | 0 invalid input tables accepted; `SafetyDataError` required | Offline test result; G0. [tests/unit/safety_analysis/test_processors.py:L34-L40] |
| IN-2 | `ClassificationResult(confidence=1.5)`; run `tests/unit/safety_analysis/test_models.py::TestClassificationResult::test_confidence_bounds` | 0 out-of-range probability records accepted | Offline test result; G0. [tests/unit/safety_analysis/test_models.py:L98-L105] |
| IN-3 | `USGSClient` limit guard; run the four parametrizations of `tests/unit/safety_analysis/geohazard/test_usgs.py::test_invalid_limit_never_fetches` | 0 requests for limits 0, 20001, True or 1.5 events | Offline test results; G0. [tests/unit/safety_analysis/geohazard/test_usgs.py:L122-L125] |
| LOAD-1 | Parse every pinned package `.py` using `ast.parse`; module imports are also exercised by the suite | 56 of 56 files parse; 0 syntax errors (files) | Source inventory and parse audit; G1. [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/core/schemas.py:L19-L84] [tests/unit/safety_analysis/test_processors.py:L34-L40] |
| LOAD-2 | Execute the complete `tests/unit/safety_analysis` tree in the section-4 form | 635 collected cases, 0 failed tests; record every skip reason and require unchanged BASE/after node statuses | JUnit comparison and offline logs; G1. [tests/unit/safety_analysis/test_cli.py:L42-L97] [tests/unit/safety_analysis/test_bert_pipeline.py:L14-L31] |
| REF-1 | `pearson_correlation` for VAL-1; independently sum centered products and compare r | Absolute error <1e-10 dimensionless against r=1.0 | VAL-1 test plus arithmetic record; G2. [tests/unit/safety_analysis/test_statistical_tests.py:L59-L64] |
| REF-2 | `linear_regression_summary` for VAL-2; independently divide centered sums and evaluate intercept | Errors <1e-10 in slope ratio, intercept output-units and dimensionless R² against 2.0, 0.0, 1.0 | VAL-2 test plus arithmetic record; G2. [tests/unit/safety_analysis/test_statistical_tests.py:L73-L80] |
| EVID-1 | `emit_manifest` over existing fixture bytes and supplied metadata; run REG-3 | 0 differing bytes against stored manifest | Exact manifest reproduction test; G5. [tests/unit/safety_analysis/geohazard/test_usgs.py:L216-L222] |
| EVID-2 | Join all five section-4 node IDs to baseline and after JUnit records; record pin, command, input SHA-256 list and aggregate fingerprint | 5 of 5 cases traced; 0 missing result records (cases) | Evidence reconciliation; G5. [tests/unit/safety_analysis/test_statistical_tests.py:L59-L80] [tests/unit/safety_analysis/test_incident_aggregation.py:L64-L71] [tests/unit/safety_analysis/test_feature_engineering.py:L75-L82] [tests/unit/safety_analysis/geohazard/test_usgs.py:L216-L222] |

UNVERIFIED: a generated, signed AQG appendix covering arbitrary downstream safety reports is not qualified by EVID-1/EVID-2; C1.

## 6. Known failure modes and pitfalls
sweep: not run (legacy pack)

| ID / symptom | Cause and consequence | Detection / existing coverage | Tracking / date |
| --- | --- | --- | --- |
| F1 silent CLI summary success | `classify --train` records `trained=true` without training; `correlate` constructs a correlator without computing results; `load --schema` looks up a registry key using the file-path string | Offline probe: patch `ClassificationPipeline.train`, invoke classify on synthetic CSV, observe exit 0 with 0 train calls; no detection check exists in the current CLI tests beyond help/load behaviour | issue pending (1); 2026-10-15. [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/cli.py:L80-L114] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/cli.py:L167-L190] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/cli.py:L238-L261] [tests/unit/safety_analysis/test_cli.py:L42-L97] |
| F2 calibration provenance/state | Nonempty fit stores fallback records in the matrix; `risk_score` treats matrix membership as data-driven even for fallback records; empty refit does not clear the previous matrix | Synthetic violation-only fit: record flag False but API flag True; refit empty and inspect retained entries; no detection check exists for flag agreement or empty-refit state | issue pending (2); 2026-10-15. [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/calibrator.py:L153-L164] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/calibrator.py:L202-L215] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/calibrator.py:L225-L249] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/calibrator.py:L394-L415] |
| F3 divergent risk interfaces / lost dashboard basis | CLI uses weighted incident counts and rounds dimensions/composite; `RiskScorer` uses total counts and retains fractional scores; dashboard expects `weights`/`method` keys while scorer supplies `composite_weights`/`normalization_method` | Identical synthetic assembled metrics produce different API/CLI scores; render scorer metadata and detect `No weights specified` / unknown method; no detection check exists for parity or scorer-to-dashboard metadata preservation | issue pending (3); 2026-10-15. [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/risk_index/cli.py:L123-L181] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/risk_index/scorer.py:L99-L118] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/risk_index/scorer.py:L219-L231] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/risk_index/scorer.py:L276-L286] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/risk_index/dashboard.py:L332-L370] |
| F4 missing inputs appear as numeric values | Unmapped severity contributes NO_HURT/zero; absent TRI fields become zero; assembled `inc_rate` is zero unless filled externally; NaN score inputs become default 5.5 | IN-1 checks missing required columns only; no detection check exists for rejecting unmapped severity; scorer tests explicitly exercise NaN defaults | #349; 2026-10-15. [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/data/processors.py:L205-L224] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/analysis/incident_aggregation.py:L120-L125] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/risk_index/data_assembler.py:L260-L265] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/risk_index/data_assembler.py:L333-L346] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/risk_index/scorer.py:L120-L128] [tests/unit/safety_analysis/risk_index/test_scorer.py:L386-L424] |
| F5 incomplete feature-window coverage | `create_windows` excludes start index `len(values)−window_size`, including the exactly-one-window case; labels are sliced by position without time alignment | Hand criterion: n=w must yield 1 window; existing test checks only positive count for n=50, w=10; no detection check exists for the final-window boundary | issue pending (8); 2026-10-15. [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/analysis/feature_engineering.py:L100-L118] [tests/unit/safety_analysis/test_feature_engineering.py:L40-L45] |
| F6 evaluation vocabulary leakage | TF-IDF is fit on all texts before holdout split; cross-validation similarly fits vocabulary before creating folds | Read call ordering: fit at line 257 precedes split at 264; CV fit at 396 precedes cross-validation at 399; no detection check exists for fold-isolated vocabulary | issue pending (6); 2026-10-15. [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/nlp/classification_pipeline.py:L253-L270] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/nlp/classification_pipeline.py:L382-L405] |
| F7 undefined correlations become plausible zero | NaN correlations are replaced by zero before peak selection; input sufficiency counts are not paired overlap counts | Inspect constant/disjoint-index input before interpreting zero or peak lag; no detection check exists for preserving undefined status | #349; 2026-10-15. [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/analysis/correlation.py:L72-L95] |
| F8 incomplete source ingestion | PHMSA loader catches spreadsheet errors and continues; invalid configuration can fall back to defaults | Reconcile expected input files and loaded records; no detection check exists requiring complete PHMSA ingestion | #349; 2026-10-15. [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/risk_index/data_assembler.py:L493-L512] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/risk_index/config_loader.py:L82-L113] |
| F9 historical automated-edit syntax damage | The historical issue names unsafe insertion inside multiline imports; imports/syntax must be checked after automated edits, rather than assuming completion from a script exit | LOAD-1 parses all 56 package Python files; LOAD-2 imports the tested API | #275; 2026-10-15. (worldenergydata, issue #275, *fix(scripts): make migrate_print_to_logging.py AST-aware to avoid mid-import injection*, problem statement.) |
| F10 missing qualified citation output | Taxonomy output carries source labels and confidence but no calculation-citation sidecar | Inspect `ClassificationResult.to_dict`; no detection check exists for a resolved standards citation | #361; 2026-10-15. [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/taxonomy/incident_classifier.py:L56-L80] |

The main CLI report route loads data through a loader that rejects JSON extensions despite its argument help naming JSON; correlation/classification report selection redirects to the Python API rather than generating those reports (F1). [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/cli.py:L273-L278] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/cli.py:L301-L325] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/data/loaders.py:L19-L51]
The risk methodology explicitly describes relative rankings and warns that release inventory is a proxy for chronic exposure; the raw fatality/injury ratios therefore must not be presented as exposure-based probabilities. [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/risk_index/methodology.py:L300-L320] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/risk_index/data_assembler.py:L303-L307]
## 7. Lessons log

Append entries after a changed behaviour or newly qualified limitation; use revision-local entry IDs without record identities.

| Date | Entry / pack revision | Lesson | Evidence / change |
| --- | --- | --- | --- |
| 2026-10-15 | L1 / 0 | Treat successful CLI summaries separately from computed analysis | F1 documents missing computation calls. [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/cli.py:L167-L190] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/cli.py:L238-L261] |
| 2026-10-15 | L2 / 0 | Preserve provenance flags across report and score APIs | F2 records fallback/matrix disagreement. [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/calibrator.py:L225-L249] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/calibrator.py:L394-L415] |
| 2026-10-15 | L3 / 0 | Record score algorithm and input cohort with every risk result | F3 records separate CLI/API implementations and metadata-key mismatch. [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/risk_index/cli.py:L123-L181] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/risk_index/scorer.py:L99-L118] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/risk_index/dashboard.py:L332-L370] |

## 8. Ownership

Proposed responsibilities for this DRAFT: calculations quality manager for provisional data-pipeline review; deputy role is a second-provider calculations reviewer, with assignment pending the maintainer; producing role is a module contributor. Clearance requires a reviewer independent of the producer. (AQG r0, §11.)
Escalate tolerance changes, unsupported references and conflicting input evidence to the quality manager; escalate changes outside the module's scope to the maintainer. (AQG r0, §§10–11.)

## 9. Dependencies

### Package and data dependencies

| Direction | Dependency / use | Evidence |
| --- | --- | --- |
| Upstream runtime | worldenergydata-core, NumPy, pandas, SciPy, Plotly, Pydantic/settings, Typer, Rich and PyYAML | [packages/worldenergydata-safety_analysis/pyproject.toml:L35-L47] |
| Optional runtime | sklearn, XGBoost, Hyperopt and joblib in safety-ml; torch, transformers and sentencepiece in safety-bert | [packages/worldenergydata-safety_analysis/pyproject.toml:L49-L62] |
| Input collections | Five accepted incident-source IDs: bsee, osha, marine_safety, phmsa, epa_tri; files or SQLite passed to assembler loaders | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/risk_index/data_assembler.py:L35-L51] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/risk_index/data_assembler.py:L386-L551] |
| Shared services | Common logger, exception hierarchy and data-root resolver | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/exceptions.py:L20-L24] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/config.py:L52-L58] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/adapters/base_adapter.py:L48-L55] |
| Downstream CLI | Root CLI registers the safety-analysis sub-app | [src/worldenergydata/cli/main.py:L145-L149] |
| Script consumer | Exploration script loads taxonomy modules from the package tree | [scripts/exploration/drilling_hse_patterns_analysis.py:L99-L134] |
| Geohazard fixture | Recorded GeoJSON and provenance manifest used by offline parser/reproduction tests | [tests/unit/safety_analysis/geohazard/test_usgs.py:L216-L233] |

Routing audit at the code pin: `docs/registry/module-routing.yaml` is absent; no registry fields are added. Dependency inventory identifiers above are package names and source IDs, rather than invented inventory rows.

### Implementation inventory and counted-family audit

Map source: digitalmodel, *Implementation map*, map commit `b5acbe5f61ed4c755c1f7ea4fafa4611bd14e407` on `codex/implmap-work`, data revision `947fa50ff9a9e210de7e8f90e01b37add85c5954`, `families[].implementations` and `families[].search_signals`.
Audit record: all 13 map families were inspected; 0 have an implementation path inside the header package, so the required inventory contains 0 rows and the counted-family list is empty. The counted-family Python-regex search is `NOT_APPLICABLE` because no map family has in-package rows. No path-vocabulary signal exclusion is needed when no families are counted. This is an empty inventory result, not evidence that this package has no methods. (digitalmodel, *Implementation map*, revisions above, `families[].implementations`.)

### Whole-repository search and map follow-up

A separate Python-source search covered tracked source, packages, examples, tests and scripts for the exact public calculation definitions and backend calls named below; wrappers and tests remain distinct from independent calculations.

| Method family absent from this package's map inventory | In-package definition inventory and additional findings | Evidence |
| --- | --- | --- |
| Schema transformation | `SchemaMapping`, `ObservationProcessor`, `IncidentProcessor`; CSV/HSE adapters delegate to loaders/processors | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/core/schemas.py:L19-L84] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/data/processors.py:L26-L251] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/adapters/csv_adapter.py:L95-L131] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/adapters/hse_adapter.py:L122-L144] |
| TF-IDF / BERT classification and persistence | `ClassificationPipeline`, `BertClassificationPipeline`, `TextPreprocessor`, `SafetyTfidfVectorizer`; registry serializes trained objects | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/nlp/classification_pipeline.py:L99-L130] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/nlp/bert_pipeline.py:L117-L193] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/nlp/bert_pipeline.py:L201-L330] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/nlp/model_registry.py:L98-L143] |
| Rule taxonomy | `IncidentClassifier` computes source/keyword rules; `ActivityTaxonomy` supplies indexes and definitions; deprecated `activity_taxonomy` re-exports these types | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/taxonomy/incident_classifier.py:L199-L484] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/taxonomy/activity_registry.py:L17-L141] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/taxonomy/activity_taxonomy.py:L1-L13] |
| Binning, smoothing, correlation | `TimeSeriesBuilder`, gradient/moving-average functions, `crosscorr`, `LaggedCrossCorrelation`, count/rate helpers | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/analysis/time_series.py:L18-L238] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/analysis/correlation.py:L17-L198] |
| Severity/count aggregation | `aggregate_by_severity`, `aggregate_by_time`, `aggregate_by_group`, `compute_hurt_index`, `compute_time_series_hurt_index`; incident report delegates | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/analysis/incident_aggregation.py:L23-L171] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/reports/incident_report.py:L57-L96] |
| Statistical tests / regression | `ttest_two_groups`, `anova_test`, `chi_square_test`, Pearson/Spearman, linear regression; outside-package SciPy t-test is a map gap, not an in-package miss | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/analysis/statistical_tests.py:L15-L142] [packages/worldenergydata-sodir/src/worldenergydata/sodir/cross_regional.py:L805-L822] |
| FFT/statistical features | `FeatureEngineer` implements statistical and FFT feature calculations and window labels | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/analysis/feature_engineering.py:L100-L199] |
| Seasonal decomposition | `decompose_signal` and iterative residual extraction both delegate to statsmodels | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/analysis/decomposition.py:L29-L85] |
| Relative activity risk and slicing | `percentile_rank`, `normalize_to_scale`, `RiskScorer`, `DataAssembler` metrics, `RiskSlicer`; `risk_index.cli._load_and_score` is a further independent calculation, explicitly inventoried here and F3 | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/risk_index/normalizer.py:L32-L111] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/risk_index/scorer.py:L90-L231] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/risk_index/data_assembler.py:L271-L375] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/risk_index/slicer.py:L45-L100] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/risk_index/cli.py:L123-L181] |
| Scenario risk / calibration | `enigma_safety_analysis` and `_compute_risk_score`; `EnigmaCalibrator` computes its own blended score and a separate fallback formula | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/skill.py:L199-L218] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/skill.py:L268-L296] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/calibrator.py:L378-L447] |
| Bounded geohazard/provenance processing | `USGSClient`, `parse_geojson`, `emit_manifest`; client guards requests, parser creates typed rows, manifest computes digests | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/geohazard/usgs.py:L103-L156] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/geohazard/usgs.py:L181-L253] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/geohazard/usgs.py:L311-L345] |

Map follow-up: inventory every method family above before it is included in a future counted-family audit; issue pending (7). The additional searches do not change the empty-inventory audit result. (digitalmodel, *Implementation map*, revisions above, `families[].implementations`.)

## 10. Coverage and open items

### Open-item ledger

All items below are assigned for maintainer triage; pending numbers refer to numbered issue drafts, not issued GitHub numbers.

| Item | Coverage / remaining qualification | Tracking |
| --- | --- | --- |
| C1 | U1: independent basis for scenario scores, source weights, confidence constants and engineering envelope; U2: shared datum, vertical origin, phase, timestamps and units; U3: publications/editions/clauses and citation sidecars; U5: generated signed downstream AQG appendix | issue pending (4); taxonomy sidecars #361 |
| C2 | U4: independent risk/taxonomy benchmark and optional-backend qualification; 17 existing skips remain; no licensed or network execution is represented by offline results | issue pending (4) |
| C3 | No in-package implementation-map rows; add section-9 families before future counting | issue pending (7) |
| C4 | Existing recursive Markdown package-data glob matches the pack; wheel exclusion needs a separate packaging change | issue pending (5); #529. [packages/worldenergydata-safety_analysis/pyproject.toml:L70-L75] |
| C5 | Main CLI computation, schema lookup and format integration are incomplete (F1) | issue pending (1). [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/cli.py:L80-L114] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/cli.py:L167-L190] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/cli.py:L238-L261] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/cli.py:L273-L325] |
| C6 | Calibration flag disagreement and stale empty-refit state (F2) | issue pending (2). [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/calibrator.py:L153-L164] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/calibrator.py:L225-L249] |
| C7 | Separate risk algorithms and dashboard metadata contract mismatch (F3) | issue pending (3). [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/risk_index/cli.py:L123-L181] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/risk_index/scorer.py:L276-L286] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/risk_index/dashboard.py:L332-L370] |
| C8 | Fold/holdout-isolated vocabulary fitting not enforced (F6) | issue pending (6). [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/nlp/classification_pipeline.py:L253-L270] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/nlp/classification_pipeline.py:L382-L405] |
| C9 | Final complete feature window omitted (F5) | issue pending (8). [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/analysis/feature_engineering.py:L100-L118] |
| C10 | Missing-input/default and incomplete-ingestion detection, undefined correlation status, historical syntax risk (F4, F7–F9) | #349, #275. [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/data/processors.py:L205-L224] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/analysis/correlation.py:L72-L95] [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/risk_index/data_assembler.py:L493-L512] |
| C11 | Detailed main path is file/schema processing through aggregation/correlation/reporting; other API families have a source inventory and offline coverage, but no independent engineering worked example beyond the two algebraic checks | issue pending (4). [tests/unit/safety_analysis/test_statistical_tests.py:L59-L80] |

### Source reading ledger

Audit record: every pinned module Python file was read and parsed, including all subdirectories; no subpackage was excluded. The table lists the complete module file inventory, with configuration and package README added below.

| Module file | Source range |
| --- | --- |
| `__init__.py` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/__init__.py:L1-L205] |
| `adapters/__init__.py` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/adapters/__init__.py:L1-L7] |
| `adapters/base_adapter.py` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/adapters/base_adapter.py:L1-L55] |
| `adapters/csv_adapter.py` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/adapters/csv_adapter.py:L1-L131] |
| `adapters/hse_adapter.py` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/adapters/hse_adapter.py:L1-L144] |
| `analysis/__init__.py` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/analysis/__init__.py:L1-L71] |
| `analysis/correlation.py` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/analysis/correlation.py:L1-L198] |
| `analysis/decomposition.py` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/analysis/decomposition.py:L1-L85] |
| `analysis/feature_engineering.py` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/analysis/feature_engineering.py:L1-L199] |
| `analysis/incident_aggregation.py` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/analysis/incident_aggregation.py:L1-L171] |
| `analysis/statistical_tests.py` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/analysis/statistical_tests.py:L1-L142] |
| `analysis/time_series.py` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/analysis/time_series.py:L1-L238] |
| `calibrator.py` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/calibrator.py:L1-L471] |
| `cli.py` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/cli.py:L1-L417] |
| `config.py` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/config.py:L1-L86] |
| `constants.py` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/constants.py:L1-L103] |
| `core/__init__.py` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/core/__init__.py:L1-L21] |
| `core/models.py` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/core/models.py:L1-L93] |
| `core/schemas.py` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/core/schemas.py:L1-L120] |
| `data/__init__.py` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/data/__init__.py:L1-L13] |
| `data/config/__init__.py` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/data/config/__init__.py:L1-L1] |
| `data/loaders.py` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/data/loaders.py:L1-L80] |
| `data/processors.py` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/data/processors.py:L1-L251] |
| `exceptions.py` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/exceptions.py:L1-L123] |
| `geohazard/__init__.py` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/geohazard/__init__.py:L1-L1] |
| `geohazard/usgs.py` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/geohazard/usgs.py:L1-L345] |
| `nlp/__init__.py` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/nlp/__init__.py:L1-L38] |
| `nlp/bert_pipeline.py` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/nlp/bert_pipeline.py:L1-L452] |
| `nlp/classification_pipeline.py` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/nlp/classification_pipeline.py:L1-L458] |
| `nlp/model_registry.py` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/nlp/model_registry.py:L1-L197] |
| `nlp/text_preprocessing.py` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/nlp/text_preprocessing.py:L1-L132] |
| `nlp/tfidf_vectorizer.py` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/nlp/tfidf_vectorizer.py:L1-L151] |
| `reports/__init__.py` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/reports/__init__.py:L1-L25] |
| `reports/base_report.py` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/reports/base_report.py:L1-L249] |
| `reports/classification_report.py` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/reports/classification_report.py:L1-L201] |
| `reports/correlation_report.py` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/reports/correlation_report.py:L1-L171] |
| `reports/incident_report.py` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/reports/incident_report.py:L1-L175] |
| `risk_index/__init__.py` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/risk_index/__init__.py:L1-L48] |
| `risk_index/__main__.py` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/risk_index/__main__.py:L1-L7] |
| `risk_index/cli.py` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/risk_index/cli.py:L1-L570] |
| `risk_index/config_loader.py` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/risk_index/config_loader.py:L1-L113] |
| `risk_index/dashboard.py` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/risk_index/dashboard.py:L1-L563] |
| `risk_index/data_assembler.py` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/risk_index/data_assembler.py:L1-L551] |
| `risk_index/methodology.py` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/risk_index/methodology.py:L1-L324] |
| `risk_index/models.py` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/risk_index/models.py:L1-L131] |
| `risk_index/normalizer.py` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/risk_index/normalizer.py:L1-L111] |
| `risk_index/scorer.py` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/risk_index/scorer.py:L1-L297] |
| `risk_index/slicer.py` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/risk_index/slicer.py:L1-L105] |
| `skill.py` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/skill.py:L1-L296] |
| `taxonomy/__init__.py` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/taxonomy/__init__.py:L1-L27] |
| `taxonomy/__main__.py` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/taxonomy/__main__.py:L1-L5] |
| `taxonomy/activity_definitions.py` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/taxonomy/activity_definitions.py:L1-L1419] |
| `taxonomy/activity_registry.py` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/taxonomy/activity_registry.py:L1-L141] |
| `taxonomy/activity_taxonomy.py` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/taxonomy/activity_taxonomy.py:L1-L13] |
| `taxonomy/cli.py` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/taxonomy/cli.py:L1-L227] |
| `taxonomy/incident_classifier.py` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/taxonomy/incident_classifier.py:L1-L554] |

| Configuration / package documentation | Source range |
| --- | --- |
| `data/config/classification_labels.yaml` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/data/config/classification_labels.yaml:L1-L31] |
| `data/config/default_stop_words.yaml` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/data/config/default_stop_words.yaml:L1-L30] |
| `data/config/model_params.yaml` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/data/config/model_params.yaml:L1-L54] |
| `geohazard/README.md` | [packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/geohazard/README.md:L1-L69] |
| Package README | [packages/worldenergydata-safety_analysis/README.md:L1-L11] |

### Test reading ledger

The offline collection and source audit use the following test files; auxiliary `__init__.py` files and `conftest.py` were also read.

| Test file | Source range |
| --- | --- |
| `conftest.py` | [tests/unit/safety_analysis/conftest.py:L1-L152] |
| `core/test_models.py` | [tests/unit/safety_analysis/core/test_models.py:L1-L177] |
| `core/test_schemas.py` | [tests/unit/safety_analysis/core/test_schemas.py:L1-L182] |
| `geohazard/test_usgs.py` | [tests/unit/safety_analysis/geohazard/test_usgs.py:L1-L391] |
| `nlp/test_classification_pipeline.py` | [tests/unit/safety_analysis/nlp/test_classification_pipeline.py:L1-L79] |
| `risk_index/test_config_loader.py` | [tests/unit/safety_analysis/risk_index/test_config_loader.py:L1-L101] |
| `risk_index/test_dashboard.py` | [tests/unit/safety_analysis/risk_index/test_dashboard.py:L1-L301] |
| `risk_index/test_data_assembler.py` | [tests/unit/safety_analysis/risk_index/test_data_assembler.py:L1-L908] |
| `risk_index/test_domain_validation.py` | [tests/unit/safety_analysis/risk_index/test_domain_validation.py:L1-L449] |
| `risk_index/test_models.py` | [tests/unit/safety_analysis/risk_index/test_models.py:L1-L177] |
| `risk_index/test_normalizer.py` | [tests/unit/safety_analysis/risk_index/test_normalizer.py:L1-L207] |
| `risk_index/test_scorer.py` | [tests/unit/safety_analysis/risk_index/test_scorer.py:L1-L605] |
| `risk_index/test_slicer.py` | [tests/unit/safety_analysis/risk_index/test_slicer.py:L1-L161] |
| `risk_index/test_time_trend.py` | [tests/unit/safety_analysis/risk_index/test_time_trend.py:L1-L109] |
| `taxonomy/test_activity_taxonomy.py` | [tests/unit/safety_analysis/taxonomy/test_activity_taxonomy.py:L1-L263] |
| `taxonomy/test_incident_classifier.py` | [tests/unit/safety_analysis/taxonomy/test_incident_classifier.py:L1-L310] |
| `taxonomy/test_taxonomy_cli.py` | [tests/unit/safety_analysis/taxonomy/test_taxonomy_cli.py:L1-L145] |
| `test_adapters.py` | [tests/unit/safety_analysis/test_adapters.py:L1-L320] |
| `test_bert_pipeline.py` | [tests/unit/safety_analysis/test_bert_pipeline.py:L1-L410] |
| `test_calibrator.py` | [tests/unit/safety_analysis/test_calibrator.py:L1-L370] |
| `test_classification_pipeline.py` | [tests/unit/safety_analysis/test_classification_pipeline.py:L1-L261] |
| `test_cli.py` | [tests/unit/safety_analysis/test_cli.py:L1-L97] |
| `test_config.py` | [tests/unit/safety_analysis/test_config.py:L1-L112] |
| `test_constants.py` | [tests/unit/safety_analysis/test_constants.py:L1-L128] |
| `test_correlation.py` | [tests/unit/safety_analysis/test_correlation.py:L1-L104] |
| `test_decomposition.py` | [tests/unit/safety_analysis/test_decomposition.py:L1-L49] |
| `test_exceptions.py` | [tests/unit/safety_analysis/test_exceptions.py:L1-L91] |
| `test_feature_engineering.py` | [tests/unit/safety_analysis/test_feature_engineering.py:L1-L100] |
| `test_incident_aggregation.py` | [tests/unit/safety_analysis/test_incident_aggregation.py:L1-L77] |
| `test_loaders.py` | [tests/unit/safety_analysis/test_loaders.py:L1-L61] |
| `test_model_registry.py` | [tests/unit/safety_analysis/test_model_registry.py:L1-L175] |
| `test_models.py` | [tests/unit/safety_analysis/test_models.py:L1-L128] |
| `test_processors.py` | [tests/unit/safety_analysis/test_processors.py:L1-L87] |
| `test_reports.py` | [tests/unit/safety_analysis/test_reports.py:L1-L315] |
| `test_schemas.py` | [tests/unit/safety_analysis/test_schemas.py:L1-L114] |
| `test_skill.py` | [tests/unit/safety_analysis/test_skill.py:L1-L320] |
| `test_statistical_tests.py` | [tests/unit/safety_analysis/test_statistical_tests.py:L1-L91] |
| `test_text_preprocessing.py` | [tests/unit/safety_analysis/test_text_preprocessing.py:L1-L146] |
| `test_tfidf_vectorizer.py` | [tests/unit/safety_analysis/test_tfidf_vectorizer.py:L1-L141] |
| `test_time_series.py` | [tests/unit/safety_analysis/test_time_series.py:L1-L120] |

### Other documentation found

Audit discovery used the exact module identities `safety_analysis` and `safety-analysis` in tracked `docs/` text; these are contextual documents, not substitutes for the code-derived counts and methods above.

| Document | Module mention evidence |
| --- | --- |
| `docs/AI_USAGE_GUIDELINES.md` | [docs/AI_USAGE_GUIDELINES.md:L83-L92] |
| `docs/CLI.md` | [docs/CLI.md:L639-L655] |
| `docs/adr/0001-domain-package-split.md` | [docs/adr/0001-domain-package-split.md:L48-L48] |
| `docs/plans/2026-04-27-issue-355-align-cli-docs-examples.md` | [docs/plans/2026-04-27-issue-355-align-cli-docs-examples.md:L15-L110] |
| `docs/plans/2026-05-04-issue-349-capability-inventory-audit.md` | [docs/plans/2026-05-04-issue-349-capability-inventory-audit.md:L21-L21] |
| `docs/plans/2026-05-18-issue-416-intervention-hse-patterns.md` | [docs/plans/2026-05-18-issue-416-intervention-hse-patterns.md:L15-L59] |
| `docs/plans/2026-05-18-issue-423-marketing-pipeline-umbrella.md` | [docs/plans/2026-05-18-issue-423-marketing-pipeline-umbrella.md:L17-L17] |
| `docs/plans/2026-05-18-issue-425-operator-hse-benchmarking.md` | [docs/plans/2026-05-18-issue-425-operator-hse-benchmarking.md:L16-L16] |
| `docs/plans/2026-05-18-issue-426-drilling-hse-patterns.md` | [docs/plans/2026-05-18-issue-426-drilling-hse-patterns.md:L17-L17] |
| `docs/plans/2026-05-18-issue-427-seasonal-intervention-risk.md` | [docs/plans/2026-05-18-issue-427-seasonal-intervention-risk.md:L20-L20] |
| `docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md` | [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md:L22-L164] |
| `docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.yaml` | [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.yaml:L325-L1001] |
| `docs/reports/2026-04-26-worldenergydata-cli-example-smoke-matrix.md` | [docs/reports/2026-04-26-worldenergydata-cli-example-smoke-matrix.md:L12-L209] |
| `docs/reports/2026-04-26-worldenergydata-cli-example-smoke-matrix.yaml` | [docs/reports/2026-04-26-worldenergydata-cli-example-smoke-matrix.yaml:L323-L475] |
| `docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.md` | [docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.md:L16-L244] |
| `docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.yaml` | [docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.yaml:L224-L416] |
| `docs/reports/cli-smoke-report-2026-05-11.json` | [docs/reports/cli-smoke-report-2026-05-11.json:L177-L181] |
| `docs/reports/cli-smoke-report-2026-05-11.md` | [docs/reports/cli-smoke-report-2026-05-11.md:L29-L29] |
| `docs/reports/data-freshness-scorecard-2026-06-08.md` | [docs/reports/data-freshness-scorecard-2026-06-08.md:L23-L24] |

### Offline coverage limits

BASE and after audit: 15 BERT test nodes were skipped by the existing module-wide optional-dependency guard, including configuration-only cases; one XGBoost training node and one statsmodels-availability node were also skipped. These are recorded skips, with 0 test-command collection errors; no skip guard was changed. [tests/unit/safety_analysis/test_bert_pipeline.py:L14-L31] [tests/unit/safety_analysis/test_classification_pipeline.py:L14-L24] [tests/unit/safety_analysis/test_classification_pipeline.py:L131-L150] [tests/unit/safety_analysis/test_decomposition.py:L14-L24]

Contract-domain audit: `uv run python -m pytest tests/contracts` in the same invocation form passed 8 tests after the documentation edit, with 0 failed, 0 skipped and 0 NOT_RUN; commands were run on the uncommitted tree at the header code pin.
