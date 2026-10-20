# Weekly aMule builds on Launchpad

This setup builds `amule-org/amule` master into a Launchpad PPA. Launchpad
builds and publishes the Ubuntu binaries; a weekly GitHub Actions job requests
the builds. Launchpad's built-in recipe scheduler supports daily builds, so
leave **Build daily** unchecked for a weekly schedule.

The public [PPA](https://launchpad.net/~freetogo/+archive/ubuntu/amule-weekly)
and [recipe](https://code.launchpad.net/~freetogo/+recipe/amule-weekly) are configured
for Ubuntu 24.04 (`noble`) and 26.04 (`resolute`), amd64. Daily builds are disabled.
The public GitHub repository `3togo/amule-weekly-builds` owns the weekly schedule.

Both release targets were built locally from upstream commit
`20feb713f709e2694e3558692ddcacfed2dd9047` on 2026-10-20. Package installation,
command-line version output, installed web interface files, recipe assembly,
and lintian were checked. The first live Launchpad build is being verified.

Launchpad imports upstream into
[`~freetogo/amule/+git/amule`](https://code.launchpad.net/~freetogo/amule/+git/amule).
The separate public packaging repository contains only the packaging overlay.
The packaging maintainer uses the account owner's public GitHub noreply address.

## Package contents

`amule-weekly` contains amule, amulegui, amuled, amulecmd, ed2k, and amuleapi
with its web interface. It conflicts with the distro aMule packages because
it installs the same paths. It does not automatically start a daemon or install
a system service. Experimental transports stay at the upstream defaults.
Updates come through apt; aMule's own update check is disabled.

## Launchpad setup

1. Create a PPA named `amule-weekly` under your account or team. Enable the
   desired architectures, starting with amd64. Ensure the owner has accepted
   Launchpad's PPA terms.
2. Import `https://github.com/amule-org/amule.git` into a Launchpad Git
   repository named `amule` under owner `freetogo` and project `amule`. Wait for a successful import.
3. Push the packaging files to the Launchpad Git repository
   `git+ssh://freetogo@git.launchpad.net/~freetogo/+git/amule-packaging`,
   on branch `packaging/launchpad-weekly`. This repository needs only
   `packaging/launchpad`, without a copy of the upstream history.
4. Use `amule-weekly.recipe`, configured for owner `freetogo`.
   Create the `amule-weekly` source package recipe with that text, targeting
   the PPA and the validated Ubuntu series. Leave **Build daily** unchecked.
5. Request a build manually. Check both the source-recipe build and the
   resulting binary builds in the PPA before enabling the weekly job.

The recipe nests only the packaging directory into the live upstream source.
It never builds a frozen copy of upstream from the packaging branch. The
version template includes a build timestamp. Launchpad constructs the final
per-release source package versions. Revisit the `3.1.0` base
when upstream releases a new version.

## Authorize the weekly trigger

Launchpad's API needs OAuth credentials, not a login password. Install
`python3-launchpadlib`, then authorize using a **new** file path:

```sh
umask 077
python3 packaging/launchpad/request-builds.py --owner freetogo \
  --credentials "$HOME/.config/launchpad/amule-weekly.oauth" \
  --authorize --dry-run
```

Follow the browser authorization prompt. Keep the OAuth file private. Store
its full contents in the scheduler repository's GitHub Actions secret named
`LAUNCHPAD_CREDENTIALS`, and set repository variable `LAUNCHPAD_OWNER` to the
Launchpad account or team name. Do not store your login password in GitHub.

Copy `weekly.yml.in` to `.github/workflows/launchpad-weekly.yml` in the repository
that will own the schedule. The Python helper must also exist on its default
branch. The schedule runs on Mondays at 03:17 UTC, subject to GitHub delays;
`workflow_dispatch` allows a manual request. Scheduled workflows run from the
default branch, and GitHub can disable them after inactivity in public repos.
Enable Actions explicitly if the scheduler repository is a fork.

For a first manual request, run the same Python command without `--authorize`
or `--dry-run`. `--dry-run` checks access and target configuration without
requesting builds. It does not validate compilation. Successful requests mean
queued builds; inspect Launchpad for the final build and publication status.

## Local packaging validation

In a clean upstream checkout, copy `packaging/launchpad/debian` to `debian`.
Install the dependencies listed in `debian/control`, then run
`dpkg-buildpackage -b -us -uc`. Use a clean container for each target release.
The `3.0 (native)` format is intentional for these disposable snapshot builds;
the source archive contains the complete upstream source and packaging.

Validate the recipe itself with `git-build-recipe` after the Launchpad imports
are available. Validate the resulting package with lintian and a clean install.

References: [Launchpad recipe setup](https://ubuntu.com/docs/launchpad/user/how-to/source-package-recipe/),
[Launchpad recipe API](https://api.launchpad.net/devel.html#source_package_recipe),
[GitHub scheduled workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).

Successful workflow runs commit a public build-request record to keep the
scheduler repository active. Repository contents write permission is used
only for that record. Launchpad credentials stay in the Actions secret.
