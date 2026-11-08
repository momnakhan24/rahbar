# Repository owner and final submission steps

Implementation work and pushes belong on `dev`. Do not paste a token in this file,
a PR, a screenshot or chat. The connected account `aimwnoaim` has push access but
not repository administration permission. At the latest metadata check, the original
repository had no Actions secrets or variables listed. Main reports protected; the
full protection rule needs an owner check.

## 1. Owner: add Docker Hub credentials

In [repository Actions settings](https://github.com/momnakhan24/rahbar/settings/secrets/actions):

1. Secrets → New repository secret → name **DOCKERHUB_TOKEN**.
2. Value: the Docker Hub personal access token for **aimwnoaim**, with Read & Write
   permission. Paste it directly into GitHub, never into a committed file.
3. Variables → New repository variable → **DOCKERHUB_USERNAME** = **aimwnoaim**.
4. Confirm the token has not expired/revoked and can push the three repositories
   `aimwnoaim/rahbar-api`, `aimwnoaim/rahbar-indexer`, `aimwnoaim/rahbar-ui`.

A Docker Desktop login or a token sent in a message does not create a GitHub secret.
The agent did not export your Docker Desktop credential to GitHub.

## 2. Owner: verify main protection and review

In Settings → Branches or Rulesets, require for `main`:

- A pull request, one genuine approving review, and no direct pushes.
- Passing **quality** and **cluster-smoke** checks; require up-to-date branches.
- Apply the rule to relevant contributors; do not bypass it to complete the demo.

Review the PR whose head is **dev**, including AI-USAGE, HISTORY-ATTRIBUTION, the
per-answer generation review and the final evaluation. Only merge after the exact
head commit is green. Git author counts do not prove two independent contributors;
the documented author reattribution must remain visible and understood.

## 3. Capture required visual evidence

Save actual screenshots in `docs/evidence/` and commit/push each file on dev before
final merge. JSON and text evidence already recorded do not replace rubric screenshots.

- UI: run the README's Ingress port-forward; open http://localhost:18080, ask a
  supported question such as "What minimum CGPA avoids academic warning?", and capture the answer with citations. Capture a hostel
  question such as "What is the application deadline for reserving a hostel room?" showing refusal as well.
- Branch protection settings showing the required checks/review.
- Deliberately failing evaluation PR with a disabled merge button, then restored
  green checks. Earlier failed/restored run metadata is recorded; a historical
  screenshot was not fabricated. If no original screenshot exists, repeat the
  controlled fixture-evidence removal/restoration on dev with a real PR and review
  requirements active. Restore the evidence and require CI to pass before merging.

The failed and restored fork demonstration is documented in FAILURE-ANALYSIS and
`docs/evidence/gate-*.json`. A screenshot of a run log alone is not the requested
blocked-merge screenshot. Avoid including credentials in any screenshot.

## 4. Merge and verify hosted CD

After review and screenshots, merge dev → main through GitHub. This triggers **CD**:

1. **test** runs the complete reusable CI (tests, manifests, scans, real fixture gate).
2. **build-push**, only after test succeeds, logs into Docker Hub, builds/scans and
   publishes all three images tagged with the merge commit's full SHA.
3. **deploy**, only after publication succeeds, creates a disposable kind cluster,
   waits for Ingress/admission and app rollouts, and checks a cited JSON answer
   through Ingress. Approve the `production` environment if GitHub requests it.

Open [CD runs](https://github.com/momnakhan24/rahbar/actions/workflows/cd.yml).
Wait until the whole run is green. Download `published-images` and
`ingress-acceptance` artifacts. The acceptance cluster ends with the runner; the
real university corpus remains the separately verified local deployment.

If CD fails, read the first failing step. Missing registry token needs owner setup;
login/push denial needs a valid token for the configured account; an environment
approval needs its authorized reviewer. Infrastructure or code failures require a
new fix on dev and passing CI before a new merge. Never bypass tests or change the
baseline merely to turn a run green. A manual retry can use **Run workflow** on
main after configuration is corrected; image tags still identify that exact commit.

## 5. Submit one team entry to Classroom

Deadline: **8 November 2026, 23:59 PKT**. Submit:

1. [Accessible repository](https://github.com/momnakhan24/rahbar), with instructors
   added if private.
2. The URL of the successful **CD** run from step 4.
3. Docker Hub links showing that run's exact SHA tags:
   [API](https://hub.docker.com/r/aimwnoaim/rahbar-api/tags),
   [indexer](https://hub.docker.com/r/aimwnoaim/rahbar-indexer/tags),
   [UI](https://hub.docker.com/r/aimwnoaim/rahbar-ui/tags).
4. Committed `eval/results.json` and `eval/baseline.json`.

Run `python scripts/check_submission.py`, inspect warnings, confirm a clean Git
status and verify every intended commit is pushed. Review the implementation so
you can explain indexing separation, grounding, measurements and known limitations.
A green local check or CI run is not a substitute for successful hosted CD.

