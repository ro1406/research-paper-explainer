# Workshop Guide: Deploying an ADK Agent on GCP

## What this is

A research paper explainer powered by Google's **Agent Development Kit (ADK)**. You upload a PDF of any research paper, and the agent — backed by Gemini 2.5 Pro — explains concepts in plain language, automatically generates flowcharts using Graphviz, and creates illustrative diagrams via Gemini's image generation. The backend is a FastAPI app deployed on Cloud Run; the frontend is a plain HTML chat interface hosted on Firebase Hosting.

---

## Architecture

```
┌──────────────────────────┐         HTTPS POST /api/explain
│   Firebase Hosting       │──────────────────────────────────►┐
│   (static HTML/JS/CSS)   │                                    │
└──────────────────────────┘                                    ▼
                                              ┌─────────────────────────────┐
                                              │   Cloud Run (single instance)│
                                              │                             │
                                              │  FastAPI                    │
                                              │    └─ ADK Runner            │
                                              │         └─ Agent            │
                                              │              ├─ Gemini 2.5 Pro (text)
                                              │              ├─ generate_flowchart (Graphviz)
                                              │              └─ generate_diagram (Gemini image)
                                              │                             │
                                              │  InMemorySessionService     │
                                              │  InMemoryArtifactService    │
                                              └─────────────────────────────┘
```

---

## How ADK works (key concepts)

| Concept | What it does |
|---|---|
| **Agent** | Wraps a Gemini model with a system prompt and a list of callable tools |
| **Runner** | Executes agent turns: sends the user message, handles tool calls, streams events back |
| **SessionService** | Stores conversation history (list of Events) keyed by `(app, user, session)` |
| **ArtifactService** | Stores binary blobs (images, files) produced during a run, also keyed by session |

In this app, both services use **in-memory** implementations — no database or GCS bucket needed. State lives in the process, which is why we constrain Cloud Run to a single instance.

---

## The two tools

### `generate_flowchart`
- Takes a dict of `{node_name: hex_color}` and a list of `[source, destination]` edges
- Renders the graph using **Graphviz** (via the `graphviz` Python package + system binary)
- Saves the resulting PNG as an artifact in `InMemoryArtifactService`
- The agent decides when a flowchart would help — no hard-coded trigger

### `generate_diagram`
- Takes a detailed text prompt and the concept to explain
- Calls **Gemini Flash image generation** (`gemini-2.5-flash-image-preview`) to produce an illustration
- Saves the PNG as an artifact
- Used for non-flowchart visuals: architecture diagrams, process animations, conceptual illustrations

After each turn, the FastAPI handler reads any newly written artifacts out of `InMemoryArtifactService`, base64-encodes them, and returns them as data URLs in the JSON response. The frontend renders them inline — no separate image endpoint needed.

---

## Session strategy for this demo

```python
session_service  = InMemorySessionService()
artifact_service = InMemoryArtifactService()
```

Everything is in RAM. Sessions and artifacts are lost on container restart.

**This is fine for a workshop because:**
- Cloud Run is configured with `--min-instances=1 --max-instances=1`, so there is always exactly one container and it never scales down mid-demo
- No Firestore, no GCS, no IAM bindings to configure live

**For production you would swap in:**
| Component | Production equivalent |
|---|---|
| `InMemorySessionService` | `VertexAiSessionService` (Firestore-backed, built into ADK) |
| `InMemoryArtifactService` | `GcsArtifactService` (GCS-backed, built into ADK) |

---

## Deployment walkthrough

### Step 1 — Install the CLIs

**gcloud CLI:** follow the installer for your OS at https://cloud.google.com/sdk/docs/install

**Firebase CLI:**
```bash
npm install -g firebase-tools
```

---

### Step 2 — GCP project setup

