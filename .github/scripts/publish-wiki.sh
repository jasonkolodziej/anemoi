#!/usr/bin/env bash
# Publishes the repo's wiki/ folder to the GitHub wiki (<repo>.wiki.git),
# called by .github/workflows/wiki.yml from a checkout of the main repo.
#
# Usage: publish-wiki.sh <wiki-clone-dir>
# Env:   SOURCE_SHA      the main-repo commit being published
#        IMPORTED_FROM   the wiki commit wiki/ was first imported from
#
# Refuses to overwrite an edit made directly in the wiki (its web UI): every
# publish records the main-repo commit it came from as a `Source-Commit:`
# trailer, and the wiki must still match wiki/ at that commit before it is
# replaced. Before the first publish there is no trailer, so the wiki must
# still be at exactly IMPORTED_FROM.
set -euo pipefail

wiki=$1
: "${SOURCE_SHA:?}" "${IMPORTED_FROM:?}"

# The most recent publish anywhere in the wiki's history, not just its tip:
# an edit made in the UI after a publish is a newer commit without a trailer.
last=$(git -C "$wiki" log --format='%(trailers:key=Source-Commit,valueonly)' | grep -m 1 . || true)
if [[ -n $last ]]; then
	if ! git cat-file -e "$last^{commit}" 2>/dev/null; then
		echo "::error::The wiki was last published from $last, which isn't in this repository's history."
		exit 1
	fi
	expected=$(mktemp -d)
	git archive "$last" wiki | tar -x -C "$expected"
	if ! drift=$(diff -rq --exclude=.git "$expected/wiki" "$wiki"); then
		echo "::error::The wiki was edited outside wiki/ since $last. Copy these edits into wiki/ in a PR first, or they'd be overwritten:"
		echo "$drift"
		exit 1
	fi
else
	head=$(git -C "$wiki" rev-parse HEAD)
	if [[ $head != "$IMPORTED_FROM" ]]; then
		echo "::error::The wiki is at $head, not $IMPORTED_FROM (the commit wiki/ was imported from), and has never been published from this repository. Copy its newer edits into wiki/ in a PR, then update IMPORTED_FROM in .github/workflows/wiki.yml."
		exit 1
	fi
fi

# Replace the whole tree, so a page deleted from wiki/ is deleted from the wiki.
find "$wiki" -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +
cp -a wiki/. "$wiki/"
git -C "$wiki" add -A
if git -C "$wiki" diff --cached --quiet; then
	echo "wiki already matches wiki/ at $SOURCE_SHA; nothing to publish"
	exit 0
fi
subject=$(git log -1 --format=%s "$SOURCE_SHA")
git -C "$wiki" -c user.name="github-actions[bot]" \
	-c user.email="41898282+github-actions[bot]@users.noreply.github.com" \
	commit -q -m "$subject" -m "Source-Commit: $SOURCE_SHA"
git -C "$wiki" push -q origin HEAD
echo "published wiki/ at $SOURCE_SHA"
git -C "$wiki" show --stat --format= HEAD
