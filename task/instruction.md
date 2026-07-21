<!-- TEMPLATE ONLY: replace this contract before running a benchmark campaign. -->

# Replace with the scientific task title

Replace this paragraph with a concise statement of the real research objective. Name the decision the result supports, but do not prescribe a reference implementation or an ordered recipe.

The task inputs are available under `/workspace/data`. Replace this sentence with the absolute path, format, units, dimensions, and scientifically relevant fields for each public input. If an input is generated, describe the generated artifact and keep its deterministic generator in `environment/`.

Produce the required deliverables under `/workspace/output`. This starter contract uses the following smoke outputs; replace the filenames and schema with the actual scientific output contract:

- `/workspace/output/result.json`: a JSON object with exactly `n_observations`, `mean_value`, `std_value`, `minimum`, and `maximum`.

For the starter smoke contract, `result.json` summarizes the numeric `value` column in `/workspace/data/input.csv` using finite numbers and a population standard deviation. A finished task should instead state the domain-specific definitions, units, constraints, and exact structured-output schema that its verifier checks.

Do not hardcode expected output values. Keep all final files under `/workspace/output` and make the computation reproducible from the visible inputs.
