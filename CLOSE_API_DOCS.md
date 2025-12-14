# Close API Documentation

## Overview

Close API is a RESTful API for managing CRM data including contacts, leads, opportunities, activities, and more. This document covers what we learned about authentication, endpoints, limitations, and implementation patterns.

## Base URL

```
https://api.close.com/api/v1/
```

All API endpoints are prefixed with this base URL.

## Authentication

Close API uses **HTTP Basic Authentication** with your API key.

### Getting Your API Key

1. Log into your Close account
2. Navigate to **Settings** > **Developer** > **API Keys**
3. Click **New API Key**
4. Provide a descriptive name and click **Create API Key**
5. **Copy the key immediately** - it won't be displayed again

### Authentication Format

The API key is used as the **username** in Basic Auth, with an **empty password**:

```
Authorization: Basic base64(api_key:)
```

**Important:** The colon (`:`) after the API key is required - it indicates an empty password.

### cURL Example

```bash
curl -u "your_api_key_here:" https://api.close.com/api/v1/me/
```

Note the colon after the API key - this is required for Basic Auth with empty password.

### PowerShell Example

```powershell
$headers = @{ 
    Authorization = "Basic " + [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("your_api_key_here:")) 
}
Invoke-WebRequest -Uri "https://api.close.com/api/v1/me/" -Headers $headers -Method GET
```

### Python Example

```python
import requests
import base64

api_key = "your_api_key_here"
auth_header = f"Basic {base64.b64encode(f'{api_key}:'.encode()).decode()}"

response = requests.get(
    "https://api.close.com/api/v1/me/",
    headers={"Authorization": auth_header}
)
print(response.json())
```

## Critical Discovery: CORS Limitations

**Important:** Close API does **NOT** support CORS (Cross-Origin Resource Sharing) from browsers.

- âŒ Direct browser requests (fetch/XMLHttpRequest) will fail with CORS errors
- âœ… Server-side requests work perfectly (Node.js, Python, etc.)
- âœ… Use a backend proxy to call Close API from frontend applications

### CORS Error Example

When trying to call Close API directly from a browser (e.g., `http://localhost:5173`), you'll get:

```
Access to fetch at 'https://api.close.com/api/v1/me/' from origin 'http://localhost:5173' 
has been blocked by CORS policy: Response to preflight request doesn't pass access control 
check: No 'Access-Control-Allow-Origin' header is present on the requested resource.
```

This happens because Close API doesn't send the `Access-Control-Allow-Origin` header in its responses, which browsers require for cross-origin requests.

### What is CORS?

CORS (Cross-Origin Resource Sharing) is a security mechanism implemented by web browsers to control how web pages can request resources from a different domain, protocol, or port than the one serving the web page.

**Same-Origin Policy:**
- Browsers enforce the "Same-Origin Policy" by default
- An origin consists of: protocol (http/https) + domain + port
- Example: `http://localhost:5173` and `https://api.close.com` are **different origins**

**Why CORS Exists:**
- Prevents malicious websites from making unauthorized requests to other domains
- Protects user data and prevents CSRF (Cross-Site Request Forgery) attacks
- Ensures that only explicitly allowed cross-origin requests are permitted

### How CORS Works

When a browser makes a cross-origin request, it:

1. **Sends a preflight request** (OPTIONS) for certain types of requests
2. **Checks response headers** from the server:
   - `Access-Control-Allow-Origin` - Which origins are allowed
   - `Access-Control-Allow-Methods` - Which HTTP methods are allowed
   - `Access-Control-Allow-Headers` - Which headers are allowed
   - `Access-Control-Allow-Credentials` - Whether credentials can be included

3. **Blocks the request** if the server doesn't send appropriate CORS headers

### Close API and CORS

Close API **does not send CORS headers** in its responses. This means:

- ❌ Browsers will **block** all requests from frontend applications
- ❌ Even if your API key is valid, the browser won't let the request complete
- ❌ This is **by design** - Close API is intended for server-to-server communication

