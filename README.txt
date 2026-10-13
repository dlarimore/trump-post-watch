TRUMP POST CLOUD WATCHER  (runs on GitHub's computers - your PC can be off)
=====================================================================

What it does
  Every 5 min on weekdays 7am-4pm ET (every 15 min nights/weekends) GitHub runs watcher.py:
  - pulls Trump's latest Truth Social posts (falls back to trumpstruth.org if Truth Social blocks it)
  - scores each NEW post: Market Heat 0-10, Confrontation 0-5 + target, SHOCK yes/no
  - pushes Heat >= 3 (or any SHOCK) to the free "ntfy" app on your phone
  - appends every new post to alert_log.csv (the 9am/7pm runs can use this to rebuild the TPR indicator)
  Expect the phone buzz 5-10 minutes after he posts (GitHub's timer can run a few minutes late).

One-time setup (about 10 minutes)
  1. Phone: install "ntfy" (App Store / Google Play, free). Tap + and subscribe to a topic name
     only you know, e.g. yourname-mnq-x7k2q9  (anyone who knows the name can read it - keep it private).
     Android: in ntfy settings allow it to override Do Not Disturb for priority 5.
  2. Make a free account at github.com (if you don't have one).
  3. Link GitHub to Claude: claude.ai > Settings > Connectors > GitHub. Then tell Claude
     "GitHub is linked, my ntfy topic is ...". Claude creates the repo, uploads these files,
     stores the topic as a secret, and sends a test push.

  Manual alternative (no Claude):
     a. github.com > New repository > name: trump-post-watch > Public > Create
     b. "uploading an existing file" > drag in watcher.py, trump_heat.py, README.txt > Commit
     c. Add file > Create new file > name: .github/workflows/watch.yml > paste the contents of watch.yml > Commit
     d. Settings > Secrets and variables > Actions > New repository secret: NTFY_TOPIC = your topic
        (optional) Variables tab: PHONE_MIN_HEAT = 5 to only get HIGH/EXTREME/SHOCK
     e. Actions tab > enable workflows > "Trump post watch" > Run workflow > tick "test" > Run
        Your phone should buzz with "TRUMP SHOCK 8/10 vs IRAN (4/5) - TEST".

Why a PUBLIC repo: public repos get unlimited free GitHub Actions minutes. A private repo
would use up the 2,000 free minutes/month in about a week at this cadence. The code and the
post log are visible to anyone who finds the repo; your ntfy topic is NOT (it's a secret).

Phone alert format
  TRUMP SHOCK 8/10 vs EU/EUROPE/RUSSIA/PUTIN (4/5) - 10:08 AM ET   <- priority 5, siren
  TRUMP HIGH 6/10 - TARIFFS/CHINA - 2:14 PM ET                      <- priority 4
  Tapping the alert opens the post.

Turn it off: repo > Actions > Trump post watch > "..." > Disable workflow.
