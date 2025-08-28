# Email Configuration Guide for SmartGrader

## Why Email Configuration is Needed

SmartGrader uses email functionality for password reset features. When users forget their passwords, they can request a reset link via email.

## Current Issue

You're seeing the error "Failed to send verification email. Please try again." because the email configuration is not set up.

## Solution: Configure Email Settings

### Option 1: For Development (Recommended for Testing)

The system is currently in development mode, which means:
- ✅ Password reset requests will work
- ✅ Verification codes will be displayed in the console
- ✅ Reset links will be generated
- ❌ No actual emails will be sent

**To test the password reset:**
1. Request a password reset
2. Check your terminal/console for the verification code and reset link
3. Use the reset link to change your password

### Option 2: For Production (Real Email Sending)

To enable real email sending, create a `.env` file in your project root with:

```env
# DeepSeek API Key (Required for AI grading)
DEEPSEEK_API_KEY=your_deepseek_token_here

# Email Configuration (Required for password reset functionality)
SMTP_EMAIL=your_email@gmail.com
SMTP_PASSWORD=your_app_password_here
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
```

### Gmail App Password Setup

If using Gmail, you need an App Password (not your regular password):

1. **Go to Google Account settings**: https://myaccount.google.com/
2. **Navigate to Security**
3. **Enable 2-Step Verification** (if not already enabled)
4. **Go to "App passwords"** (under 2-Step Verification)
5. **Generate an App Password** for "Mail"
6. **Use this App Password** in the `SMTP_PASSWORD` field

### Alternative Email Providers

You can use other email providers with these settings:

**Outlook/Hotmail:**
```env
SMTP_SERVER=smtp-mail.outlook.com
SMTP_PORT=587
```

**Yahoo:**
```env
SMTP_SERVER=smtp.mail.yahoo.com
SMTP_PORT=587
```

## Testing the Setup

1. Create the `.env` file with your email settings
2. Restart the Flask application
3. Try the password reset feature
4. Check your email for the reset link

## Development Mode Benefits

For development and testing, the current setup is actually beneficial because:
- No need to configure email servers
- Verification codes are clearly displayed in console
- Reset links work immediately
- No risk of sending test emails to real addresses

## Next Steps

1. **For testing**: Use the current development mode (no changes needed)
2. **For production**: Follow the email configuration steps above
3. **For deployment**: Ensure your hosting provider supports SMTP

The password reset system is fully functional - you just need to check the console output for the verification codes and links!
