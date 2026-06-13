# Sandbox Setup Guide

How to publish the Colab notebook and obtain a shareable link for the
hackathon submission portal (Submission Spec §10.5).

---

## Prerequisites

- GitHub repository pushed and **public** (required for Colab to open it)
- `sample_candidates.json` in the repo under `data/sample_candidates.json`
  OR committed to a publicly accessible path

---

## One-time setup (do this before submitting)

### 1. Add sample data to the repo

Copy the hackathon bundle's `sample_candidates.json` into the repo so Colab
can fetch it without a manual upload:

```bat
cd redrob-ranker
mkdir data
copy ..\sample_candidates.json data\sample_candidates.json
git add data/sample_candidates.json
git commit -m "add sample data for Colab sandbox"
git push
```

### 2. Update the two placeholders in the notebook

Open `notebooks/redrob_ranker_sandbox.ipynb` and replace:

| Placeholder | Replace with |
|---|---|
| `https://github.com/YOUR_USERNAME/redrob-ranker.git` | Your actual GitHub clone URL |
| `https://raw.githubusercontent.com/YOUR_USERNAME/redrob-ranker/main/data/sample_candidates.jsonl` | Raw URL to `data/sample_candidates.json` converted to JSONL — or just rely on the JSON conversion path which works automatically once the file is in the repo |

Commit and push the updated notebook:

```bat
git add notebooks/redrob_ranker_sandbox.ipynb
git commit -m "sandbox: set actual github url in colab notebook"
git push
```

### 3. Fill the remaining TODOs in submission_metadata.yaml

```yaml
team_name: "your-team-name"
primary_contact:
  phone: "+91-XXXXXXXXXX"
github_repo: "https://github.com/YOUR_USERNAME/redrob-ranker"
sandbox_link: "https://colab.research.google.com/github/YOUR_USERNAME/redrob-ranker/blob/main/notebooks/redrob_ranker_sandbox.ipynb"
compute:
  platform: "Windows 11 laptop"
  cpu_cores: <your core count>
  python_version: "3.11.x"
  os: "Windows 11"
reproduction_tested: true   # flip after running rank.py locally
```

---

## Getting the Colab shareable link

Colab can open any notebook committed to a public GitHub repo using a
deterministic URL — **no manual upload required**.

**Your sandbox link will be:**

```
https://colab.research.google.com/github/YOUR_USERNAME/redrob-ranker/blob/main/notebooks/redrob_ranker_sandbox.ipynb
```

Replace `YOUR_USERNAME` with your GitHub username. That's it — this URL is
valid immediately once the repo is public and the notebook is committed.

> Tip: test it in an incognito window to confirm it opens without login.

### Making the link "open in Colab" from the README

Add this badge to `README.md`:

```markdown
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/YOUR_USERNAME/redrob-ranker/blob/main/notebooks/redrob_ranker_sandbox.ipynb)
```

---

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

---

## After publishing

Update `submission_metadata.yaml`:

```yaml
sandbox_link: "https://colab.research.google.com/github/YOUR_USERNAME/redrob-ranker/blob/main/notebooks/redrob_ranker_sandbox.ipynb"
```

Commit and push. The sandbox requirement (§10.5) is now satisfied.
