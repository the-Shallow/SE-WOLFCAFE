# Frontend API Configuration Guide

This document explains how the SafeBites frontend handles API configuration using environment variables.

## Overview

The frontend has been refactored to use a centralized API configuration system instead of hardcoded backend URLs. This provides several benefits:

- **Environment Flexibility**: Easy switching between development, staging, and production environments
- **Security**: No hardcoded sensitive URLs in source code
- **Maintainability**: Single source of truth for all API endpoints
- **Testability**: Easier to mock and test API calls

## File Structure

```
frontend/
├── .env.example           # Example environment file (committed to git)
├── .env.development       # Development environment config (committed to git)
├── .env.production        # Production environment config (committed to git)
├── .env.local            # Local overrides (NOT committed to git)
├── src/
│   └── config/
│       └── api.ts        # Centralized API configuration
```

## Environment Files

### `.env.example`
Template file showing what environment variables are needed. Copy this to `.env.local` to get started.

### `.env.development`
Default configuration for development environment:
```bash
VITE_API_BASE_URL=http://localhost:8000
```

### `.env.production`
Configuration for production builds:
```bash
VITE_API_BASE_URL=https://safebites-yu1o.onrender.com
```

### `.env.local` (Create this file)
Your local overrides. This file is **gitignored** and should never be committed:
```bash
VITE_API_BASE_URL=http://localhost:8000
# or point to any backend URL you need for local development
```

## API Configuration (`src/config/api.ts`)

The centralized configuration file exports:

### 1. `API_BASE_URL`
The base URL for the backend API, automatically loaded from environment variables:
```typescript
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://safebites-yu1o.onrender.com';
```

### 2. `API_ENDPOINTS`
Object containing all API endpoint builders:
```typescript
export const API_ENDPOINTS = {
  users: {
    login: (username: string, password: string) => `${API_BASE_URL}/users/login?...`,
    signup: `${API_BASE_URL}/users/signup`,
    me: `${API_BASE_URL}/users/me`,
  },
  restaurants: {
    base: `${API_BASE_URL}/restaurants`,
    byId: (id: string) => `${API_BASE_URL}/restaurants/${id}`,
    menu: (id: string) => `${API_BASE_URL}/restaurants/${id}/menu`,
    chat: (id: string) => `${API_BASE_URL}/restaurants/${id}/chat`,
  },
};
```

### 3. Helper Functions
- `isApiConfigured()`: Check if API is properly configured
- `logApiConfig()`: Log current configuration for debugging

## Usage in Components

### Before (Hardcoded):
```typescript
const response = await fetch('https://safebites-yu1o.onrender.com/users/login?...', {
  method: 'POST',
});
```

### After (Environment-based):
```typescript
import { API_ENDPOINTS } from '../config/api';

const response = await fetch(API_ENDPOINTS.users.login(username, password), {
  method: 'POST',
});
```

## Refactored Files

The following files have been updated to use the centralized API configuration:

### Pages:
- [Login.tsx](src/pages/Login.tsx:3) - User login
- [SignUp.tsx](src/pages/SignUp.tsx:3) - User registration
- [Dashboard.tsx](src/pages/Dashboard.tsx:3) - User dashboard
- [Settings.tsx](src/pages/Settings.tsx:2) - User settings
- [Home.tsx](src/pages/Home.tsx:2) - Restaurant listing
- [RestaurantMenu.tsx](src/pages/RestaurantMenu.tsx:2) - Menu display
- [SearchChat.tsx](src/pages/SearchChat.tsx:2) - AI-powered search
- [AddRestaurant.tsx](src/pages/AddRestaurant.tsx:3) - Restaurant submission

### Tests:
- [Login.test.tsx](src/frontend_test/Login.test.tsx:5)
- [SignUp.test.tsx](src/frontend_test/SignUp.test.tsx:5)

## Development Workflow

### 1. Local Development
```bash
# Use default development config
npm run dev

# Or create custom .env.local
echo "VITE_API_BASE_URL=http://localhost:8000" > .env.local
npm run dev
```

### 2. Testing Against Different Backends
```bash
# Test against staging server
echo "VITE_API_BASE_URL=https://staging.safebites.com" > .env.local
npm run dev

# Test against production
echo "VITE_API_BASE_URL=https://safebites-yu1o.onrender.com" > .env.local
npm run dev
```

### 3. Production Build
```bash
# Uses .env.production automatically
npm run build

# Or override for custom deployment
VITE_API_BASE_URL=https://custom.backend.com npm run build
```

## Environment Variable Naming

Vite requires environment variables to be prefixed with `VITE_` to be exposed to the client:

✅ **Correct**: `VITE_API_BASE_URL`
❌ **Wrong**: `API_BASE_URL` (won't be accessible in browser)

## Security Considerations

1. **Never commit `.env.local`** - It's in `.gitignore` for a reason
2. **Don't store secrets** - Environment variables are exposed to the browser
3. **Use HTTPS in production** - Always use secure protocols for production URLs
4. **Validate URLs** - The config includes fallback to production URL if env var is missing

## Debugging

### Check current configuration:
```typescript
import { logApiConfig } from '../config/api';

// In your component or console
logApiConfig();
// Output: { baseUrl: 'http://localhost:8000', environment: 'development' }
```

### Verify environment variables:
Open browser console and check:
```javascript
console.log(import.meta.env.VITE_API_BASE_URL);
```

### Common Issues:

**Issue**: API calls fail with 404
**Solution**: Check that `VITE_API_BASE_URL` is correctly set and backend is running

**Issue**: Changes to `.env` file not taking effect
**Solution**: Restart the dev server (`npm run dev`) after changing environment files

**Issue**: Environment variable is `undefined`
**Solution**: Ensure the variable name starts with `VITE_` prefix

## Migration Guide

If you need to add a new API endpoint:

1. Add it to `API_ENDPOINTS` in `src/config/api.ts`:
```typescript
export const API_ENDPOINTS = {
  // ... existing endpoints
  orders: {
    base: `${API_BASE_URL}/orders`,
    byId: (id: string) => `${API_BASE_URL}/orders/${id}`,
  },
};
```

2. Use it in your component:
```typescript
import { API_ENDPOINTS } from '../config/api';

const response = await fetch(API_ENDPOINTS.orders.byId('123'));
```

## Testing

Tests automatically use the API configuration:

```typescript
import { API_ENDPOINTS } from '../config/api';

test('calls correct API endpoint', async () => {
  // Test will use the configured endpoint
  expect(fetchCall[0]).toBe(API_ENDPOINTS.users.signup);
});
```

## Deployment

### Render.com / Vercel / Netlify:
Add environment variable in the platform's dashboard:
- **Key**: `VITE_API_BASE_URL`
- **Value**: `https://your-backend-url.com`

### Docker:
```dockerfile
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build
```

## Summary

The frontend now uses a flexible, environment-based API configuration system that:
- ✅ Eliminates hardcoded URLs
- ✅ Supports multiple environments (dev/staging/prod)
- ✅ Provides centralized endpoint management
- ✅ Improves testability and maintainability
- ✅ Follows Vite best practices

For questions or issues, refer to the [Vite Environment Variables documentation](https://vitejs.dev/guide/env-and-mode.html).
