# Sandbox Setup Guide

Documents the Colab sandbox built for Submission Spec §10.5.

**Status: complete.** The sandbox is live at the link below.

---

## Sandbox link

```
https://colab.research.google.com/github/datapiratepy/redrob-ranker/blob/main/notebooks/redrob_ranker_sandbox.ipynb
```

The README badge links to the same URL.

---

## Setup (completed)

All one-time steps are done:

| Step | Status |
|---|---|
| `data/sample_candidates.json` committed to repo | ✅ |
| `GITHUB_URL` set to `https://github.com/datapiratepy/redrob-ranker.git` in notebook | ✅ |
| `submission_metadata.yaml` fully filled (team, phone, URLs, compute, `reproduction_tested: true`) | ✅ |
| Repo public on GitHub | ✅ |

---

## Getting the Colab shareable link

Colab can open any notebook committed to a public GitHub repo using a
deterministic URL — **no manual upload required**.

**Your sandbox link will be:**

```
https://colab.research.google.com/github/datapiratepy/redrob-ranker/blob/main/notebooks/redrob_ranker_sandbox.ipynb
```

This URL is valid as long as the repo is public and the notebook is committed.

> Tip: test it in an incognito window to confirm it opens without login.

## Running the sandbox end-to-end (verification checklist)

1. Open the link above
2. Runtime → Run all  (`Ctrl+F9`)
3. Confirm each cell completes with a ✓ prefix
4. Expected output for 50-candidate sample:
   - pass 1: scored 50 candidates, recalled N (a few seconds)
   - pass 2: reasoning for min(N, 100) candidates, verification clean
   - Top-10 table displayed
   - Score distribution chart displayed
   - CSV download triggered
5. Confirm the validator cell prints `✓ VALIDATOR PASS` (or manual check passes)

Total runtime on Colab CPU: **under 60 seconds**.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Clone failed` | Ensure repo is **public**, not private |
| `sample_candidates.json not found` | Upload it via Files panel (Step 4 instructions shown in notebook) |
| `ModuleNotFoundError: src` | Make sure REPO_DIR is in sys.path — re-run Step 2 cell |
| `FileNotFoundError: config/jd_signals.yaml` | Clone failed silently — re-check GITHUB_URL in Step 2 |
| `reasoning verification failed` | Do not modify scoring/reasoning source — report as a bug |

---

## Alternative: Colab with manual file upload

If you prefer not to commit `sample_candidates.json` to GitHub:

1. Open the notebook link
2. In Step 4, use the Files panel to upload `sample_candidates.json`
3. Re-run Step 4 — it detects the uploaded file automatically
4. Continue from Step 5

The notebook is designed to handle both paths.

