# Auth notes: OAuth2PasswordBearer vs JSON login

Learning note about the Swagger form-data "mismatch" in this project's auth.

## The two separate things

### 1. `OAuth2PasswordBearer` (in `backend/auth.py`)

- Its only real job: on **protected** requests, read the `Authorization: Bearer <token>`
  header and hand you the token string.
- It never touches login credentials.
- It does not care about Pydantic.
- `tokenUrl="/login"` is **just a documentation hint** for Swagger's Authorize
  button. No validation, nothing enforced.

### 2. The `/login` endpoint

- This is where the client **sends** `email`/`password`.
- This is the only place where "form data vs JSON" matters.

They are independent. You **can** use a Pydantic `LoginRequest` with
`OAuth2PasswordBearer`. Nothing breaks for real clients.

## Why the mismatch appears

The OAuth2 spec defines the "password grant" token request as:

- content type: `application/x-www-form-urlencoded` (form data, not JSON)
- fields: `username` and `password`

`OAuth2PasswordBearer` advertises this exact flow to Swagger, so Swagger renders
an Authorize dialog that **always** posts form data with `username`/`password`.

Our schema is different:

```python
# backend/schemas/auth.py
class LoginRequest(BaseModel):
    email: EmailStr
    password: str
```

So if `/login` is written with `LoginRequest` (JSON), and Swagger's Authorize
button sends form data with `username`, the endpoint returns **422** because the
field name and content type don't match.

Where the library declares those names:

`fastapi/security/oauth2.py` -> `class OAuth2PasswordRequestForm`:

```
The OAuth2 specification dictates that for a password flow the data should be
collected using form data (instead of JSON) and that it should have the specific
fields `username` and `password`.
```

It's the OAuth2 **spec** that fixes the names `username`/`password`. Our code
never declares `username`; the library does.

## Consequences table

| `/login` accepts          | Real clients (JSON) | Swagger Authorize button |
|---------------------------|---------------------|--------------------------|
| Pydantic `LoginRequest`   | works               | breaks (sends form data) |
| `OAuth2PasswordRequestForm` | works (form data) | works                    |

Both still use `OAuth2PasswordBearer` to protect routes. That part is orthogonal.

## Solutions

### A. Accept form data (what most tutorials do)

`/login` uses `OAuth2PasswordRequestForm`. The email rides in the `username`
form field. Swagger Authorize works, but `LoginRequest` becomes unused.

```python
from fastapi.security import OAuth2PasswordRequestForm

@app.post("/login", response_model=TokenResponse)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == form.username))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return TokenResponse(access_token=create_access_token(user.id))
```

### B. Use `HTTPBearer` instead of `OAuth2PasswordBearer` (clean for JSON APIs)

`HTTPBearer` gives Swagger a plain "paste your token" box (no OAuth2 flow, no
forced form). `/login` stays Pydantic/JSON.

```python
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

bearer_scheme = HTTPBearer()

async def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = creds.credentials
    ...
```

Workflow: call `/login` (JSON) -> copy `access_token` -> Authorize -> paste.

### C. Accept both form and JSON

Custom dependency. Most code, rarely worth it.

## What this project actually decided

We only need the endpoint for the webapp, **not** the Swagger Authorize button.
So keep the Pydantic `LoginRequest` (JSON).

Webapp flow:

1. `POST /login` with JSON `{ "email": ..., "password": ... }`
2. Receive `{ "access_token": "..." }` and store it
3. Send header `Authorization: Bearer <token>` on protected requests
4. `OAuth2PasswordBearer` reads the header -> `get_current_user` decodes it

The form-data quirk only exists for Swagger's Authorize button; the webapp never
uses it.

Tip: `OAuth2PasswordBearer` always advertises the OAuth2 password flow in `/docs`
(adding that Authorize dialog). If that looks misleading, `HTTPBearer` is the
drop-in that advertises plain bearer auth instead. Functionally identical for the
webapp.
