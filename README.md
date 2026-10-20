# Weekly aMule Ubuntu builds

This repository requests weekly builds of [amule-org/amule](https://github.com/amule-org/amule) on Launchpad.

- PPA: [freetogo/amule-weekly](https://launchpad.net/~freetogo/+archive/ubuntu/amule-weekly)
- Recipe: [amule-weekly](https://code.launchpad.net/~freetogo/+recipe/amule-weekly)
- Ubuntu targets: 24.04 (noble) and 26.04 (resolute), amd64
- Schedule: Mondays at 03:17 UTC, plus manual workflow dispatch

Launchpad imports upstream master and builds the packages. GitHub Actions only requests builds. Launchpad's daily build option stays disabled.

The private scheduler repository avoids GitHub's scheduled-workflow inactivity limit for public repositories. The source and packaging remain publicly available on Launchpad.

The workflow reads repository variable `LAUNCHPAD_OWNER` and secret `LAUNCHPAD_CREDENTIALS` (a Launchpad OAuth credentials file with public write access). Login passwords and SSH private keys are not used by the workflow.

See [packaging setup](packaging/launchpad/README.md) for package details and local validation.
