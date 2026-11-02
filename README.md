# Carousel scheduler for @martinraja_etymology

Posts one carousel to Instagram at **9:17 am, 2:34 pm and 7:36 pm IST**, in order, from `schedule.csv`: 37 Noob on
2 Nov 2026 at 12:35 pm (moved from 9:17 am, which passed before the first run), then 38 Novice at 2:34 pm through
127 Savour on 2 Dec 2026 9:17 am. It runs on GitHub Actions, so your laptop can stay off. Every post is logged in `posted.csv` with its link.

| File | What it is |
|---|---|
| `carousels/<nnn-word>/` | The slides as 4:5 JPEGs (`01.jpg` … `08.jpg`), made by `build.py` |
| `schedule.csv` | One row per carousel: slot (IST), folder, number of slides, word, caption |
| `posted.csv` | Written by the scheduler after each post (slot, folder, media id, time, link) |
| `post.py` | Publishes through Instagram's official API (`post`, `check`, `status`) |
| `.github/workflows/post.yml` | The job. Started 5–24 min before each slot by cron-job.org (step 4), by any push that changes `schedule.csv`, and by GitHub's own schedule as a late backup |

## One-time setup (about 30 minutes)

### 1. Get an Instagram access token (you do this; don't paste the token into chat)
Meta renames these menus now and then; if a label below doesn't match, tell Claude what you see.

1. Go to <https://developers.facebook.com/apps>, log in with Facebook and click **Create app**.
2. Use case: **Manage messaging & content on Instagram**. If it isn't listed, choose **Other**, then app type
   **Business**. Name it "Carousel scheduler" and finish.
3. Open **Instagram → API setup with Instagram login** (it may sit under **Use cases → Customize**).
4. Under **Generate access tokens**, click **Add account** and log in as **@martinraja_etymology**. Allow the
   permissions it asks for (it needs `instagram_business_basic` and `instagram_business_content_publish`).
   - If it says the account must be a tester first: **App roles → Roles → Add people → Instagram Tester**, enter
     `martinraja_etymology`, then accept the invite at instagram.com → **Settings → Apps and websites → Tester
     invites**. Then go back to step 4.
5. Click **Generate token** next to the account and copy the token. It lasts **60 days**.

### 2. Store the token in GitHub
In the repository: **Settings → Secrets and variables → Actions → New repository secret**. Name: `IG_TOKEN`.
Secret: paste the token. **Add secret**.

### 3. Test it without posting
**Actions → Post carousel → Run workflow →** mode **check** → **Run workflow**. A green tick means the token works,
GitHub is serving the images, and Instagram accepted the next carousel (it is *not* published). If it goes red, open
the run, copy the error and show it to Claude.

### 4. Exact-time triggers (cron-job.org, free)
GitHub starts its own scheduled runs 4–7 hours late (seen 23 Oct–2 Nov 2026), so the exact times come from
cron-job.org: at 9:12, 14:12 and 19:12 it asks GitHub to start the workflow, which happens within a minute, and
`post.py` waits for the exact minute of the slot (up to 40 minutes). It never posts early, so an extra or early trigger is harmless.

**a. A GitHub token that can only start this workflow** (you make it; don't paste it into chat)
1. Open <https://github.com/settings/personal-access-tokens/new> (Fine-grained token).
2. Name: `cron-job.org carousel trigger`. Expiration: **Custom**, 31 Dec 2026 (the queue ends 2 Dec).
3. Repository access: **Only select repositories** → `martinraja619/carousel-scheduler`.
4. Permissions → Repository permissions → **Actions: Read and write**. Nothing else (Metadata: Read-only is added
   by itself).
5. **Generate token** and copy it (it starts with `github_pat_`).

**b. One job on cron-job.org**
1. Sign up at <https://console.cron-job.org/signup> and log in.
2. **Create cronjob**:
   - Title: `Carousel trigger`
   - URL: `https://api.github.com/repos/martinraja619/carousel-scheduler/actions/workflows/post.yml/dispatches`
   - Execution schedule: **Custom**: every day of the month, every weekday, every month, hours **9, 14 and 19**,
     minute **12**. Time zone **Asia/Kolkata** (if the job has no time-zone box, set it under the account's
     **Settings**). That's 9:12, 14:12 and 19:12; each run waits for its slot (9:17, 14:34, 19:36).
   - **Advanced** tab → Request method **POST**, these two headers, and this request body (type it with straight
     quotes):

     | Header | Value |
     |---|---|
     | `Accept` | `application/vnd.github+json` |
     | `Authorization` | `Bearer ` followed by the token (one space after Bearer) |

     Body: `{"ref":"main","inputs":{"mode":"post"}}`. cron-job.org then offers to add a JSON `Content-Type` header:
     accept it. (Typing `X-GitHub-Api-Version` or a second `Content-Type` by hand got a 400 on 2 Nov 2026.)
   - Notifications: tick **execution fails**. Then **Create**.
(Cloning a second job gave "possibly malformed job" on 2 Nov 2026, so it's one job with three times.)

**c. Test:** open one job and click **Test run**. A response of **204** (or 200) means it works, and a new run
appears under **Actions** with event `workflow_dispatch`. It posts nothing unless a slot is under 40 min away, and
then it posts at that slot's exact minute.

That's it. From the next slot on it posts by itself.

## Day to day
- **See what's posted:** open `posted.csv`, or run the workflow with mode **status**.
- **If a post fails:** GitHub emails you, and cron-job.org emails you if it couldn't start the workflow. The next
  trigger retries it (missed carousels post one per run, oldest first).
- **Post something at an odd time:** change its `slot` in `schedule.csv` to a time under 40 minutes away and push. The
  push starts a run that posts it at that minute.
- **Pause everything:** **Actions → Post carousel → ⋯ → Disable workflow** (Enable to resume; any missed slots are
  then posted one per run, oldest first).
- **Token expiry:** a token made on 23 Oct 2026 stops working around 22 Dec 2026. Make a new one (step 1.5) and
  update the `IG_TOKEN` secret. The cron-job.org token (step 4a) runs out on 31 Dec 2026.

## Changing the queue (needs Claude or a terminal)
```
python build.py --first 37 --last 127 --start "2026-11-02 14:34"
```
rebuilds the JPEGs and `schedule.csv` from `F:\AED\carousels` (carousels already in `posted.csv` keep their place).
Then commit and push. To change the posting times, edit `SLOTS` in `build.py`, the cron-job.org job's
hours and minute (each run must start under 40 minutes before its slot) **and** the backup cron lines in `post.yml` (cron is UTC: IST minus 5:30).

## Notes
- The repository is public, because Instagram fetches the images from a public link. Anyone who finds it can see
  upcoming carousels before they're posted.
- Same as posting by hand: slides 01–08, cropped to 4:5 the way the app does when you pick 4:5 (the centre
  1080×1350, i.e. 45 px of empty margin off the top and bottom), no filters.
- Caption: `<Word> னா என்ன? | Root words in Tamil | Word Power Made Easy in Tamil`. Words about a person (`PEOPLE`
  in `build.py`: Noob, Novice, Pantheist, Dictator, Benefactor, Mortician) get `னா யாரு?` instead.
- Before posting, `post.py` checks your last 10 posts for the same caption, so a retry never posts a carousel twice.
