# RetailOS Deployment

## Local Run

```powershell
streamlit run app.py
```

## Required Secret

Create `.streamlit/secrets.toml`:

```toml
[auth]
redirect_uri = "http://localhost:8501/oauth2callback"
cookie_secret = "replace-with-a-long-random-string"

[auth.google]
client_id = "your-google-client-id"
client_secret = "your-google-client-secret"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"

[access]

[[access.users]]
username = "admin"
name = "Retail Admin"
role = "admin"
password = "ChangeMeNow123"

[[access.users]]
username = "analyst"
name = "Operations Analyst"
role = "analyst"
password = "Analyse123"

[[access.users]]
username = "viewer"
name = "Business Viewer"
role = "viewer"
password = "Viewer123"

[access.google_roles]
admin = ["admin@example.com"]
analyst = ["analyst@example.com"]
viewer = ["viewer@example.com"]
```

For production, prefer a password hash instead of a plain password. Roles supported are `admin`, `analyst`, and `viewer`. Google Sign-In is optional; local users remain as the fallback path.

## Streamlit Community Cloud

1. Push this project to GitHub.
2. In Streamlit Community Cloud, create a new app.
3. Select this repo and set the main file to `app.py`.
4. In app settings, add secrets:

```toml
[auth]
redirect_uri = "https://your-app-name.streamlit.app/oauth2callback"
cookie_secret = "replace-with-a-long-random-string"

[auth.google]
client_id = "your-google-client-id"
client_secret = "your-google-client-secret"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"

[access]

[[access.users]]
username = "admin"
name = "Retail Admin"
role = "admin"
password = "ChangeMeNow123"

[[access.users]]
username = "analyst"
name = "Operations Analyst"
role = "analyst"
password = "Analyse123"

[[access.users]]
username = "viewer"
name = "Business Viewer"
role = "viewer"
password = "Viewer123"

[access.google_roles]
admin = ["admin@example.com"]
analyst = ["analyst@example.com"]
viewer = ["viewer@example.com"]
```

5. Deploy.

If the app was already deployed before dependency fixes, open the app settings and reboot or redeploy it after the new commit is pushed.

## Render / Procfile-based Platforms

This repo includes a `Procfile`:

```text
web: streamlit run app.py --server.port=$PORT --server.address=0.0.0.0
```

Set the auth secret using either:

- `.streamlit/secrets.toml`
- environment variables:
  - `RETAILOS_AUTH_USERNAME`
  - `RETAILOS_AUTH_PASSWORD`
  - `RETAILOS_AUTH_NAME`
  - `RETAILOS_AUTH_ROLE`
  - or `RETAILOS_AUTH_PASSWORD_HASH`

## Google Sign-In Notes

- Use Streamlit's native OIDC authentication commands: `st.login()`, `st.user`, and `st.logout()`.
- For Google Cloud, add your Streamlit callback URL to the authorized redirect URIs.
- Keep at least one local admin account configured so you can still access the app if OAuth is misconfigured.

## Important Security Note

Do not commit `.streamlit/secrets.toml`. It is ignored by `.gitignore`.
