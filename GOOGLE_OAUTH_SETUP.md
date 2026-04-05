# Google OAuth Setup Guide for RetailOS

This guide walks you through enabling Google Sign-In authentication for RetailOS dashboard.

## Prerequisites
- A Google Cloud Project (GCP)
- Access to Google Cloud Console
- RetailOS already running locally or on a server

## Step 1: Create a Google Cloud Project

1. Visit [Google Cloud Console](https://console.cloud.google.com/)
2. Click on **Select a Project** → **New Project**
3. Enter project name: `RetailOS Dashboard` (or your choice)
4. Click **Create**

## Step 2: Enable OAuth 2.0 APIs

1. In Google Cloud Console, go to **APIs & Services** > **Library**
2. Search for and enable these APIs:
   - **Google+ API** (or **Google Identity Service API**)
   - **OAuth 2.0** (already enabled by default)

## Step 3: Create OAuth 2.0 Credentials

1. Go to **APIs & Services** > **Credentials**
2. Click **Create Credentials** → **OAuth 2.0 Client ID**
3. If prompted, configure the OAuth consent screen first:
   - **User Type**: External
   - **App name**: RetailOS
   - Add scopes: `openid`, `email`, `profile`
   - Add test users (your Google account emails)
4. Back to Credentials, select **Web application**
5. Name: `RetailOS Dashboard`
6. Add Authorized redirect URIs:
   - Local: `http://localhost:8501/oauth2callback`
   - Production: `https://your-domain.com/oauth2callback`
7. Click **Create**
8. Copy the **Client ID** and **Client Secret**

## Step 4: Configure RetailOS

### Option A: Using Secrets File (Development)

Edit `.streamlit/secrets.toml`:

```toml
[auth]
redirect_uri = "http://localhost:8501/oauth2callback"
cookie_secret = "your-random-secret-string-min-32-chars"

[auth.google]
client_id = "YOUR_GOOGLE_CLIENT_ID.apps.googleusercontent.com"
client_secret = "YOUR_GOOGLE_CLIENT_SECRET"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"

# Optional: Set role mappings for Google users
[access.google_roles]
admin = ["admin@yourdomain.com"]
analyst = ["analyst@yourdomain.com"]
viewer = ["user@yourdomain.com", "guest@example.com"]

# Don't forget local fallback credentials
[[access.users]]
username = "admin"
name = "Admin User"
role = "admin"
password = "ChangeMeNow123"

[[access.users]]
username = "analyst"
name = "Analyst User"
role = "analyst"
password = "AnalystPass123"
```

### Option B: Using Environment Variables (Production)

Set these environment variables on your server:

```bash
# Google OAuth config
RETAILOS_AUTH_REDIRECT_URI="https://your-domain.com/oauth2callback"
RETAILOS_AUTH_COOKIE_SECRET="your-random-secret-string-min-32-chars"
RETAILOS_AUTH_GOOGLE_CLIENT_ID="YOUR_GOOGLE_CLIENT_ID.apps.googleusercontent.com"
RETAILOS_AUTH_GOOGLE_CLIENT_SECRET="YOUR_GOOGLE_CLIENT_SECRET"
RETAILOS_AUTH_GOOGLE_METADATA_URL="https://accounts.google.com/.well-known/openid-configuration"

# Google role mappings (comma-separated emails)
RETAILOS_GOOGLE_ADMIN_EMAILS="admin@yourdomain.com"
RETAILOS_GOOGLE_ANALYST_EMAILS="analyst@yourdomain.com,analyst2@yourdomain.com"
RETAILOS_GOOGLE_VIEWER_EMAILS="user@yourdomain.com,guest@example.com"

# Local fallback user
RETAILOS_AUTH_USERNAME="admin"
RETAILOS_AUTH_NAME="Admin User"
RETAILOS_AUTH_ROLE="admin"
RETAILOS_AUTH_PASSWORD="ChangeMeNow123"  # Or use password hash
```

### Option C: Using streamlit.toml (Configuration File)

Create `.streamlit/config.toml`:

```toml
[client]
showErrorDetails = true

[server]
headless = true
port = 8501
runOnSave = true

[theme]
primaryColor = "#e76f51"
backgroundColor = "#f4efe8"
secondaryBackgroundColor = "#fff"
textColor = "#1f2a2c"
```

## Step 5: Test Google Sign-In

1. Start RetailOS:
   ```bash
   streamlit run dashboard_app.py
   ```

2. Open `http://localhost:8501`

3. You should now see a **"Continue with Google"** button

4. Click it, authenticate with a Google account that's in your authorized users list

5. You'll be redirected and logged in as the mapped role (admin/analyst/viewer)

## Step 6: Deploy to Production

### For Heroku:

1. Update `Procfile` to specify Python version:
   ```
   web: python -m streamlit.cli run dashboard_app.py --client.showErrorDetails=false --server.port=$PORT --server.headless=true
   ```

2. Set config vars:
   ```bash
   heroku config:set RETAILOS_AUTH_GOOGLE_CLIENT_ID="..."
   heroku config:set RETAILOS_AUTH_GOOGLE_CLIENT_SECRET="..."
   heroku config:set RETAILOS_AUTH_REDIRECT_URI="https://your-app.herokuapp.com/oauth2callback"
   heroku config:set RETAILOS_AUTH_COOKIE_SECRET="$(python -c 'import secrets; print(secrets.token_hex(32))')"
   ```

### For AWS/GCP/Azure:

1. Use their secrets management (AWS Secrets Manager, GCP Secret Manager, etc.)
2. Set environment variables from your deployment platform
3. Update authorized redirect URIs in Google Cloud Console

## Troubleshooting

### "Google Sign-In is available but not configured"

This means:
- Google apps credentials are NOT in secrets or environment variables
- Fallback to local username/password login

**Fix**: Add Google client ID and secret to secrets.toml or env vars

### "Invalid redirect URI"

- Check the redirect URI in Google Cloud Console
- Must exactly match `http://localhost:8501/oauth2callback` (local) or `https://your-domain.com/oauth2callback` (production)

### "Signed in user not found in role mappings"

- The user's Google email is not in your `google_roles` configuration
- Add their email to appropriate role list in secrets.toml or env vars
- Default role is "viewer" if no mapping exists

### "Cookie secret is invalid"

- Generate a random 32+ character string:
  ```bash
  python -c 'import secrets; print(secrets.token_hex(32))'
  ```

## Security Best Practices

✅ **Do:**
- Use password hashes instead of plain passwords
- Use environment variables on production
- Rotate Google secret regularly
- Enable 2FA on your Google admin account
- Restrict authorized domains/users

❌ **Don't:**
- Commit secrets.toml to git (add to .gitignore)
- Use weak cookie secrets
- Share client secrets publicly
- Mix test and production credentials

## Generate Password Hash

To create a password hash for `password_hash` field:

```python
from src.auth import _pbkdf2_sha256
password = "YourPassword123"
salt = "your-random-salt-string"
hash_value = _pbkdf2_sha256(password, salt, 390000)
print(f"pbkdf2_sha256$390000${salt}${hash_value}")
```

## Additional Resources

- [Streamlit Authentication Documentation](https://docs.streamlit.io/deploy/streamlit-cloud/authentication-without-sso)
- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [RetailOS Auth Module](./src/auth.py)
