#!/usr/bin/env bash
# Ask GitHub Pages to build the commit that is checked out.
#
# A push made with GITHUB_TOKEN does not start a Pages build. The owner's push
# does, and that build can still be running (or queued) with the older HTML.
# Wait for any in-flight build to finish, request a build of HEAD, and if a
# later build moves the site off HEAD, request HEAD again.

set -euo pipefail

if [ "${BUILD_TYPE_OVERRIDE:-}" != "" ]; then
  build_type="${BUILD_TYPE_OVERRIDE}"
else
  build_type=$(gh api "repos/${GITHUB_REPOSITORY}/pages" --jq .build_type)
fi
echo "Pages build_type=${build_type}"
if [ "${build_type}" != "legacy" ]; then
  echo "Pages is not publishing from the branch, so no branch build was requested."
  exit 0
fi

head=$(git rev-parse HEAD)
echo "Want Pages to publish ${head}"

latest() {
  json=$(gh api "repos/${GITHUB_REPOSITORY}/pages/builds/latest")
  status=$(jq -r .status <<<"${json}")
  commit=$(jq -r .commit <<<"${json}")
}

request() {
  echo "Requesting a Pages build of the latest default-branch commit."
  gh api --method POST "repos/${GITHUB_REPOSITORY}/pages/builds" >/dev/null
}

for _ in $(seq 1 40); do
  latest
  echo "in flight: status=${status} commit=${commit}"
  if [ "${status}" = "built" ] || [ "${status}" = "errored" ]; then
    break
  fi
  sleep 15
done

attempts=0
while [ "${attempts}" -lt 3 ]; do
  request
  attempts=$((attempts + 1))
  published=0
  for _ in $(seq 1 40); do
    latest
    echo "status=${status} commit=${commit}"
    if [ "${commit}" = "${head}" ] && [ "${status}" = "errored" ]; then
      jq .error <<<"${json}"
      exit 1
    fi
    if [ "${commit}" = "${head}" ] && [ "${status}" = "built" ]; then
      published=1
      break
    fi
    sleep 15
  done
  if [ "${published}" -ne 1 ]; then
    continue
  fi
  held=1
  for _ in $(seq 1 6); do
    sleep 10
    latest
    echo "confirm status=${status} commit=${commit}"
    if [ "${commit}" != "${head}" ] || [ "${status}" != "built" ]; then
      held=0
      echo "A later Pages build moved off ${head}; requesting it again."
      break
    fi
  done
  if [ "${held}" -eq 1 ]; then
    echo "GitHub Pages published ${head}."
    exit 0
  fi
done

echo "GitHub Pages did not publish ${head}."
exit 1
