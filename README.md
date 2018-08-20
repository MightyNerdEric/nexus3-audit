# nexus3-audit

This is a utility to audit and remove unwanted snapshots from a Nexus 3 docker
repository, via the REST API.

## Password
The password can either be passed via the `-p` or `--pass` argument, or via
environment variable `NEXUSPASS` (the argument takes precedence).