1. Create a GCP project at [console.cloud.google.com](https://console.cloud.google.com)
2. Enable the **Vertex AI API** for the project (search "Vertex AI" in the console and click Enable)

> Cloud Run, Cloud Build, and Artifact Registry APIs will be enabled automatically the first time you run `gcloud run deploy`.

---

### Step 3 — Link a Firebase project

Firebase Hosting is used to serve the static frontend. Firebase projects and GCP projects are the same thing — you just add Firebase to your existing GCP project.

1. Go to [console.firebase.google.com](https://console.firebase.google.com)
2. Click **Add project** → choose **"Add Firebase to a Google Cloud project"**
3. Select your GCP project from the dropdown
4. Follow the prompts (you can skip Google Analytics)

---

### Step 4 — Authenticate and configure locally

```bash
# Log in to gcloud and set the active project
gcloud auth login
gcloud init   # choose your project when prompted
```

Open `.firebaserc` and replace the placeholder with your project ID:
```json
{
  "projects": {
    "default": "your-project-id"
  }
}
```

Then log in to Firebase:
```bash
firebase login
```

---

### Step 5 — Deploy the backend to Cloud Run

From the project root:

```bash
gcloud run deploy research-explainer \
  --source . \
  --region us-central1 \
  --min-instances=1 \
  --max-instances=1 \
  --allow-unauthenticated \
  --set-env-vars="GOOGLE_GENAI_USE_VERTEXAI=TRUE,GOOGLE_CLOUD_LOCATION=us-central1,GOOGLE_CLOUD_PROJECT=<YOUR_PROJECT_ID>"
```

Key flags explained:

| Flag | Why |
|---|---|
| `--source .` | Builds the container image from the local `Dockerfile` using Cloud Build — no need to push to a registry manually |
| `--min-instances=1` | Keeps one container warm at all times; in-memory sessions survive between requests |
| `--max-instances=1` | Prevents a second instance from spinning up (which would have its own empty session store) |
| `--allow-unauthenticated` | Public endpoint — fine for a workshop demo |
| `--set-env-vars` | Tells the Gemini SDK to use Vertex AI instead of the public API key path |

Copy the HTTPS URL printed at the end — you'll need it in the next step.

---

### Step 6 — Deploy the frontend to Firebase Hosting

Open `public/index.html` and replace the `BACKEND_URL` constant near the top of the `<script>` block with the Cloud Run URL from Step 5:

```js
// Before
const BACKEND_URL = "http://localhost:8000/api/explain";

// After
const BACKEND_URL = "https://YOUR-CLOUD-RUN-URL.run.app/api/explain";
```

Then deploy:

```bash
firebase deploy --only hosting
```

Firebase prints the public URL. That's the URL you share with the audience.

---

## Live demo flow

1. **Open the app URL** in the browser — the chat interface loads with the PDF upload zone visible
2. **Drag and drop a research paper PDF** onto the upload zone (or click to select) — the file name appears in the zone
3. **Type an initial question** in the text box — e.g. *"Explain the attention mechanism"* — and press Enter
4. **Watch the response** — the agent reads the paper, explains the concept, then calls `generate_flowchart` and/or `generate_diagram`; diagrams appear inline below the text
5. **Ask a follow-up** — the PDF is now locked (shown in the banner above the input) and the conversation continues; the agent remembers the full paper context
6. **Point out the session bar** — explain that this conversation is stored in memory on the single Cloud Run instance; if you pressed "New chat" a fresh session starts
7. **Show the Cloud Run console** — navigate to the Cloud Run service in GCP console, point out min/max instances = 1, show the logs streaming in real time

---

## Cleanup (avoiding ongoing costs)

The only resource that costs money while idle is the Cloud Run service running with `--min-instances=1`. Firebase Hosting is free at low traffic.

**Option A — Scale to zero (keeps the service, stops the always-on charge):**
```bash
gcloud run services update research-explainer \
  --region us-central1 \
  --min-instances=0
```
The service stays deployed and will cold-start (~3–5s) on the next request.

**Option B — Delete the Cloud Run service entirely:**
```bash
gcloud run services delete research-explainer --region us-central1
```

**Optionally delete the Artifact Registry repository** (stores the container image, ~$0.08/month):
```bash
gcloud artifacts repositories delete cloud-run-source-deploy \
  --location us-central1
```

Firebase Hosting can be left as-is — no charges for a static site at low traffic.
