# Arctic Fuse Home TV

Fork of [Arctic Fuse 3](https://github.com/jurialmunkey/skin.arctic.fuse.3),
by jurialmunkey. Original artwork, attribution and CC BY-NC-SA 4.0 license remain.
Home TV adds a vertical native PVR channel list, current programme details and
access to the author's original top menu. Its stable installed ID is
`skin.arctic.fuse.hometv`; settings remain in that add-on's own profile.

## Branches

- `omega`: original author branch, without Home TV changes. It is an upstream
  reference; development commits are not automatically installed.
- `upstream-stable`: the last published author tag accepted for integration.
- `home-tv`: Home TV source, based on an author tag with real Git ancestry.
- `updates/arctic-X.Y.Z`: proposed integration; never automatically merged.
- `kodi-repo`: approved packages and the Kodi repository index, without profiles.

Only three existing runtime files are customised: `1080i/Home.xml`,
`1080i/Startup.xml`, and `1080i/Custom_1182_Dialog_Topmenu_Overlay.xml`.
The Home source has an insertion point for the current author's native menu.
The add-on ID and name are changed at packaging time so upstream source keeps
its original names and can be merged without thousands of namespace edits.

The first source build reproduces the already device-tested 1.0.0 ZIP byte for
byte. The exact checksum is recorded in `.hometv/approvals/1.0.0.json`.

## Receiving author updates

The **Propose Arctic updates** workflow checks the author's official Omega
repository manifest daily. It accepts stable versions only, fetches the
corresponding author tag, verifies version, GUI API and commit ancestry, and
performs a normal Git merge in a temporary worktree.

On a clean merge it increments the Home TV package version, builds a candidate
and attempts to open a draft PR. If GitHub blocks token-created PRs, it keeps
the update branch and provides a comparison link in the run summary instead.
On conflicts it aborts the merge and prepares a report-only proposal listing
the affected files. Existing update branches are never reset
or force-pushed. A failed integration cannot replace the TV's installed skin.
New development commits with the same published version are left alone.

Git merges cannot prove runtime compatibility. Before an update is released,
check cold startup, first OK playback, Back to the same list, channel changes,
native Film/Series navigation, skin switching and profile preservation on the
intended Kodi/device combination. Verify audio on the TV. Record only checks
that actually passed. Never copy private profiles or logs into this repository.

## Build and release

Python 3.13, Git and the standard library are sufficient:

```sh
python -m unittest discover -s .hometv/tests -v
python .hometv/maintain.py build
```

Candidates have no verified runtime unless their exact SHA256 already has a
device approval record. After testing, commit `.hometv/approvals/VERSION.json`
with the package hash, verified runtime and completed checks. Do not approve a
future Kodi release by copying an earlier record. A version already published
cannot be replaced with different bytes; bump `.hometv/config.json` instead.

Run **Publish approved Home TV** manually on `home-tv`, entering that version.
The workflow rebuilds the skin and refuses publication unless the exact bytes
match the device approval. It updates `kodi-repo` using a fast-forward push.
No scheduled workflow publishes or installs a candidate.

The bootstrap repository add-on is available on `kodi-repo` as
`repository.arctic.hometv-1.0.0.zip`. Its repository directory is limited to
Kodi 21. A future Kodi 22 channel needs its own compatibility review and tests;
it is not enabled by changing a version label. Preferences live outside the
skin package and are not overwritten by a normal Kodi add-on update. Future
upstream changes to settings formats may still require a migration.

## GitHub setup

Make `home-tv` the default branch and enable Actions for the fork. The existing
restriction on token-created pull requests can remain in place: update branches
and comparison links work without changing that setting. Workflow job
permissions are read-only for checks and write only for update proposals or
manual publication. No personal access token or device credential is stored.
Run the check workflow and a manual upstream check after first setup. GitHub
may disable schedules on inactive public repositories; check Actions if the
daily job stops. Scheduled runs do not guarantee uninterrupted monitoring.

The original author's repository-dispatch workflow is removed from the Home TV
branch: Home TV releases never dispatch a release to the author's repository.
The project does not modify Kodi, plugins or the original installed AF3 skin.
Emergency recovery and private device backups remain outside this public fork.

## Current scope

1.0.0 was checked on Fire TV with Kodi 21.3, Skin Variables 2.2.9,
Texture Maker 0.2.11 and TMDb Helper 6.17.9. Audio was restored by the user on the
Fire TV. This is not a guarantee for later Kodi/plugin versions or every device.
