# TechCorp SaaS - Product Documentation

## TaskFlow Pro Documentation

### Getting Started

#### Account Setup
1. Sign up at app.techcorp.com/signup
2. Verify your email address
3. Create your first workspace
4. Invite team members via email or shareable link
5. Choose your subscription tier

#### Creating Your First Project
1. Click "New Project" in the dashboard
2. Enter project name and description
3. Select project template (Kanban, Scrum, Waterfall, or Blank)
4. Add team members to the project
5. Start creating tasks

### Features Guide

#### Task Management
- **Creating Tasks**: Click "+" button or press 'N' keyboard shortcut
- **Task Fields**: Title, description, assignee, due date, priority, labels, attachments
- **Subtasks**: Break down complex tasks into smaller steps
- **Dependencies**: Link tasks that must be completed in sequence
- **Recurring Tasks**: Set up daily, weekly, or monthly recurring tasks

#### Collaboration
- **Comments**: @mention team members to notify them
- **File Attachments**: Drag and drop files up to 100MB per file
- **Activity Feed**: See real-time updates on project changes
- **Notifications**: Configure email, push, or in-app notifications

#### Automation
- **Workflow Rules**: Automatically move tasks based on status changes
- **Email Integration**: Create tasks from emails sent to project@yourworkspace.techcorp.com
- **Webhooks**: Trigger external actions when tasks are updated

#### Integrations
- Slack, Microsoft Teams
- Google Drive, Dropbox
- GitHub, GitLab, Bitbucket
- Zapier for 1000+ app connections

### Mobile App Features
- Full task management capabilities
- Offline mode (syncs when online)
- Push notifications
- Camera integration for quick photo attachments
- Biometric authentication

---

## Frequently Asked Questions

### Account & Billing

**Q: How do I upgrade my subscription?**
A: Go to Settings > Billing > Change Plan. Select your new tier and confirm. Changes take effect immediately, and you'll be prorated for the current billing period.

**Q: Can I cancel anytime?**
A: Yes, cancel anytime from Settings > Billing > Cancel Subscription. You'll retain access until the end of your billing period. No refunds for partial months.

**Q: What payment methods do you accept?**
A: We accept all major credit cards (Visa, Mastercard, Amex, Discover) and PayPal. Enterprise customers can pay via invoice (NET 30 terms).

**Q: Do you offer discounts for nonprofits or educational institutions?**
A: Yes! We offer 30% discounts for verified nonprofits and educational institutions. Contact sales@techcorp.com with proof of status.

**Q: How does per-user pricing work?**
A: You're billed for active users in your workspace. Add or remove users anytime; billing adjusts automatically on your next invoice.

### Technical Issues

**Q: I can't log in. What should I do?**
A: 
1. Verify you're using the correct email address
2. Try password reset at app.techcorp.com/reset
3. Check if your account was deactivated (contact admin)
4. Clear browser cache and cookies
5. Try incognito/private browsing mode

**Q: Why aren't I receiving email notifications?**
A:
1. Check Settings > Notifications to ensure email notifications are enabled
2. Check your spam/junk folder
3. Add notifications@techcorp.com to your contacts
4. Verify your email address is correct in Settings > Profile

**Q: The app is running slowly. How can I fix this?**
A:
1. Close unnecessary browser tabs
2. Clear browser cache
3. Disable browser extensions temporarily
4. Check your internet connection speed
5. Try using the desktop app instead of browser

**Q: How do I export my data?**
A: Go to Settings > Data Export. Choose format (CSV, JSON, or PDF) and select date range. Export will be emailed to you within 24 hours.

### Features & Functionality

**Q: What's the difference between Starter and Professional plans?**
A:
- Starter: Limited to 10 users, 5GB storage, basic integrations
- Professional: Unlimited users, 100GB storage, all integrations, priority support, advanced automation

**Q: Can I use TaskFlow Pro offline?**
A: The mobile app supports offline mode. Browser version requires internet connection. Changes sync automatically when you reconnect.

**Q: How many projects can I create?**
A: Unlimited projects on all plans.

**Q: Can I customize the workflow stages?**
A: Yes! Go to Project Settings > Workflow and add/edit/reorder stages. Professional and Enterprise plans support advanced workflow automation.

**Q: Is there a limit on file storage?**
A: Starter: 5GB total, Professional: 100GB total, Enterprise: 1TB+ (custom). Individual file limit: 100MB.

