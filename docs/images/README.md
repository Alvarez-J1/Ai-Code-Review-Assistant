# Screenshot Capture Plan

Capture these PNG files after running the app with seeded demo data:

- `new-review.png`: the Paste Diff tab on the New Review screen
- `github-review.png`: the GitHub PR tab with a valid demo PR URL entered
- `findings.png`: a GitHub-origin review detail page with severity/category/file filters visible
- `recent-reviews.png`: the Recent Reviews page showing both seeded demo sessions

Suggested local flow:

```powershell
docker compose up --build
docker compose --profile seed run --rm seed-demo
```

Then open `http://localhost:3000` and capture the screens above.

No placeholder images are committed here; only real screenshots should be added.