**Why Close API Doesn't Support CORS:**
- Security: Prevents API keys from being exposed in frontend code
- Control: Forces developers to use backend services where API keys can be secured
- Best Practice: API keys should never be in client-side JavaScript

### Browser Console Error Details

You might see errors like:

```
Failed to load resource: net::ERR_FAILED
TypeError: Failed to fetch
```

These are all symptoms of CORS blocking. The request never reaches Close API - it's blocked by the browser before leaving your machine.

### What Works vs. What Doesn't

**✅ Works (Server-Side):**
- Node.js/Express server making requests
- Python scripts using `requests` library
- PowerShell `Invoke-WebRequest`
- cURL commands
- Any server-side HTTP client

**❌ Doesn't Work (Browser):**
- `fetch()` in JavaScript
- `XMLHttpRequest` in JavaScript
- Axios in browser
- Any HTTP request from browser JavaScript

### Why You Can't "Fix" CORS on the Client Side

**Common Misconceptions:**
- ❌ "I can add headers to fix CORS" - No, CORS headers must come from the server
- ❌ "I can use a browser extension" - This only works for your browser, not for users
- ❌ "I can disable CORS in my browser" - This is a security risk and doesn't help end users

**The Reality:**
- CORS is enforced by the **browser**, not your code
- CORS headers must be sent by the **server** (Close API in this case)
- You cannot modify Close API's response headers
- The **only solution** is a backend proxy

## Solution: Backend Proxy

Since browsers cannot directly call Close API, you **must** use a backend proxy server.

### Architecture

```
Frontend (Browser) â†’ Backend Proxy â†’ Close API
```

The backend proxy:
1. Receives requests from your frontend (same origin or CORS-enabled)
2. Adds authentication headers with your API key
3. Forwards requests to Close API (server-to-server, no CORS)
4. Returns responses to frontend

### Why This Works

- Browser â†’ Proxy: Same origin or proxy allows CORS
- Proxy â†’ Close API: Server-to-server request, CORS doesn't apply
- API key stays secure on the backend


**Detailed Explanation:**

**Step 1: Browser → Proxy**
- Your frontend calls your own proxy server (e.g., `http://localhost:3001`)
- If same origin: No CORS check needed
- If different origin: Proxy sends `Access-Control-Allow-Origin` header (via CORS middleware)
- Browser sees the CORS header and allows the request ✅

**Step 2: Proxy → Close API**
- Proxy makes server-to-server HTTP request
- **CORS doesn't apply** - CORS is a browser security feature, not a server feature
- Servers can make requests to any domain without CORS restrictions
- Close API responds normally ✅

**Step 3: Proxy → Browser**
- Proxy receives response from Close API
- Proxy adds CORS headers (`Access-Control-Allow-Origin: *` or specific origin)
- Browser receives response with proper CORS headers
- Browser allows your frontend to read the response ✅

**Key Points:**
- CORS only applies to **browser** requests, not server requests
- Your proxy can call Close API without any CORS restrictions
- Your proxy controls what CORS headers to send back to the browser
- API key stays secure on the backend (never exposed to browser)
## Backend Proxy Implementation

### Node.js/Express Proxy

```javascript
import express from 'express';
import cors from 'cors';

const app = express();
const PORT = process.env.PORT || 3001;

const CLOSE_API_KEY = 'your_api_key_here';
const CLOSE_API_BASE = 'https://api.close.com/api/v1';

app.use(cors()); // Allow frontend to call this proxy
app.use(express.json());

const authHeader = `Basic ${Buffer.from(`${CLOSE_API_KEY}:`).toString('base64')}`;

app.use('/api/close', async (req, res) => {
  try {
    const path = req.path || '/';
    const queryString = req.url.includes('?') ? req.url.substring(req.url.indexOf('?')) : '';
    const url = `${CLOSE_API_BASE}${path}${queryString}`;
    
    const options = {
      method: req.method,
      headers: {
        'Authorization': authHeader,
        'Content-Type': 'application/json',
      },
    };
    
    if (['POST', 'PUT', 'PATCH'].includes(req.method) && req.body) {
      options.body = JSON.stringify(req.body);
    }
    
    const response = await fetch(url, options);
    const data = await response.json();
    
    res.status(response.status).json(data);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.listen(PORT, () => {
  console.log(`Proxy server running on http://localhost:${PORT}`);
});
```

### Python/Flask Proxy

```python
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import base64
import os