### Security & Privacy

**Q: Is my data encrypted?**
A: Yes. Data is encrypted in transit (TLS 1.3) and at rest (AES-256). We're SOC 2 Type II certified.

**Q: Where are your servers located?**
A: Primary servers in US-East (Virginia) and EU-West (Ireland). Enterprise customers can choose data residency.

**Q: Do you sell my data?**
A: Never. We don't sell, rent, or share customer data with third parties for marketing purposes. See our privacy policy at techcorp.com/privacy.

**Q: Can I enable two-factor authentication?**
A: Yes! Enable 2FA in Settings > Security. We support authenticator apps (Google Authenticator, Authy) and SMS.

---

## Troubleshooting Guide

### Login Issues

**Problem**: "Invalid credentials" error
**Solution**:
1. Verify email address (case-sensitive)
2. Use "Forgot Password" to reset
3. Check if account exists (try signing up - you'll get "email already exists" if it does)
4. Contact support if account was suspended

**Problem**: "Account locked" message
**Solution**: Account locks after 5 failed login attempts. Wait 30 minutes or contact support@techcorp.com to unlock immediately.

### Performance Issues

**Problem**: Slow loading times
**Solution**:
1. Check status.techcorp.com for service status
2. Test internet speed (minimum 5 Mbps recommended)
3. Disable browser extensions
4. Try different browser (Chrome, Firefox, Safari, Edge supported)
5. Clear cache: Settings > Advanced > Clear Cache

**Problem**: Tasks not syncing across devices
**Solution**:
1. Refresh the page/app
2. Check internet connection
3. Log out and log back in
4. Verify you're using the same account on all devices

### Integration Issues

**Problem**: Slack integration not working
**Solution**:
1. Reconnect integration: Settings > Integrations > Slack > Reconnect
2. Verify Slack workspace permissions
3. Check that bot is added to relevant channels
4. Re-authorize if permissions changed

**Problem**: Email-to-task not creating tasks
**Solution**:
1. Verify you're sending to correct address: project-[ID]@yourworkspace.techcorp.com
2. Check spam folder for bounce-back messages
3. Ensure sender email is a workspace member
4. Check project permissions (must have "create task" permission)

### Mobile App Issues

**Problem**: App crashes on startup
**Solution**:
1. Update to latest version (App Store/Play Store)
2. Restart device
3. Clear app cache (Settings > Apps > TaskFlow Pro > Clear Cache)
4. Reinstall app
5. Check device OS version (iOS 14+ or Android 10+ required)

**Problem**: Push notifications not working
**Solution**:
1. Enable notifications in device settings
2. Check in-app notification settings
3. Ensure app has background refresh enabled
4. Log out and log back in

### Billing Issues

**Problem**: Payment failed
**Solution**:
1. Verify card details are correct
2. Check card has sufficient funds
3. Contact your bank (may be blocking international charges)
4. Try alternative payment method
5. Update payment method in Settings > Billing

**Problem**: Charged wrong amount
**Solution**:
1. Check Settings > Billing > Invoice History
2. Verify number of active users
3. Check for mid-cycle upgrades (prorated charges)
4. Contact billing@techcorp.com with invoice number

---

## API Documentation

### Authentication
Use API keys from Settings > API > Generate Key

```
Authorization: Bearer YOUR_API_KEY
```

### Rate Limits
- Free tier: 100 requests/hour
- Professional: 1,000 requests/hour
- Enterprise: 10,000 requests/hour

### Common Endpoints

**Get Tasks**
```
GET /api/v1/projects/{project_id}/tasks
```

**Create Task**
```
POST /api/v1/projects/{project_id}/tasks
{
  "title": "Task name",
  "description": "Task details",
  "assignee_id": "user_123",
  "due_date": "2026-04-15"
}
```

**Update Task**
```
PATCH /api/v1/tasks/{task_id}
{
  "status": "completed"
}
```

Full API documentation: developers.techcorp.com/api

---

## Contact Support

- **Email**: support@techcorp.com (response within 24 hours)
- **Live Chat**: Available in-app (Professional/Enterprise, 9am-6pm EST)
- **Phone**: Enterprise customers only - see your welcome email
- **Help Center**: help.techcorp.com
- **Status Page**: status.techcorp.com
- **Community Forum**: community.techcorp.com
