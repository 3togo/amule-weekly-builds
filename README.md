# Weekly aMule Ubuntu builds

This repository requests weekly builds of [amule-org/amule](https://github.com/amule-org/amule) on Launchpad.

- PPA: [freetogo/amule-weekly](https://launchpad.net/~freetogo/+archive/ubuntu/amule-weekly)
- Recipe: [amule-weekly](https://code.launchpad.net/~freetogo/+recipe/amule-weekly)
- Ubuntu targets: 24.04 (noble) and 26.04 (resolute), amd64
- Schedule: Mondays at 03:17 UTC, plus manual workflow dispatch

Launchpad imports upstream master and builds the packages. GitHub Actions only requests builds. Launchpad's daily build option stays disabled.

The scheduler uses free runners in this public repository. Each successful weekly run commits a build-request record, keeping the repository active. The source and packaging are also public on Launchpad.

The workflow reads repository variable `LAUNCHPAD_OWNER` and secret `LAUNCHPAD_CREDENTIALS` (a Launchpad OAuth credentials file with public write access). Login passwords and SSH private keys are not used by the workflow.

See [packaging setup](packaging/launchpad/README.md) for package details and local validation.

## Installation

After packages are published, on Ubuntu 24.04 or 26.04:

```sh
sudo add-apt-repository ppa:freetogo/amule-weekly
sudo apt update
sudo apt install amule-weekly
```

The package includes the desktop client, daemon, remote GUI, command-line client, and REST API/web interface. It replaces the distribution's aMule packages while installed.

## Build status

The [first request workflow](https://github.com/3togo/amule-weekly-builds/actions/runs/39467566079) completed successfully. [Latest request records](status/last-request.json) link to the Launchpad source builds. Check the PPA for the resulting binary builds and published packages.
