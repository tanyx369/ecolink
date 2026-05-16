# Google Services Setup

Follow these steps before running EcoLink AI for the first time.

---

## 1. Create a Firebase project

1. Go to [console.firebase.google.com](https://console.firebase.google.com)
2. Click **Add project** → name it (e.g. `ecolink-ai`)
3. Disable Google Analytics if you prefer (not needed)

## 2. Enable Firestore

1. In your Firebase project → **Build → Firestore Database**
2. Click **Create database**
3. Choose **Native mode**
4. Pick a region (e.g. `asia-southeast1`)

## 3. Enable Firebase Authentication

1. **Build → Authentication → Get started**
2. Under **Sign-in providers** → add **Google**
3. Set your support email → Save

## 4. Get Firebase web config

1. **Project Settings → General → Your apps**
2. Click **Add app → Web** → register the app
3. Copy the `firebaseConfig` object → paste into `frontend/.env.local`

## 5. Enable Google Cloud APIs

In [Google Cloud Console](https://console.cloud.google.com) for the same project:

| API | Why |
|-----|-----|
| Vertex AI API | `text-embedding-004` embeddings |
| Generative Language API | Gemini 1.5 Pro |
| Maps JavaScript API | Ecosystem map |
| Cloud Run API | Backend deployment |
| Artifact Registry API | Docker image storage |

Enable each: **APIs & Services → Library → search → Enable**

## 6. Create a service account

1. **IAM & Admin → Service Accounts → Create Service Account**
2. Name: `ecolink-backend`
3. Grant roles:
   - **Vertex AI User**
   - **Firebase Admin SDK Administrator Service Agent**
   - **Cloud Datastore User** (for Firestore)
4. Click **Done**
5. Open the service account → **Keys → Add Key → JSON**
6. Download the JSON file → save as **`backend/service-account.json`**

> ⚠ Never commit `service-account.json` to git. It is already in `.gitignore`.

## 7. Get a Maps JavaScript API key

1. **APIs & Services → Credentials → Create Credentials → API key**
2. Restrict the key to **Maps JavaScript API**
3. Add HTTP referrer restrictions: `localhost:3000/*` and your production domain
4. Copy the key → set as `NEXT_PUBLIC_MAPS_API_KEY` in `frontend/.env.local`
   and `MAPS_API_KEY` in `backend/.env`

## 8. Get a Gemini API key (optional)

If you want to use an API key instead of ADC for Gemini:

1. [Google AI Studio](https://aistudio.google.com) → **Get API key**
2. Set as `GEMINI_API_KEY` in `backend/.env`

If you skip this, the backend will use Application Default Credentials (ADC) via the service account, which also works.

---

## Environment files checklist

### `backend/.env`
```
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_APPLICATION_CREDENTIALS=./service-account.json
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GEMINI_API_KEY=AIza...          # optional, uses ADC if omitted
MAPS_API_KEY=AIza...
```

### `frontend/.env.local`
```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_FIREBASE_API_KEY=AIza...
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID=your-project-id
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=your-project.appspot.com
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=123456789
NEXT_PUBLIC_FIREBASE_APP_ID=1:...:web:...
NEXT_PUBLIC_MAPS_API_KEY=AIza...
```
