# RetailOS Deployment

## Local Run

```powershell
streamlit run app.py
```

## Required Secret

Create `.streamlit/secrets.toml`:

```toml
[auth]
username = "admin"
password = "ChangeMeNow123"
```

For production, prefer a password hash instead of a plain password.

## Streamlit Community Cloud

1. Push this project to GitHub.
2. In Streamlit Community Cloud, create a new app.
3. Select this repo and set the main file to `app.py`.
4. In app settings, add secrets:

```toml
[auth]
username = "admin"
password = "ChangeMeNow123"
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
  - or `RETAILOS_AUTH_PASSWORD_HASH`

## Important Security Note

Do not commit `.streamlit/secrets.toml`. It is ignored by `.gitignore`.
