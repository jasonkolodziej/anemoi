#!/usr/bin/env bash
# One-time setup so .github/workflows/build-training-image.yml can build the
# training image on Cloud Build and update its job, signing in with Workload
# Identity Federation (no stored key). Run by a project owner, from anywhere
# `gcloud` and `gh` are signed in:
#
#   docker/cloud-run-training/setup-ci.sh
#
# Safe to re-run: anything that already exists is kept, and bindings that
# already exist are no-ops. A brand-new service account takes a few seconds
# to become visible to IAM, so bindings on it are retried.
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-anemoi-training}"
REGION="${REGION:-us-central1}"
REPO="${REPO:-jasonkolodziej/anemoi}"
JOB="${JOB:-anemoi-train-schedule}"
POOL=github
PROVIDER=anemoi-repo

PROJECT_NUMBER=$(gcloud projects describe "${PROJECT_ID}" --format 'value(projectNumber)')
CI_SA="anemoi-ci-build@${PROJECT_ID}.iam.gserviceaccount.com"
# Cloud Build runs the build, and the job runs, as this account.
RUNTIME_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

# retry <command...>: up to 6 tries, 10s apart -- for IAM's eventual
# consistency right after the service account is created.
retry() {
	local n
	for n in 1 2 3 4 5 6; do
		if "$@" >/dev/null; then return 0; fi
		echo "  (attempt $n failed; retrying in 10s)" >&2
		sleep 10
	done
	echo "FAILED: $*" >&2
	return 1
}

echo "== APIs"
gcloud services enable iamcredentials.googleapis.com sts.googleapis.com --project "${PROJECT_ID}"

echo "== Workload Identity pool and provider (trusts ${REPO} on main only)"
gcloud iam workload-identity-pools describe "${POOL}" --project "${PROJECT_ID}" --location global >/dev/null 2>&1 ||
	gcloud iam workload-identity-pools create "${POOL}" \
		--project "${PROJECT_ID}" --location global --display-name "GitHub Actions"
gcloud iam workload-identity-pools providers describe "${PROVIDER}" \
	--project "${PROJECT_ID}" --location global --workload-identity-pool "${POOL}" >/dev/null 2>&1 ||
	gcloud iam workload-identity-pools providers create-oidc "${PROVIDER}" \
		--project "${PROJECT_ID}" --location global --workload-identity-pool "${POOL}" \
		--display-name "${REPO} main" \
		--issuer-uri https://token.actions.githubusercontent.com \
		--attribute-mapping "google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref" \
		--attribute-condition "assertion.repository == '${REPO}' && assertion.ref == 'refs/heads/main'"

echo "== Service account ${CI_SA}"
gcloud iam service-accounts describe "${CI_SA}" --project "${PROJECT_ID}" >/dev/null 2>&1 ||
	gcloud iam service-accounts create anemoi-ci-build --project "${PROJECT_ID}" \
		--display-name "GitHub CI: build the training image, update its job"

echo "== Who may act as it: GitHub runs from ${REPO}"
retry gcloud iam service-accounts add-iam-policy-binding "${CI_SA}" --project "${PROJECT_ID}" \
	--role roles/iam.workloadIdentityUser \
	--member "principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL}/attribute.repository/${REPO}"

echo "== What it may do"
# Submit and read builds, use the project's APIs, read a failed build's log.
for role in roles/cloudbuild.builds.editor roles/serviceusage.serviceUsageConsumer roles/logging.viewer; do
	retry gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
		--member "serviceAccount:${CI_SA}" --role "${role}" --condition None
done
# Upload the build's source.
retry gcloud storage buckets add-iam-policy-binding "gs://${PROJECT_ID}_cloudbuild" \
	--member "serviceAccount:${CI_SA}" --role roles/storage.admin
# Run the build, and the job, as the runtime account.
retry gcloud iam service-accounts add-iam-policy-binding "${RUNTIME_SA}" --project "${PROJECT_ID}" \
	--member "serviceAccount:${CI_SA}" --role roles/iam.serviceAccountUser
# Read the image repository: Cloud Run checks whoever updates a job can
# pull the image it's pointed at.
retry gcloud artifacts repositories add-iam-policy-binding anemoi --project "${PROJECT_ID}" --location "${REGION}" \
	--member "serviceAccount:${CI_SA}" --role roles/artifactregistry.reader
# Point this one job at the new image.
retry gcloud run jobs add-iam-policy-binding "${JOB}" --project "${PROJECT_ID}" --region "${REGION}" \
	--member "serviceAccount:${CI_SA}" --role roles/run.developer

echo "== Repository variables (Variables, not Secrets)"
gh variable set GCP_WIF_PROVIDER --repo "${REPO}" \
	--body "projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL}/providers/${PROVIDER}"
gh variable set GCP_CI_SERVICE_ACCOUNT --repo "${REPO}" --body "${CI_SA}"

echo "Done. Check with: gh variable list --repo ${REPO}"
