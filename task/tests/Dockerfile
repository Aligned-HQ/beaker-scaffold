# Separate verifier image. Its build context is task/tests/, so COPY paths are
# relative to this directory and never use a leading `tests/` or `environment/`.
FROM --platform=linux/amd64 python:3.12-slim

ENV WORKSPACE_DIR=/workspace \
    DATA_DIR=/workspace/data \
    OUTPUT_DIR=/workspace/output \
    TESTS_DIR=/tests \
    LOG_DIR=/logs/verifier

WORKDIR ${TESTS_DIR}

RUN python -m pip install --no-cache-dir \
        pytest==8.4.1 \
        pytest-json-ctrf==0.3.5 \
    && mkdir -p ${TESTS_DIR}/data ${OUTPUT_DIR} ${LOG_DIR}

COPY data/ ${TESTS_DIR}/data/
COPY test_outputs.py ${TESTS_DIR}/test_outputs.py
COPY test.sh ${TESTS_DIR}/test.sh

RUN chmod +x ${TESTS_DIR}/test.sh
