# Separate verifier image. Its build context is task/tests/, so COPY paths are
# relative to this directory and never use a leading `tests/` or `environment/`.
FROM --platform=linux/amd64 python:3.12-slim

ENV WORKSPACE_DIR=/workspace \
    DATA_DIR=/workspace/data \
    OUTPUT_DIR=/workspace/output \
    TESTS_DIR=/tests \
    LOG_DIR=/logs/verifier

WORKDIR ${TESTS_DIR}

COPY wheels/ /opt/wheels/

RUN python -m pip install --no-cache-dir --no-index \
        --find-links=/opt/wheels \
        -r /opt/wheels/requirements.txt \
    && rm -rf /opt/wheels \
    && mkdir -p ${TESTS_DIR}/data ${OUTPUT_DIR} ${LOG_DIR}

COPY data/ ${TESTS_DIR}/data/
COPY test_outputs.py ${TESTS_DIR}/test_outputs.py
COPY test.sh ${TESTS_DIR}/test.sh

RUN chmod +x ${TESTS_DIR}/test.sh
