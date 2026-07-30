# Runtime image for the agent. Do not copy solution/, tests/test_outputs.py,
# hidden truth, or expected outputs into this image.
#
# This is the ONLY image the Gemini Data Collection (Nexus) sandbox runs. It
# ignores [verifier].environment_mode and executes the agent and the verifier in
# one container, so the verifier's own dependencies have to be installed here
# too. Without them tests/test.sh dies on "No module named pytest" and the task
# is rejected before a single check runs.
FROM --platform=linux/amd64 python:3.12-slim

ENV WORKSPACE_DIR=/workspace \
    DATA_DIR=/workspace/data \
    OUTPUT_DIR=/workspace/output \
    SOLUTION_DIR=/solution \
    TESTS_DIR=/tests \
    LOG_DIR=/logs/verifier

WORKDIR ${WORKSPACE_DIR}

# The starter solution uses only the Python standard library, so the Oracle
# image has no package-install or network bootstrap step. When a finished task
# needs third-party runtime packages, vendor its Linux/amd64 wheels under this
# build context and install them with --no-index --find-links.
#
# wheels/ carries the verifier's dependencies (pytest and the CTRF reporter).
# Keep it in step with tests/wheels/: the sandbox is air-gapped, so anything
# test.sh imports must be baked in at build time. Installing under /opt rather
# than /tmp is deliberate — the runtime overlays /tmp with an empty tmpfs and
# would erase anything left there during the build.
COPY wheels/ /opt/wheels/

RUN python -m pip install --no-cache-dir --no-index \
        --find-links=/opt/wheels \
        -r /opt/wheels/requirements.txt \
    && rm -rf /opt/wheels

COPY data/ ${DATA_DIR}/

# The sandbox runs one container and executes both the agent and the verifier
# as this unprivileged user, so every directory either step writes to has to be
# owned by it. That includes the whole /logs tree the harness collects from:
# naming only ${LOG_DIR} leaves /logs itself root-owned, so the agent cannot
# create /logs/agent and its output redirect fails before the solution runs.
# The symptom is a trial that dies with no artifacts and no reward file.
RUN useradd --create-home --shell /bin/bash agent \
    && mkdir -p ${WORKSPACE_DIR} ${DATA_DIR} ${OUTPUT_DIR} ${SOLUTION_DIR} \
        ${TESTS_DIR} /logs /logs/agent /logs/artifacts ${LOG_DIR} \
    && chown -R agent:agent ${WORKSPACE_DIR} ${SOLUTION_DIR} ${TESTS_DIR} /logs

USER agent
