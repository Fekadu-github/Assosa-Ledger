# Assosa Ledger — backend

A small shared API so the site-operations tool works from more than one
device/person instead of storing data locally only. Uses the same
pattern as your other project: **Render** for the API, **Supabase
Postgres** for the database.

## 1. Database

You can reuse your existing Supabase project (a new table set here won't
interfere with your other project's tables) or create a fresh Supabase
project — either works. Either way, grab the **Connection string** for
Supabase's Postgres (Project Settings -> Database -> Connection string,
"URI" format, remember to substitute your actual password). It looks like:

    postgresql://postgres:[YOUR-PASSWORD]@[HOST]:5432/postgres

## 2. Deploy the API to Render

1. Put this folder (`main.py`, `requirements.txt`, `create_user.py`) in
   its own GitHub repo, or a subfolder of an existing one.
2. In Render: New -> Web Service -> point it at that repo/folder.
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Environment variables to set on the Render service:
   - `DATABASE_URL` — the Supabase connection string from step 1
   - `SECRET_KEY` — any long random string (this signs login sessions —
     treat it like a password; changing it later logs everyone out)
   - `ALLOWED_ORIGINS` — the URL of wherever you host the frontend file,
     e.g. `https://your-ledger-site.netlify.app` (comma-separate if more
     than one). Using `*` works for testing but let's tighten this once
     it's live.
6. Deploy. Visit `https://<your-render-url>/health` — you should see
   `{"status": "ok"}`.

## 3. Create your login

From your own computer (not Render):

```bash
export DATABASE_URL="postgresql://postgres:...@...supabase.co:5432/postgres"
pip install sqlalchemy psycopg2-binary passlib[bcrypt]
python create_user.py
```

Answer the prompts — make yourself `role: owner`. Owners can create
further accounts later (for your friend, a geologist, etc.) either by
re-running this script or by logging into the app and it calling
`POST /auth/users` (the frontend doesn't have a UI for this yet — ask me
to add a simple "manage users" screen once you're ready for it).

## 4. Point the frontend at this backend

Open the Assosa Ledger HTML file in a browser, and on first load it'll
ask for a **Server URL** — enter your Render URL
(`https://your-service.onrender.com`, no trailing slash). It remembers
this on that device from then on.

## Roles, as currently enforced

- **owner** — full access, including creating new user accounts
- **gm** / **geologist** — can view and add/delete entries
- **viewer** — read-only

If you want finer-grained rules later (e.g. only geologists can mark
extraction entries "Verified"), that's a small addition on top of this
— just ask.
