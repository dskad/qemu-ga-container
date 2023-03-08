# QEMU Guest Agent Container Image

## Overview

This container is designed to run on a minimal container operating system like CoreOS or
Flatcar Linux, running under QEMU/KVM, Proxmox, or other libvirt based virtual machine.
These operating systems often don't have a package management system to easily install the agent.

## Quick Start

Enable the QEMU Guest Agent Channel in the VM configuration.
| VM Host                        | Enable Guest Agent                                            |
| ------------------------------ | ------------------------------------------------------------- |
| QEMU / Virtual Machine Manager | Add the `Guest Agent Channel` device (org.qemu.guest_agent.0) |
| Proxmox                        | Enable the `QEMU Guest Agent` option                          |

### Docker on Fedora CoreOS

````bash
sudo docker run --rm -d --name qemu-ga \
  --device /dev/virtio-ports/org.qemu.guest_agent.0:/dev/virtio-ports/org.qemu.guest_agent.0 \
  -v /etc/os-release:/etc/os-release:ro \
  --uts=host \
  docker.io/danskadra/qemu-ga
````

## Useful Options

| Option                                               | Description                                   |
| ---------------------------------------------------- | --------------------------------------------- |
| `--device [VirtIO Serial Port]:[VirtIO Serial Port]` | (**Required**) Agent communication to host VM |
| `--uts=host`                                         | Allows Guest Agent to read VM hostname        |
| `-v /etc/os-release:/etc/os-release:ro`              | Read only access to VM OS info                |

## Security Considerations

The QEMU Guest Agent is designed to interact directly with the host operating system.
To allow access to the host while running the Guest Agent inside of a container, the
container must be run with extended capabilities. Generally this is accomplished by
using the `--privileged` command option. This grants far more capabilities to the
container than is needed by the use case presented here. i.e. Retrieving IP addresses,
host names, OS versions, etc, for visibility to the KVM host.

Security can be improved by replacing the `--privileged` option with the `--device`
option and bind mounting a volumes to specific files. This can be used to limit access
to only the VirtIO Guest Agent device, instead of all the devices in /dev or other
capabilities granted by `--privileged`.

## Additional Info

- [QEMU Guest Agent Protocol Reference](https://qemu.readthedocs.io/en/latest/interop/qemu-ga-ref.html)
- [GitHub Repo](https://github.com/dskad/qemu-ga-container)
