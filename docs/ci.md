# CI Gate — Skill Integrity Check

## Purpose

This gate protects the repository's engineering assets on every pull request.
It ensures that:

1. The portable Skill definition (`skills/cloud-operations-analysis/SKILL.md`)
   has not been deleted or corrupted.
2. The hot context bundle (`CLAUDE.md`) has not been stripped of its
   `## Repository Context` section, which holds all repository-specific
   assumptions separated by K 5.D.2.

Without this gate, a pull request could silently degrade the Engineering Skill
to an unusable state while passing all other CI checks.

---

## Rule Enforced

The CI job `validate` in `.github/workflows/skill-integrity.yml` fails (exit 1)
if **any** of the following is true:

| # | Condition | Checked file |
|---|---|---|
| 1 | `skills/cloud-operations-analysis/SKILL.md` does not exist | SKILL.md |
| 2 | `CLAUDE.md` does not exist | CLAUDE.md |
| 3 | `SKILL.md` does not begin with a YAML frontmatter opening delimiter (`---`) | SKILL.md |
| 4 | The YAML frontmatter block is unclosed (no second `---`) | SKILL.md |
| 5 | Frontmatter is missing the `name` field | SKILL.md |
| 6 | Frontmatter is missing the `description` field | SKILL.md |
| 7 | Frontmatter is missing the `compatibility` field | SKILL.md |
| 8 | The body after the frontmatter contains no non-whitespace content | SKILL.md |
| 9 | `CLAUDE.md` does not contain `## Repository Context` | CLAUDE.md |

The gate exits 0 (success) only when all nine conditions are satisfied.

All validation logic lives in `scripts/ci/validate-skill.sh`. The workflow YAML
is a thin runner — it checks out the repository and calls the script.

---

## How to Test Locally

Run the script from the repository root:

```bash
bash scripts/ci/validate-skill.sh
```

Expected output on a clean repository:

```
=== Skill Integrity Check ===
SKILL file : skills/cloud-operations-analysis/SKILL.md
CLAUDE file: CLAUDE.md

PASS: SKILL.md exists at skills/cloud-operations-analysis/SKILL.md
PASS: CLAUDE.md exists
PASS: SKILL.md has YAML frontmatter opening delimiter
PASS: SKILL.md frontmatter closing delimiter found at line 33
PASS: Frontmatter contains 'name' field
PASS: Frontmatter contains 'description' field
PASS: Frontmatter contains 'compatibility' field
PASS: SKILL.md body is not empty
PASS: CLAUDE.md contains '## Repository Context' section

=== Result: PASSED (all checks passed) ===
```

To test a failure, temporarily remove a required frontmatter field from
`skills/cloud-operations-analysis/SKILL.md` and re-run. The script will print
`FAIL:` lines and exit 1. Restore the field to return to a passing state.

For inline help:

```bash
bash scripts/ci/validate-skill.sh --help
```

---

## GitHub Branch Protection — Admin Step

To make this gate **required** (blocking merge), a repository admin must
configure branch protection after the first CI run completes:

1. Go to **Settings → Branches** in the GitHub repository.
2. Click **Edit** (or **Add rule**) for the `master` branch.
3. Enable **Require status checks to pass before merging**.
4. Search for and select the check named **`Validate engineering assets`**.
5. Enable **Require branches to be up to date before merging**.
6. Click **Save changes**.

Until these steps are completed, the workflow runs on every PR but does not
block merging. The gate is advisory only until branch protection is applied.

> **Note:** The status check name that appears in GitHub is the `name:` field
> of the job in the workflow — `Validate engineering assets`. Use this exact
> string in the search box in step 4.

---

## Known Limitations

| Limitation | Detail |
|---|---|
| YAML is not fully parsed | The frontmatter validator checks for field key presence using `grep`, not a YAML parser. A syntactically invalid YAML value for a present key will pass the check. This is intentional: installing a YAML parser in CI adds a dependency with its own failure modes. A malformed value is caught during Skill loading, not at this gate. |
| Body check is presence-only | The check confirms the body is non-empty but does not validate its structure (headings, section count, etc.). Structural validation would require a domain-specific parser and is out of scope for this gate. |
| Gate does not run on push to master | The workflow triggers on `pull_request` only. A direct push to `master` bypasses the gate. Branch protection (admin step above) is required to prevent this. |
| Workflow file can be deleted in a PR | A PR that deletes `.github/workflows/skill-integrity.yml` will not trigger the check at all. The gate does not protect itself. Mitigation: add the workflow file to a `CODEOWNERS` rule requiring a repository admin review. |
| `[skip ci]` in commit message | GitHub Actions skips all workflows when `[skip ci]` or `[no ci]` appears in the commit message. When branch protection is configured with Required status checks, GitHub still blocks the merge if the check has never passed — this provides a partial mitigation. |
| Script requires bash 4+ | The script uses `(( ))` arithmetic and `[[ ]]` conditionals. The GitHub-hosted `ubuntu-latest` runner ships with bash 5. Local macOS users running the default system bash (3.2) should install a current bash via their package manager. |

---

## Files

| File | Purpose |
|---|---|
| `.github/workflows/skill-integrity.yml` | CI workflow — triggers on PR; calls the script |
| `scripts/ci/validate-skill.sh` | All validation logic; readable; commented; exit codes documented |
| `docs/ci.md` | This file |
