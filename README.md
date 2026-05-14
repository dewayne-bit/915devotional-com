# 915devotional.com — Site Guide

A static website for the daily 9:15 AM devotional. No monthly hosting cost beyond what you're already paying GoDaddy. Easy to maintain.

---

## What's in this folder

| File | What it does |
|------|--------------|
| `index.html` | Homepage — hero, "Join Zoom" button, latest devotional, recent grid, prayer CTA |
| `devotionals.html` | Full archive page with search |
| `prayer.html` | Prayer request form |
| `styles.css` | All the visual styling |
| `script.js` | Loads devotionals + handles search & form |
| **`devotionals.json`** | **The file you'll edit most — all devotionals + Zoom info live here** |
| `README.md` | This file |

---

## Step 1: Set the Zoom meeting info (one-time)

Open **`devotionals.json`** and update the `zoom` block at the top:

```json
"zoom": {
  "joinUrl": "https://us02web.zoom.us/j/12345678901?pwd=AbCdEf",
  "meetingId": "123 4567 8901",
  "passcode": "morning",
  "scheduleNote": "Mon–Thu at 9:15 AM ET"
}
```

- **`joinUrl`** — the full Zoom URL with passcode embedded. In Zoom, find your meeting → "Copy Invitation" → grab the link that starts with `https://...zoom.us/j/...?pwd=...`. That's the magic link that auto-joins without typing a passcode.
- **`meetingId`** — what shows on the homepage under the button.
- **`passcode`** — same.

Save the file. The button on the homepage now joins your meeting in one click.

---

## Step 2: Add a new devotional after each session

This is the daily/weekly task. It takes 2 minutes.

**1.** After the Zoom session, upload the recording to your YouTube channel (or unlisted is fine — embeds still work). Copy the YouTube video ID from the URL:

- `https://www.youtube.com/watch?v=`**`6G7a44B6rwg`** ← that part
- or `https://youtu.be/`**`6G7a44B6rwg`**

**2.** Open `devotionals.json`. At the **top** of the `devotionals` array, paste a new entry. Newest first — that's how the site decides what's "Latest."

```json
{
  "date": "2026-05-08",
  "title": "Trust in the Lord with All Your Heart",
  "scriptures": ["Proverbs 3:5-6", "Psalm 37:5"],
  "youtubeId": "6G7a44B6rwg",
  "summary": "What does it look like to actually trust God when the path forward feels uncertain?"
}
```

**Field tips:**
- `date` — `YYYY-MM-DD` format. Used to sort and to show "Wed, May 8, 2026" on the card.
- `title` — short, descriptive.
- `scriptures` — an array. Add as many as you covered.
- `youtubeId` — just the ID, not the full URL.
- `summary` — optional. 1–2 sentences. Skip it by leaving it as `""` if you'd rather not.

**3.** Save the file. Re-upload it to your GoDaddy host (see Step 4). Done — the new devotional is live.

---

## Step 3: Connect the prayer form (one-time)

The prayer form needs a tiny free service called **Formspree** to email you submissions. Setup takes 5 minutes.

1. Go to **https://formspree.io/** and sign up (the free plan allows 50 submissions/month — plenty for a devotional site; upgrade only if you outgrow it).
2. Click **+ New Form**. Set the email to **dewayne@shingleusa.com**.
3. Formspree will give you a form endpoint that looks like: `https://formspree.io/f/xnqkpqab`
4. Copy the part after `/f/` — that's your **form ID** (e.g. `xnqkpqab`).
5. Open `prayer.html`, find this line:

   ```html
   <form id="prayer-form" action="https://formspree.io/f/YOUR_FORM_ID" method="POST">
   ```

   Replace `YOUR_FORM_ID` with your actual form ID. Save.

6. The first time someone submits, Formspree will email you to confirm the address. Click the confirmation link and you're set.

That's it — prayer requests now arrive in your inbox with subject "New prayer request from 915devotional.com."

> **Cost note for Nikki:** Formspree free tier = $0/month. Only upgrade if you exceed 50 submissions/month, which is unlikely for a devotional site.

---

## Step 4: Upload to GoDaddy

You already own `915devotional.com` through GoDaddy. To get the site online:

### Option A — GoDaddy Web Hosting (cPanel / File Manager)

If you have GoDaddy's "Web Hosting" or "Deluxe Hosting" plan:

1. Log in to GoDaddy → **My Products** → click **Manage** next to your hosting plan.
2. Click **cPanel Admin** (or **File Manager** directly).
3. Navigate to the **`public_html`** folder.
4. **Delete** the default placeholder files inside (usually `index.html` or a "Coming Soon" page).
5. **Upload** every file from this folder (`index.html`, `devotionals.html`, `prayer.html`, `styles.css`, `script.js`, `devotionals.json`, `README.md`) into `public_html`.
6. Visit **https://915devotional.com** — it should be live.

### Option B — You don't have hosting yet, only the domain

You have two cheap-or-free choices:

**Cheapest: free static hosting + point your domain at it.**
- Upload these files to **Netlify** (drag-and-drop at https://app.netlify.com/drop) or **Cloudflare Pages**. Both are free for sites this size.
- Then in GoDaddy, point your domain's DNS at the Netlify/Cloudflare URL. They have step-by-step guides.
- $0/month. Faster than GoDaddy hosting.

**Easiest: buy GoDaddy's basic Web Hosting (~$7/mo).**
- Use Option A above.

> **Recommendation:** Netlify is genuinely free, faster, and Nikki will appreciate the $0/month bill. Worth the 15 minutes of DNS setup.

### Updating later

When you add a new devotional (Step 2 above), you only need to re-upload the **`devotionals.json`** file. That's the only file that changes day-to-day.

---

## Testing locally before uploading

You can preview the site on your own computer before pushing changes live:

1. Open Terminal in this folder.
2. Run: `python3 -m http.server 8080`
3. Visit **http://localhost:8080** in your browser.

(The reason for the local server: browsers won't load `devotionals.json` if you just double-click `index.html` due to security rules. The 1-line server fixes that.)

Stop with `Ctrl+C` when done.

---

## What's NOT included (yet) — easy adds later

These would all be small follow-on projects if you want them:

- **Email newsletter signup** — collect email addresses to notify people of new devotionals (Mailchimp free tier handles this).
- **Public prayer wall** — show approved prayer requests publicly with reactions like "praying for you."
- **Podcast / RSS feed** — auto-distribute audio versions to Apple Podcasts and Spotify.
- **Login + admin panel** — instead of editing JSON, fill out a web form to add a devotional.
- **Calendar integration** — show today's date highlighted, link to "add to my calendar."

When you're ready for any of these, ask and we'll bolt it on.

---

## Quick troubleshooting

- **"Site looks unstyled / images missing"** → Make sure all files are in the same folder when uploaded.
- **"Devotionals don't show up"** → Check that `devotionals.json` is valid JSON. If unsure, paste it into https://jsonlint.com to validate.
- **"Zoom button doesn't work"** → You haven't filled in the `joinUrl` in `devotionals.json` yet. See Step 1.
- **"Prayer form does nothing"** → Formspree isn't connected yet. See Step 3.

---

*"Therefore everyone who hears these words of mine and puts them into practice is like a wise man who built his house on the rock."* — Matthew 7:24
