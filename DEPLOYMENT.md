# Assosa Ledger — full deployment runbook (Supabase + Render + Netlify)

This is everything in one place to get the shared, multi-device version
of the tool live. It uses the same three services you already know from
your other project:

- **Supabase** — the database (Postgres)
- **Render** — hosts the backend API (`main.py`)
- **Netlify** — hosts the frontend (`assosa-ledger-frontend.html`)

Do the three steps in this order — each one needs something from the
step before it.

---

## Step 1 — Supabase (the database)

1. Go to [supabase.com](https://supabase.com) and either use your
   existing project or create a new one (New Project → give it a name
   like `assosa-ledger` → set a database password you'll remember →
   choose a region close to Ethiopia if offered, e.g. an EU region →
   Create).
2. Once it's ready: **Project Settings → Database → Connection string**.
   Choose the **URI** tab. Copy it — it looks like:
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.xxxxxxxxxxxx.supabase.co:5432/postgres
   ```
3. Replace `[YOUR-PASSWORD]` with the actual database password you set
   in step 1. Save this full string somewhere — it's your `DATABASE_URL`
   for the next step.

You don't need to create any tables yourself — the backend creates them
automatically the first time it starts up.

---

## Step 2 — Render (the backend API)

1. Put the backend files in a GitHub repo (a new small repo is
   cleanest): `main.py`, `requirements.txt`, `create_user.py`.
2. In Render: **New → Web Service** → connect that repo.
3. Settings:
   - **Build command**: `pip install -r requirements.txt`
   - **Start command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Instance type**: free tier is fine to start
4. **Environment variables** (Render dashboard → Environment):
   | Key | Value |
   |---|---|
   | `DATABASE_URL` | the full Supabase connection string from Step 1 |
   | `SECRET_KEY` | any long random string, e.g. generate one with `openssl rand -hex 32` |
   | `ALLOWED_ORIGINS` | your Netlify URL once you have it in Step 3 (use `*` for now, tighten later) |
5. Deploy. When it's live, open `https://<your-render-url>/health` in a
   browser — you should see `{"status":"ok"}`. If you see an error
   instead, check the Render logs tab; the most common cause is
   `DATABASE_URL` not matching what Supabase gave you.

---

## Step 3 — Netlify (the frontend)

The frontend is a single HTML file — Netlify can host it with no build
step at all.

1. Go to [netlify.com](https://netlify.com) → **Add new site → Deploy
   manually** (the drag-and-drop option).
2. Put `assosa-ledger-frontend.html` into an empty folder, and **rename
   it to `index.html`** inside that folder (Netlify serves `index.html`
   as the site's homepage automatically).
3. Drag that folder onto the Netlify deploy page.
4. Netlify gives you a URL like `https://random-name-123.netlify.app`.
   That's your app's address from now on — bookmark it, put it on your
   phone's home screen.
5. **Go back to Render** and update `ALLOWED_ORIGINS` to this exact
   Netlify URL (no trailing slash), so the backend only accepts requests
   from your actual site. Redeploy the Render service after changing it.

If you'd rather connect a GitHub repo to Netlify instead of drag-and-drop
(so future updates auto-deploy), that works too — same idea, just point
Netlify's "Publish directory" at the folder containing `index.html`.

---

## Step 4 — Create your login

From your own computer (not Render, not Netlify):

```bash
export DATABASE_URL="postgresql://postgres:...@....supabase.co:5432/postgres"
pip install sqlalchemy psycopg2-binary passlib[bcrypt]
python create_user.py
```

Answer the prompts. Set your role to `owner`. This is the account
you'll actually sign in with.

---

## Step 5 — Sign in and verify end-to-end

1. Open your Netlify URL.
2. On the sign-in screen, enter:
   - **Server URL**: your Render URL (e.g. `https://assosa-api.onrender.com`)
   - **Username / password**: what you just created in Step 4
3. You should land on the Overview screen. Add a test entry in any
   module (e.g. one piece of equipment), then open the same Netlify URL
   on your phone and sign in the same way — you should see that same
   entry there too. That confirms the shared database is working across
   devices.

---

## Adding your friend / geologists later

There's no "create account" button in the app yet (only you, as
`owner`, can create logins, on purpose). For now, run `create_user.py`
again for each new person, using the same `DATABASE_URL`. When you're
ready, ask me to add a simple "manage users" screen inside the app
itself so you don't need to keep running the script by hand.

---

## Step 6 — Getting it onto Android and iPhone

There are two tiers here — be clear-eyed about which one is actually free
on each platform, because it's not symmetric.

### Tier 1 — free on both platforms, works today, no app store at all

Once the frontend is live on Netlify, open that URL on the phone's
browser and add it to the home screen:

- **Android (Chrome)**: menu (⋮) → "Add to Home Screen" / "Install app"
- **iPhone (Safari)**: Share button → "Add to Home Screen"

This puts a real icon on the home screen, opens full-screen with no
browser bar, and works offline for the interface itself (it still needs
a connection to load/save data, same as the web version). **This costs
nothing on either platform and needs no developer account.** For a small
team, this is genuinely enough — it's what most internal company tools
actually use rather than a "real" app-store app.

### Tier 2 — an installable APK / a real App Store listing

If you specifically want a `.apk` file or an App Store listing:

- **[PWABuilder.com](https://www.pwabuilder.com)** (free, made by Microsoft) —
  paste in your Netlify URL, and it packages the site into an Android
  package and an iOS/Xcode project for you, free of charge.
- **Android**: the resulting `.apk` can be shared and installed directly
  on any Android phone with no Play Store account and no fee at all
  (the phone will ask to allow "install from unknown sources" once).
  Publishing it *on* the Play Store instead is a one-time $25 Google
  Play developer fee, optional.
- **iPhone**: this is the one place there's no free option. Apple does
  not allow installing an app outside the App Store (no side-loading
  equivalent to Android) except through their official developer
  program, which costs **$99/year** — required for TestFlight beta
  distribution or a real App Store listing, no way around it. This is
  an Apple platform rule, not a limitation of PWABuilder or this app.

**Recommendation**: use Tier 1 (Add to Home Screen) for both platforms
to start — it's free, instant, and likely all you need for a small
team. Only look at PWABuilder + the Apple fee if you specifically need
an official App Store presence later.

---

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Render `/health` shows an error | `DATABASE_URL` is wrong, or missing the password substitution |
| Sign-in says "Could not reach that server" | Server URL typed wrong, or Render service is asleep (free tier sleeps after inactivity — wait ~30s and retry) |
| Sign-in succeeds but says "Session expired" immediately | `SECRET_KEY` changed after you logged in once — sign in again |
| Entries added on phone don't show on PC | Both devices must use the **same** Server URL — check for typos, especially `http` vs `https` |
| Netlify site loads but login form does nothing | Open the browser console (F12) — if it shows a CORS error, `ALLOWED_ORIGINS` on Render doesn't match your Netlify URL exactly |

---

## What you should already have on hand for this

- `main.py`, `requirements.txt`, `create_user.py` — the backend (from earlier in this conversation)
- `assosa-ledger-frontend.html` — the frontend (from earlier in this conversation)

If any of those got lost, tell me and I'll regenerate them.
