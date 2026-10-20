# Weekly aMule Ubuntu builds

This repository requests weekly builds of [amule-org/amule](https://github.com/amule-org/amule) on Launchpad.

- PPA: [freetogo/amule-weekly](https://launchpad.net/~freetogo/+archive/ubuntu/amule-weekly)
- Recipe: [amule-weekly](https://code.launchpad.net/~freetogo/+recipe/amule-weekly)
- Ubuntu targets: 24.04 (noble) and 26.04 (resolute), amd64
- Schedule: Mondays at 03:17 UTC, plus manual workflow dispatch

Launchpad imports upstream master and builds the packages. GitHub Actions requests builds and monitors publication. Launchpad's daily build option stays disabled.

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

The [publication monitor](https://github.com/3togo/amule-weekly-builds/actions/workflows/publication.yml) checks both requested Ubuntu builds every 10 minutes on GitHub-hosted runners, including when your computer is off. GitHub may delay scheduled runs. You can also run it manually from Actions.

[Latest request records](status/last-request.json) identify the source builds. The monitor reads the exact source version from each build log, follows its binary builds, and requires both Launchpad's Published status and that exact version in the corresponding amd64 APT package index. Old packages cannot satisfy a new request.

Progress changes are committed to `status/publication.json`. Each run has a summary with build links; failed builds or HTTP/API errors fail the workflow with diagnostic annotations. Pending publication is a successful check, not a claim that packages are ready. Configure GitHub Actions notifications in your GitHub account to receive failed-run alerts.

For signed manual source uploads, a target in `status/last-request.json` can specify an explicit `version` and use the PPA URL as its `url`. The monitor then follows that exact source version through binary builds and APT publication without depending on a recipe build. The next weekly request replaces these targets with the new recipe builds as usual.

Once both versions are available, scheduled runs skip network polling. The next weekly request automatically starts monitoring again. This monitor uses public endpoints and needs no Launchpad credentials. It reports blockers; packaging fixes still require a code change.
