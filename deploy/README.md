# Auto-Deploy Setup Guide

This sets up automatic deployment when you push to GitHub.

## Quick Setup on Server

### 1. Install Flask
```bash
pip3 install flask
```

### 2. Copy the service file
```bash
cp /opt/odoo-bengkel/addons/odoo-bengkel/deploy/webhook.service /etc/systemd/system/
```

### 3. Edit the secret (important!)
```bash
nano /etc/systemd/system/webhook.service
# Change: Environment=WEBHOOK_SECRET=your-secret-here
# To something secure like: Environment=WEBHOOK_SECRET=my-super-secret-key-123
```

### 4. Configure the webhook script
Edit `/opt/odoo-bengkel/addons/odoo-bengkel/deploy/webhook_server.py`:
- `REPO_PATH` - path to your addon folder
- `ODOO_SERVICE` - your Odoo systemd service name (or `None` to skip restart)

### 5. Start the service
```bash
systemctl daemon-reload
systemctl enable webhook
systemctl start webhook
systemctl status webhook
```

### 6. Open firewall port (if needed)
```bash
ufw allow 9000
```

## Configure GitHub Webhook

1. Go to: https://github.com/haninggrk/odoo-bengkel/settings/hooks
2. Click **Add webhook**
3. Settings:
   - **Payload URL**: `http://YOUR_SERVER_IP:9000/webhook`
   - **Content type**: `application/json`
   - **Secret**: Same secret you set in step 3
   - **Events**: Just the push event
4. Click **Add webhook**

## Test It

Push a change and check:
```bash
# View logs
journalctl -u webhook -f

# Manual test
curl http://localhost:9000/health
```

## Troubleshooting

- **Check if running**: `systemctl status webhook`
- **View logs**: `journalctl -u webhook -n 50`
- **Manual pull test**: `cd /opt/odoo-bengkel/addons/odoo-bengkel && git pull`
