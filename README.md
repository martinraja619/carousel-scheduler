# Carousel scheduler for @martinraja_etymology

Posts one carousel to Instagram at **9:17 am, 2:34 pm and 7:36 pm IST**, in order, from `schedule.csv`: 37 Noob on
2 Nov 2026 9:17 am through 127 Savour on 2 Dec 2026 9:17 am. Nothing posts before 2 Nov (runs before then find nothing
due). It runs on GitHub Actions, so your laptop can stay off. Every post is logged in `posted.csv` with its link.

| File | What it is |
|---|---|
| `carousels/<nnn-word>/` | The slides as 4:5 JPEGs (`01.jpg` … `08.jpg`), made by `build.py` |
| `schedule.csv` | One row per carousel: slot (IST), folder, number of slides, word, caption |
| `posted.csv` | Written by the scheduler after each post (slot, folder, media id, time, link) |
| `post.py` | Publishes through Instagram's official API (`post`, `check`, `status`) |
| `.github/workflows/post.yml` | When it runs: 15 min before each slot, plus two catch-up runs |

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

That's it. From the next slot on it posts by itself.

## Day to day
- **See what's posted:** open `posted.csv`, or run the workflow with mode **status**.
- **If a post fails:** GitHub emails you. The next catch-up run retries it automatically.
- **Pause everything:** **Actions → Post carousel → ⋯ → Disable workflow** (Enable to resume; any missed slots are
  then posted one per run, oldest first).
- **Token expiry:** a token made on 23 Oct 2026 stops working around 22 Dec 2026. Make a new one (step 1.5) and
  update the `IG_TOKEN` secret.

## Changing the queue (needs Claude or a terminal)
```
python build.py --first 37 --last 127 --start "2026-11-02 09:17"
```
rebuilds the JPEGs and `schedule.csv` from `F:\AED\carousels` (carousels already in `posted.csv` keep their place).
Then commit and push. To change the posting times, edit `SLOTS` in `build.py` **and** the cron lines in
`post.yml` (cron is UTC: IST minus 5:30, run 15 minutes early).

## Notes
- The repository is public, because Instagram fetches the images from a public link. Anyone who finds it can see
  upcoming carousels before they're posted.
- Same as posting by hand: slides 01–08, cropped to 4:5 the way the app does when you pick 4:5 (the centre
  1080×1350, i.e. 45 px of empty margin off the top and bottom), no filters.
- Caption: `<Word> னா என்ன? | Root words in Tamil | Word Power Made Easy in Tamil`. Words about a person (`PEOPLE`
  in `build.py`: Noob, Novice, Pantheist, Dictator, Benefactor, Mortician) get `னா யாரு?` instead.
- Before posting, `post.py` checks your last 10 posts for the same caption, so a retry never posts a carousel twice.
