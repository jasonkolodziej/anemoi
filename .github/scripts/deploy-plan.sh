#!/usr/bin/env bash
# Decides what .github/workflows/deploy.yml tests and deploys, and writes it
# to $GITHUB_OUTPUT (test_console, test_api, deploy_console, deploy_api,
# plan) plus a human-readable plan to $GITHUB_STEP_SUMMARY -- the summary is
# what the reviewer sees on the run page before approving.
#
# Deploy decisions on main compare each component against a
# `deployed/<component>` tag that deploy.yml moves only after that component
# ships successfully -- not against "what this push changed". So a change
# that didn't ship (approval rejected, deploy failed, or a run superseded by
# a newer commit) stays pending and is picked up by the next run, instead of
# being silently dropped. A component with no tag yet has never been
# deployed by this workflow and counts as changed.
#
# Env: EVENT (github.event_name), REF (github.ref), HEAD_SHA, BEFORE_SHA
# (push), BASE_SHA (pull_request), DISPATCH_CONSOLE / DISPATCH_API
# ("true"/"false", workflow_dispatch inputs).
set -euo pipefail

CONSOLE_RE='^console/'
API_RE='^(docker/api/|docker/multistage\.Dockerfile|src/|pyproject\.toml$|uv\.lock$)'
DOCS_RE='\.md$'
# The workflow and this script: changing them re-runs both test suites (so
# the pipeline change itself gets exercised) but doesn't by itself deploy.
PIPELINE_RE='^\.github/(workflows/deploy\.yml|scripts/deploy-plan\.sh)$'

# touches <regex> <files...>: does any non-Markdown file match?
touches() {
	local re=$1
	shift
	printf '%s\n' "$@" | grep -Ev "$DOCS_RE" | grep -Eq "$re"
}

changed_since() { # changed_since <commit> -> files changed from it to HEAD_SHA
	git diff --name-only "$1" "$HEAD_SHA"
}

test_console=false test_api=false deploy_console=false deploy_api=false
declare -A why=([console]="no changes" [api]="no changes")

case "$EVENT" in
pull_request)
	mapfile -t files < <(git diff --name-only "$BASE_SHA...$HEAD_SHA")
	touches "$CONSOLE_RE|$PIPELINE_RE" "${files[@]}" && test_console=true
	touches "$API_RE|$PIPELINE_RE" "${files[@]}" && test_api=true
	;;
workflow_dispatch)
	test_console=$DISPATCH_CONSOLE
	test_api=$DISPATCH_API
	if [[ $REF == refs/heads/main ]]; then
		deploy_console=$DISPATCH_CONSOLE
		deploy_api=$DISPATCH_API
		for comp in console api; do
			var="deploy_$comp"
			why[$comp]=$([[ ${!var} == true ]] && echo "requested manually" || echo "not requested")
		done
	fi
	;;
push)
	for comp in console api; do
		re=$CONSOLE_RE
		[[ $comp == api ]] && re=$API_RE
		tag="deployed/$comp"
		if ! git rev-parse -q --verify "refs/tags/$tag" >/dev/null; then
			printf -v "deploy_$comp" true
			why[$comp]="never deployed by this workflow (no $tag tag)"
			continue
		fi
		mapfile -t files < <(changed_since "refs/tags/$tag")
		if touches "$re" "${files[@]}"; then
			printf -v "deploy_$comp" true
			why[$comp]="changed since $tag ($(git rev-parse --short "refs/tags/$tag"))"
		fi
	done
	# This push's own files, for the pipeline-change rule. BEFORE_SHA is all
	# zeros (new branch) or may be unknown after a force push.
	if [[ -n ${BEFORE_SHA:-} && ! $BEFORE_SHA =~ ^0+$ ]] && git cat-file -e "$BEFORE_SHA^{commit}" 2>/dev/null; then
		mapfile -t pushed < <(changed_since "$BEFORE_SHA")
	else
		mapfile -t pushed < <(changed_since "$HEAD_SHA~1")
	fi
	touches "$PIPELINE_RE" "${pushed[@]}" && test_console=true && test_api=true
	[[ $deploy_console == true ]] && test_console=true
	[[ $deploy_api == true ]] && test_api=true
	;;
*)
	echo "unexpected event: $EVENT" >&2
	exit 1
	;;
esac

plan=()
[[ $deploy_console == true ]] && plan+=("console + D1 migrations")
[[ $deploy_api == true ]] && plan+=("docker/api")
plan_text=$(IFS=', '; echo "${plan[*]:-nothing}")
plan_text=${plan_text//,/, }

{
	echo "test_console=$test_console"
	echo "test_api=$test_api"
	echo "deploy_console=$deploy_console"
	echo "deploy_api=$deploy_api"
	echo "plan=$plan_text"
} >>"${GITHUB_OUTPUT:-/dev/stdout}"

{
	echo "## Deploy plan: $plan_text"
	echo
	echo "| Component | Test | Deploy | Why |"
	echo "|---|---|---|---|"
	echo "| console (+ D1 migrations) | $test_console | $deploy_console | ${why[console]} |"
	echo "| docker/api | $test_api | $deploy_api | ${why[api]} |"
	if [[ $EVENT == push && ( $deploy_console == true || $deploy_api == true ) ]]; then
		echo
		echo "One approval on the **cloudflare-production** environment deploys everything marked above, in order: D1 migrations → console → docker/api."
	fi
} >>"${GITHUB_STEP_SUMMARY:-/dev/stdout}"
