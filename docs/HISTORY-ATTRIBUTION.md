# Commit author reattribution

The user requested balanced author counts between `aimwnoaim` and `momnakhan24`,
and previously identified both as accounts they control. This branch openly
reattributes selected existing commits between those identities. It does not add
empty commits or pretend that new implementation work happened.

The balance is an author-metadata adjustment, not evidence that two independent
people performed equal work. AI assistance remains disclosed in AI-USAGE.md.

The original `dev-aimwnoaim` history is retained, together with an archive reference
named `archive/pre-balance-2026-11-07`. Commits shared with main are not rewritten.
Selected feature commits change author/committer identity; original timestamps,
messages and trees remain intact. Descendant SHAs necessarily change because their
parent SHAs change. A mapping of rewritten historical SHAs is recorded separately.

Original image tags, CI runs and evidence referring to old SHAs are not relabelled
as builds or checks of new SHAs. The archive and mapping retain their provenance.
The balanced branch needs a fresh CI run before submission. Existing published
branches, main, review approvals and the original PR are not overwritten as part
of preparing this branch.

## Subsequent branch publication

The user renamed the published working branch to **dev** and deleted the older
remote development/archive branches. Original history is retained locally and the
committed mapping still records provenance; no deleted remote branch is recreated.
New commits now use **aimwnoaim** only, at the user's explicit instruction. Counts
can diverge as genuine work continues. Later CI verifies the actual dev head;
old image tags and run URLs remain identified by their original source SHAs.
