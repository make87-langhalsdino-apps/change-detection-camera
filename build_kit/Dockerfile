FROM debian:bookworm-slim

## Custom Add-ons

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
      gnupg

RUN echo "deb http://archive.raspberrypi.org/debian/ bookworm main" > /etc/apt/sources.list.d/raspi.list \
    && apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 82B129927FA3303E

RUN apt-get update \
#    && apt-get -y upgrade \  # DO WE NEED THIS?
    && apt-get install -y --no-install-recommends \
        python3-picamera2 \
        libcamera-apps \
        libcamera-dev \
        libcamera-tools \
        libcap-dev \
        python3-libcamera \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*