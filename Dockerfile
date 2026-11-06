FROM alpine:3.24
LABEL maintainer="dskadra@gmail.com"
LABEL maintainer="philipp@haussleiter.de"

ENV STATS_PORT=8080

RUN apk add --update --no-cache qemu-guest-agent python3

WORKDIR /app
COPY stats_service.py /app/stats_service.py
COPY entrypoint.sh /entrypoint.sh

ENTRYPOINT [ "/entrypoint.sh" ]
CMD ["-m", "virtio-serial", "-p", "/dev/virtio-ports/org.qemu.guest_agent.0"]
