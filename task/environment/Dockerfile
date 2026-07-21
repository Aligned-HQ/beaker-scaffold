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

# Harbor's installed-agent bootstrap expects these tools. Keeping them in the
# final stage makes its system-package step an offline no-op when needed.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        ripgrep \
        git \
    && rm -rf /var/lib/apt/lists/*

# Add only dependencies required by the agent-facing task, with pinned Python
# versions. Replace this block when the real workflow needs domain packages.
# RUN python -m pip install --no-cache-dir numpy==2.1.3 scipy==1.14.1

COPY data/ ${DATA_DIR}/

RUN useradd --create-home --shell /bin/bash agent \
    && mkdir -p ${WORKSPACE_DIR} ${OUTPUT_DIR} ${LOG_DIR} \
    && chown -R agent:agent ${WORKSPACE_DIR} ${OUTPUT_DIR}

USER agent
