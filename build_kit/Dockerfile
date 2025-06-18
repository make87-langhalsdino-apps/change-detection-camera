FROM ghcr.io/make87/debian:bookworm AS base-image

ARG VIRTUAL_ENV=/make87/venv

RUN apt-get update \
    && apt-get install --no-install-suggests --no-install-recommends -y \
        build-essential \
        python3 \
        python3-venv \
        python3-dev \
        python3-pip \
        # --------------------------------------------------------------
        # Runtime libraries required by opencv-python-headless wheels
        # --------------------------------------------------------------
        libjpeg-dev \
        libpng-dev \
        libtiff5 \
        libopenjp2-7 \
        libatlas3-base \
        # --------------------------------------------------------------
        # Picamera2 runs on top of libcamera; these packages are present
        # in Debian 12 and are harmless on non-Pi hardware.
        # --------------------------------------------------------------
        python3-libcamera \
        libcamera-dev; \
    && python3 -m venv ${VIRTUAL_ENV} \
    && ${VIRTUAL_ENV}/bin/pip install --upgrade pip setuptools wheel \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

RUN ${VIRTUAL_ENV}/bin/python3 -m pip install -U pip
RUN set -eux; \
    if [ -f ./pip.conf ]; then \
      echo "Found pip.conf, pointing PIP_CONFIG_FILE at it"; \
      export PIP_CONFIG_FILE="$(pwd)/pip.conf"; \
    else \
      echo "No pip.conf found, using default indexes"; \
    fi; \
    ${VIRTUAL_ENV}/bin/python3 -m pip install .


FROM ghcr.io/make87/python3-debian12:latest

ARG VIRTUAL_ENV=/make87/venv
COPY --from=base-image ${VIRTUAL_ENV} ${VIRTUAL_ENV}

ENTRYPOINT ["/make87/venv/bin/python3", "-m", "app.main"]