app = Flask(__name__)
CORS(app)  # Allow frontend to call this proxy

CLOSE_API_KEY = os.getenv('CLOSE_API_KEY', 'your_api_key_here')
CLOSE_API_BASE = 'https://api.close.com/api/v1'

@app.route('/api/close/<path:endpoint>', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
def proxy_close_api(endpoint):
    url = f"{CLOSE_API_BASE}/{endpoint}"
    if request.query_string:
        url += f"?{request.query_string.decode()}"
    
    auth_header = f"Basic {base64.b64encode(f'{CLOSE_API_KEY}:'.encode()).decode()}"
    
    headers = {
        'Authorization': auth_header,
        'Content-Type': 'application/json'
    }
    
    if request.method == 'GET':
        response = requests.get(url, headers=headers)
    elif request.method == 'POST':
        response = requests.post(url, headers=headers, json=request.json)
    elif request.method == 'PUT':
        response = requests.put(url, headers=headers, json=request.json)
    elif request.method == 'PATCH':
        response = requests.patch(url, headers=headers, json=request.json)
    elif request.method == 'DELETE':
        response = requests.delete(url, headers=headers)
    
    return jsonify(response.json()), response.status_code

if __name__ == '__main__':
    app.run(port=3001)
```

### Python/FastAPI Proxy

```python
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import httpx
import base64
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CLOSE_API_KEY = os.getenv('CLOSE_API_KEY', 'your_api_key_here')
CLOSE_API_BASE = 'https://api.close.com/api/v1'

@app.api_route('/api/close/{path:path}', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
async def proxy_close_api(path: str, request: Request):
    url = f"{CLOSE_API_BASE}/{path}"
    
    if request.url.query:
        url += f"?{request.url.query}"
    
    auth_header = f"Basic {base64.b64encode(f'{CLOSE_API_KEY}:'.encode()).decode()}"
    
    headers = {
        'Authorization': auth_header,
        'Content-Type': 'application/json'
    }
    
    body = None
    if request.method in ['POST', 'PUT', 'PATCH']:
        body = await request.json()
    
    async with httpx.AsyncClient() as client:
        response = await client.request(
            method=request.method,
            url=url,
            headers=headers,
            json=body
        )
    
    return response.json()
```

## Common Endpoints

### Get Current User

```http
GET /me/
```

Returns information about the authenticated user, including:
- User ID, email, name
- Organizations
- Email accounts
- Phone numbers
- Permissions

**Tested successfully** with PowerShell:
```powershell
$headers = @{ Authorization = "Basic " + [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("api_key:")) }
Invoke-WebRequest -Uri "https://api.close.com/api/v1/me/" -Headers $headers
```

### Contacts

```http
GET /contact/
GET /contact/{contact_id}/
POST /contact/
PUT /contact/{contact_id}/
PATCH /contact/{contact_id}/
DELETE /contact/{contact_id}/
```

**Query Parameters:**
- `limit` - Number of results (default: 100, max: 200)
- `skip` - Number of results to skip
- `query` - Search query string

**Example:**
```http
GET /contact/?limit=10&query=john
```

### Leads

```http
GET /lead/
GET /lead/{lead_id}/
POST /lead/
PUT /lead/{lead_id}/
PATCH /lead/{lead_id}/
DELETE /lead/{lead_id}/
```

### Opportunities (Deals)

```http
GET /opportunity/
GET /opportunity/{opportunity_id}/
POST /opportunity/
PUT /opportunity/{opportunity_id}/
PATCH /opportunity/{opportunity_id}/
DELETE /opportunity/{opportunity_id}/
```

### Activities

```http
GET /activity/
GET /activity/{activity_id}/
POST /activity/
PUT /activity/{activity_id}/
PATCH /activity/{activity_id}/
DELETE /activity/{activity_id}/
```

## Frontend Integration Pattern

### Using the Proxy

Your frontend should call the proxy, not Close API directly:

```typescript
// âŒ This won't work (CORS error)
const CLOSE_API_BASE = 'https://api.close.com/api/v1';

// âœ… This works (via proxy)
const PROXY_BASE = 'http://localhost:3001/api/close';

async function getCurrentUser() {
  const response = await fetch(`${PROXY_BASE}/me/`);
  return response.json();
}
```

### Example: React Hook

```typescript
import { useState, useEffect } from 'react';

const PROXY_BASE = 'http://localhost:3001/api/close';

export function useCloseAPI(endpoint: string) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true);
        const response = await fetch(`${PROXY_BASE}${endpoint}`);
        if (!response.ok) {
          throw new Error(`API Error: ${response.status}`);
        }
        const result = await response.json();
        setData(result);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, [endpoint]);

  return { data, loading, error };
}
```

## Error Handling

Close API returns standard HTTP status codes:

- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized (invalid API key)
- `404` - Not Found
- `429` - Rate Limited
- `500` - Server Error

**Error Response Format:**
```json
{
  "error": {
    "message": "Error description",
    "type": "error_type"
  }
}
```

## Rate Limits

Close API has rate limits. Check the response headers:
- `X-RateLimit-Limit` - Maximum requests per time window
- `X-RateLimit-Remaining` - Remaining requests in current window
- `X-RateLimit-Reset` - Time when the rate limit resets

## Security Best Practices

1. **Never expose API keys in frontend code**
   - Store API keys in environment variables on the backend
   - Use backend proxy to handle authentication

2. **Use environment variables**
   ```bash
   # .env file (backend)
   CLOSE_API_KEY=your_api_key_here
   ```

3. **Restrict CORS origins** in your proxy
   ```javascript
   app.use(cors({
     origin: 'http://localhost:5173' // Only allow your frontend
   }));
   ```

4. **Validate and sanitize inputs** before forwarding to Close API

5. **Implement rate limiting** in your proxy to prevent abuse

## Testing API Connection

### Test with cURL

```bash
curl -u "your_api_key:" https://api.close.com/api/v1/me/
```

### Test with PowerShell

```powershell
$headers = @{ 
    Authorization = "Basic " + [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("your_api_key:")) 
}
$response = Invoke-WebRequest -Uri "https://api.close.com/api/v1/me/" -Headers $headers
$response.Content
```

**Verified:** This works perfectly from server-side (PowerShell/Node.js/Python).

### Test with Python

```python
import requests
import base64

api_key = "your_api_key"
auth = base64.b64encode(f"{api_key}:".encode()).decode()

response = requests.get(
    "https://api.close.com/api/v1/me/",
    headers={"Authorization": f"Basic {auth}"}
)

print(response.status_code)
print(response.json())
```

## Key Takeaways

1. **Close API uses HTTP Basic Auth** with API key as username and empty password
2. **CORS is NOT supported** - browsers cannot call Close API directly
3. **Backend proxy is REQUIRED** for frontend applications
4. **Server-side requests work perfectly** - tested with PowerShell, works with Node.js/Python
5. **API key must be kept secure** on the backend, never in frontend code

## References

- [Close API Documentation](https://developer.close.com/)
- [Authentication Guide](https://developer.close.com/topics/authentication/)
- [API Reference](https://developer.close.com/reference/)
