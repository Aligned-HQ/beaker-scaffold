# Tolerance guidance for scientific verifiers

Numeric tolerances are part of the verifier contract. They are not universal
scientific constants and must be calibrated for the data, units, observable, and
decision that the task actually uses.

Use the table below as a starting point for a calibration discussion, not as an
automatic pass/fail table:

| Quantity | Illustrative starting point | Calibration notes |
| --- | --- | --- |
| Binding or free energy | ±2 kcal/mol or ±20% | State which bound is used. Check sign and units, and compare at least one other defensible method or perturbation before choosing the final bound. |
| Molecular or structural distance | ±0.1 Å or ±1% | Relate the bound to coordinate precision, experimental resolution, and the decision-relevant distance. |
| Bond/dihedral angle | ±5° | Use a circular difference for periodic angles and justify a tighter or wider bound from the measurement or model uncertainty. |
| Concentration or assay measurement | The assay's stated precision or confidence interval | Do not replace missing uncertainty with a generic percentage when the assay protocol or supplied data can provide a better estimate. |
| Rate, affinity, or other log-scale quantity | ±0.3 log10 units (about a two-fold factor) | Only use this when the quantity is reported on a log scale and the experimental/model variation supports it. |
| Bounded score or model metric | ±0.01 absolute, or the observed seed/held-out variation | Use the variation of legitimate reruns or an uncertainty interval when it is available; arbitrary decimal precision is not a scientific requirement. |
| Counts, identifiers, and categorical decisions | Exact match | If multiple labels are scientifically equivalent, encode that equivalence explicitly instead of adding a numeric tolerance. |

When both absolute and relative tolerances are useful, document the rule in
`verification_explanation`. A common rule is
`abs(value - reference) <= max(abs_tol, rel_tol * abs(reference))`; use `min`
instead when the task deliberately requires the tighter bound. Near zero,
absolute tolerance is usually more meaningful than relative tolerance.

For every inequality in `tests/`, record what it brackets, which legitimate
sources of variation it covers (for example rounding, alternative algorithms,
instrument noise, or stochastic seeds), and how it was checked against a
reasonable alternative solution. The bound must accept scientifically
defensible alternatives and reject a materially wrong result. If a result is
used to make a thresholded decision, test the decision and its supporting
measurement rather than relying only on a broad global numeric range.
