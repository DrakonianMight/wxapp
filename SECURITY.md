# Security Policy

## Supported Versions

Currently being maintained:

| Version | Supported          |
| ------- | ------------------ |
| main    | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it by:

1. **DO NOT** open a public GitHub issue
2. Email the maintainer directly (check GitHub profile for contact)
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

You should receive a response within 48 hours.

## Security Best Practices

### For Users

1. **Never commit credentials**: Don't commit `.streamlit/secrets.toml` or `.env` files
2. **Use strong passwords**: When creating AWS Cognito accounts
3. **Rotate tokens**: Regularly update your API tokens
4. **Environment variables**: Use environment variables for sensitive configuration
5. **HTTPS only**: Always use HTTPS in production deployments

### For Contributors

1. **Review before committing**: Check for accidentally committed secrets
2. **Use .env.example**: Never put real credentials in example files
3. **Validate inputs**: Always validate and sanitize user inputs
4. **Dependencies**: Keep dependencies up to date
5. **Code review**: Security-sensitive changes need thorough review

## Security Features

### Built-in Security

- ✅ Token-based authentication (AWS Cognito)
- ✅ No hardcoded passwords
- ✅ Environment-based configuration
- ✅ User-provided credentials only
- ✅ No long-lived credentials storage
- ✅ Input validation for coordinates

### Not Included (Users Must Implement)

- ❌ Rate limiting (implement at deployment level)
- ❌ DDoS protection (use CloudFlare or similar)
- ❌ User session management (Streamlit handles basic sessions)

## Common Security Questions

### Q: Is it safe to host this publicly?

A: Yes, with proper configuration:
- Don't expose your AWS credentials
- Use authentication at the hosting level (e.g., Streamlit Community Cloud password protection)
- Consider rate limiting for API calls

### Q: Where are credentials stored?

A: Credentials are:
- Entered by users in the UI (not stored)
- Stored in session state (temporary, cleared on page refresh)
- Never written to disk or logs

### Q: Can someone steal my AWS token?

A: Tokens are:
- Session-only (not persisted)
- Expire automatically (AWS Cognito manages expiration)
- Only visible to the current user's browser session

### Q: Is the code safe for public repositories?

A: Yes, after:
- Removing any hardcoded credentials/IDs
- Adding `.gitignore` to exclude sensitive files
- Ensuring no `.streamlit/secrets.toml` is committed

## Known Limitations

1. **No built-in rate limiting**: Implement this at your deployment platform
2. **Session hijacking**: Use HTTPS and secure hosting
3. **API abuse**: Monitor usage and implement quotas if needed

## Updates

This security policy may be updated. Check back regularly for changes.

**Last Updated**: 2025-12-13
