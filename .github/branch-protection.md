# Branch Protection Setup

To prevent contributors from pushing directly to `main`, configure these settings
in GitHub repository settings (Settings > Branches > Branch protection rules):

## Required rules for `main`:

1. **Require a pull request before merging**
   - Required approving reviews: 1
   - Dismiss stale pull request approvals when new commits are pushed: ON
   - Require review from Code Owners: ON

2. **Require status checks to pass before merging**
   - Require branches to be up to date before merging: ON
   - Required checks: `lint`, `test`, `docker`

3. **Do not allow bypassing the above settings**

4. **Restrict who can push to matching branches**
   - Only allow repository admins

## How to apply (GitHub CLI):

```bash
gh api repos/NITI-Lab/SOUK/branches/main/protection \
  -X PUT \
  -f required_status_checks='{"strict":true,"contexts":["lint","test (3.12)","docker"]}' \
  -f enforce_admins=false \
  -f required_pull_request_reviews='{"required_approving_review_count":1,"dismiss_stale_reviews":true,"require_code_owner_reviews":true}' \
  -f restrictions=null
```
