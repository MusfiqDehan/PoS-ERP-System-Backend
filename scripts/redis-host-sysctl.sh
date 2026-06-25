#!/usr/bin/env sh
# Set vm.overcommit_memory=1 on the Docker/WSL host for Redis BGSAVE/AOF fork.
# Compose runs this via the redis-sysctl-init one-shot service; use this script
# on bare-metal hosts or if the init container cannot get privileged mode.
set -eu

if sysctl -w vm.overcommit_memory=1; then
  echo "vm.overcommit_memory=1 applied."
else
  echo "Failed to set vm.overcommit_memory. Run as root on the host." >&2
  exit 1
fi

if [ -d /etc/sysctl.d ]; then
  printf '%s\n' 'vm.overcommit_memory = 1' > /etc/sysctl.d/99-redis-overcommit.conf
  echo "Persisted to /etc/sysctl.d/99-redis-overcommit.conf"
fi
