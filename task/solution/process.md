# Intended solution process

This is a review-facing template. Replace the smoke workflow with the process an expert would actually use for the chosen scientific question.

1. Inspect the public inputs under `DATA_DIR`, confirm their format, units, dimensions, identifiers, and basic quality before selecting an analysis path.
2. State the practitioner-facing decision and identify the intermediate measurements or diagnostics that determine later choices.
3. Choose among scientifically defensible methods, explaining why the selected model or computational approach fits the data and the decision. Keep meaningful alternatives visible rather than baking the reference recipe into `instruction.md`.
4. Compute the primary result from the inputs using reproducible, environment-based paths and pinned dependencies. Record uncertainty, sensitivity, convergence, or quality checks appropriate to the domain.
5. Validate the result with independent relationships, held-out data, physical constraints, replicated calculations, or other evidence that does not simply reproduce the same implementation.
6. Write every declared machine-checkable artifact under `OUTPUT_DIR`. Ensure schemas, units, ordering, and metadata match the public contract.
7. Re-run the pipeline from the visible inputs with the same environment variables and confirm that the outputs are deterministic or that the allowed stochastic variation is documented and tested.

Do not put hidden reference values, verifier-only fixtures, or answer shortcuts in this file. The final version should describe the real scientific workflow clearly enough for a non-specialist reviewer to understand why the solution is plausible.
