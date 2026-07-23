.PHONY: setup-check check check-strict runner-test run-smoke run-harbor run-task-fixer run-task-review run-trajectory-review verify-skill-runs

setup-check:
	./scripts/check-setup.sh $(ARGS)

check:
	python3 scripts/validate_scaffold.py

check-strict:
	python3 scripts/validate_scaffold.py --strict

runner-test:
	PYTHONDONTWRITEBYTECODE=1 python3 scripts/test_harbor_runner.py

run-smoke:
	./harbor_runner.py task --no-remote --smoke-test $(ARGS)

run-harbor:
	./harbor_runner.py $(ARGS)

run-task-fixer:
	./scripts/run-task-fixer.sh $(TARGET)

run-task-review:
	./scripts/run-task-review.sh $(TARGET)

run-trajectory-review:
	./scripts/run-trajectory-review.sh $(TARGET)

verify-skill-runs:
	./scripts/verify-skill-runs.sh $(ARGS)
