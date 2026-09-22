# Assosa Ledger

Site-operations and commission-tracking tool for the gold mining project
(equipment, crews/commissions, extraction, gold custody, compliance,
security log, budget, and personal compensation tracking).

## Structure

```
AssosaLedger/
├── backend/          FastAPI app — deploy to Render, database on Supabase
│   ├── main.py
│   ├── requirements.txt
│   ├── create_user.py
│   └── README.md
├── frontend/         Single-file web app — deploy to Netlify (also installs on phones as an app, see below)
│   └── index.html
└── DEPLOYMENT.md     Full step-by-step: Supabase → Render → Netlify
```

## Quick start

Follow **DEPLOYMENT.md** top to bottom — it covers all three services in
order and ends with a working sign-in you can use from a PC and a phone
at the same time.

## Getting this on a phone (Android + iPhone), for free, today

Once `frontend/index.html` is deployed to Netlify, open that Netlify URL
on a phone's browser and use **"Add to Home Screen"** (Chrome on Android:
menu → Add to Home Screen. Safari on iPhone: Share button → Add to Home
Screen). This installs it as an actual app icon, works full-screen, and
costs nothing — no app store, no developer account, on either platform.

For a real Android APK / iOS app-store build, see the note in
`DEPLOYMENT.md` on PWABuilder — free tool, but be aware Apple requires a
paid ($99/year) developer account for any real App Store or TestFlight
distribution; there's no way around that on Apple's platform. Android
has a genuinely free path (a side-loadable APK, no store needed).
