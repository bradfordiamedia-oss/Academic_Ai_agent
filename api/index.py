"""Vercel serverless entrypoint.

Vercel only runs short-lived request/response functions — it cannot host the
actual Academic Agent app, which is a Streamlit server (persistent process,
WebSocket connection, session state). This endpoint is an honest landing page
that explains that and points to where the real app runs.
"""
from http.server import BaseHTTPRequestHandler

PAGE = """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Academic Agent</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 640px; margin: 4rem auto; padding: 0 1rem; line-height: 1.5; }
    code { background: #f2f2f2; padding: 0.1rem 0.35rem; border-radius: 4px; }
  </style>
</head>
<body>
  <h1>Academic Agent</h1>
  <p>
    This project's app is a <strong>Streamlit</strong> app (Thesis Qualification
    Checker + Exam Auto-Grader). Streamlit needs a persistent server process,
    which Vercel's serverless platform doesn't provide &mdash; so this page is a
    placeholder, not the live app.
  </p>
  <p>Run it yourself:</p>
  <ul>
    <li>Locally: clone the repo, <code>pip install -r requirements.txt</code>, then <code>streamlit run app.py</code></li>
    <li>Hosted: deploy the <code>Academic_Agent</code> folder on
      <a href="https://share.streamlit.io">Streamlit Community Cloud</a> (see the
      project README for exact steps)</li>
  </ul>
  <p>
    Source: <a href="https://github.com/bradfordiamedia-oss/Bradford/tree/main/Academic_Agent">
    bradfordiamedia-oss/Bradford/Academic_Agent</a>
  </p>
</body>
</html>"""


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(PAGE.encode("utf-8"))
