# Containerized QEMU Guest Agent

This container is designed to run on a minimal container operating system like CoreOS or Flatcar Linux running under QEMU/KVM, Proxmox, or other etc, where the os doesn't have a package management system to easily install the agent.

````bash
docker run --name qemu-ga \
  --privileged \
  --net=host \
  -v /dev:/dev \
  -v /etc/os-release:/etc/os-release:ro  \
  docker.io/danskadra/qemu-ga qemu-ga -v
````
