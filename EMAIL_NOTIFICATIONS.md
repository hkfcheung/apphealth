# Email Notifications Setup

The Status Dashboard now supports email notifications for service status changes. You'll be notified when services go down or come back up, with smart anti-spam protection.

## Features

- **Intelligent Notifications**: Only sends emails when services transition from OPERATIONAL to a problem state (degraded, incident, maintenance, unknown)
- **Recovery Alerts**: Notifies you when services return to OPERATIONAL after being down
- **Anti-Spam Protection**:
  - Cooldown period between notifications (default: 60 minutes per service)
  - Only one notification per status change
  - Won't spam you if a service stays in the same non-operational state
- **Beautiful HTML Emails**: Color-coded status badges with direct links to status pages

## How It Works

### Notification Triggers

✅ **WILL send email:**
- Service goes from OPERATIONAL → DEGRADED/INCIDENT/MAINTENANCE/UNKNOWN
- Service recovers from problem state → OPERATIONAL

❌ **WON'T send email:**
- Service stays OPERATIONAL
- Service stays in same problem state (e.g., DEGRADED → DEGRADED)
- Less than 60 minutes since last notification for that service
- Email not configured

### Cooldown Protection

The system prevents email bombardment by tracking the last notification time for each service. Default cooldown is 60 minutes, meaning:

- If AWS goes down at 2:00 PM, you get an email
- If AWS is still down at 2:30 PM (next poll), no email
- If AWS comes back up at 2:45 PM, you get a recovery email
- If AWS goes down again at 2:50 PM, **no email** (cooldown active until 3:45 PM)

## Setup Instructions

### Option 1: Gmail (Recommended for personal use)

1. **Enable 2-Factor Authentication** on your Gmail account

2. **Generate an App Password**:
   - Go to https://myaccount.google.com/apppasswords
   - Select "Mail" and your device
   - Copy the 16-character password

3. **Create or edit `.env` file** in the project root:

```bash
# Email Notifications
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=abcd efgh ijkl mnop  # Your 16-char app password (spaces optional)
SMTP_FROM_EMAIL=your-email@gmail.com
NOTIFICATION_EMAIL=your-email@gmail.com
NOTIFICATION_COOLDOWN_MINUTES=60
```

4. **Restart the backend**:
```bash
docker-compose restart backend
```

### Option 2: SendGrid (Recommended for production)

1. **Sign up for SendGrid** at https://sendgrid.com

2. **Create an API key** with "Mail Send" permissions

3. **Configure `.env`**:
```bash
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USERNAME=apikey
SMTP_PASSWORD=your-sendgrid-api-key
SMTP_FROM_EMAIL=noreply@your-domain.com
NOTIFICATION_EMAIL=alerts@your-company.com
```

### Option 3: AWS SES (Recommended for AWS deployments)

1. **Verify your domain/email** in AWS SES

2. **Create SMTP credentials** in the SES console

3. **Configure `.env`**:
```bash
SMTP_HOST=email-smtp.us-east-1.amazonaws.com  # Your region
SMTP_PORT=587
SMTP_USERNAME=your-ses-smtp-username
SMTP_PASSWORD=your-ses-smtp-password
SMTP_FROM_EMAIL=noreply@your-domain.com
NOTIFICATION_EMAIL=alerts@your-company.com
```

## Testing

To test your email configuration:

1. **Manually trigger a status change** by temporarily taking down one of your monitored services
2. **Check the backend logs** for notification activity:
```bash
docker-compose logs -f backend | grep -i notification
```

3. **Look for log messages** like:
```
INFO: Sent notification for aws-cloudfront: operational → incident
```

## Customization

### Change Cooldown Period

Edit the cooldown in minutes in your `.env` file:
```bash
# Wait 2 hours between notifications per service
NOTIFICATION_COOLDOWN_MINUTES=120

# More frequent notifications (30 minutes)
NOTIFICATION_COOLDOWN_MINUTES=30
```

### Multiple Recipients

The current implementation sends to one email address. To send to multiple people:

1. Use your SMTP provider's distribution list feature
2. Or create a Google Group and use that as `NOTIFICATION_EMAIL`

## Troubleshooting

### No emails being sent

1. **Check configuration**:
```bash
docker-compose exec backend python -c "from app.config import settings; from app.notifications import EmailNotifier; print('Configured:', EmailNotifier.is_configured())"
```

2. **Check backend logs** for errors:
```bash
docker-compose logs backend | grep -i "email\|smtp\|notification"
```

3. **Common issues**:
   - Gmail: Make sure you're using an App Password, not your regular password
   - SendGrid: Verify sender email address
   - AWS SES: Check if you're still in sandbox mode (limits recipients)

### Emails going to spam

- Add your sender email to your contacts
- Configure SPF/DKIM records if using custom domain
- Use a verified sending domain

### Too many/few emails

Adjust `NOTIFICATION_COOLDOWN_MINUTES` in your `.env` file.

## Email Preview

### Subject Line Examples
```
✅ AWS CloudFront - Service Restored
⚠️ Slack - Performance Degraded
🚨 Microsoft 365 - Incident Detected
🔧 Box - Maintenance in Progress
```

### Email Body
The email includes:
- Clear status transition (OLD STATUS → NEW STATUS)
- Timestamp of the change
- Service summary/incident description
- Direct link to the status page
- Color-coded status badges

## Security Notes

- **Never commit `.env` files** to version control
- **Use App Passwords** for Gmail (never your account password)
- **Rotate credentials** periodically
- **Use environment variables** in production deployments
- **Limit SMTP credentials** to mail-sending only

## Disabling Notifications

To disable email notifications, simply remove or comment out the email settings in your `.env` file:

```bash
# SMTP_HOST=smtp.gmail.com
# SMTP_PORT=587
# ...
```

Then restart the backend:
```bash
docker-compose restart backend
```
