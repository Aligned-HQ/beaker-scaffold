# Runtime image for the agent. Do not copy solution/, tests/, hidden truth, or
# expected outputs into this image.
FROM --platform=linux/amd64 python:3.12-slim

ENV WORKSPACE_DIR=/workspace \
    DATA_DIR=/workspace/data \
    OUTPUT_DIR=/workspace/output \
    OUTPUT_PATH=/workspace/output/result.json \
    SOLUTION_DIR=/solution \
    TESTS_DIR=/tests \
    LOG_DIR=/logs/verifier

WORKDIR ${WORKSPACE_DIR}

# The starter solution uses only the Python standard library, so the Oracle
# image has no package-install or network bootstrap step. When a finished task
# needs third-party runtime packages, vendor its Linux/amd64 wheels under this
# build context and install them with --no-index --find-links.

COPY data/ ${DATA_DIR}/

RUN useradd --create-home --shell /bin/bash agent \
    && mkdir -p ${WORKSPACE_DIR} ${OUTPUT_DIR} ${LOG_DIR} \
    && chown -R agent:agent ${WORKSPACE_DIR} ${OUTPUT_DIR} ${LOG_DIR}

USER agent
