#!/usr/bin/env python3
"""
Simple GitHub Webhook Listener for Auto-Pull
Listens for push events and pulls the latest code.

Usage:
    1. Install: pip3 install flask
    2. Run: python3 webhook_server.py
    3. Configure GitHub webhook to point to: http://your-server:9000/webhook
"""

import subprocess
import os
import hmac
import hashlib
from flask import Flask, request, jsonify

app = Flask(__name__)

# Configuration
REPO_PATH = "/opt/odoo-bengkel/addons/odoo-bengkel"
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "your-secret-here")  # Set this!
ODOO_SERVICE = "odoo"  # systemd service name, set to None if not using systemd

def verify_signature(payload_body, signature_header):
    """Verify GitHub webhook signature."""
    if not signature_header:
        return False
    
    hash_object = hmac.new(
        WEBHOOK_SECRET.encode('utf-8'),
        msg=payload_body,
        digestmod=hashlib.sha256
    )
    expected_signature = "sha256=" + hash_object.hexdigest()
    return hmac.compare_digest(expected_signature, signature_header)

@app.route('/webhook', methods=['POST'])
def webhook():
    # Verify signature (optional but recommended)
    signature = request.headers.get('X-Hub-Signature-256')
    if WEBHOOK_SECRET != "your-secret-here":
        if not verify_signature(request.data, signature):
            return jsonify({"error": "Invalid signature"}), 403
    
    # Check if it's a push event
    event = request.headers.get('X-GitHub-Event')
    if event != 'push':
        return jsonify({"message": f"Ignored event: {event}"}), 200
    
    # Pull the latest code
    try:
        os.chdir(REPO_PATH)
        
        # Git pull
        result = subprocess.run(
            ['git', 'pull', 'origin', 'main'],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        pull_output = result.stdout + result.stderr
        
        # Restart Odoo service if configured
        restart_output = ""
        if ODOO_SERVICE:
            restart_result = subprocess.run(
                ['sudo', 'systemctl', 'restart', ODOO_SERVICE],
                capture_output=True,
                text=True,
                timeout=30
            )
            restart_output = restart_result.stdout + restart_result.stderr
        
        return jsonify({
            "status": "success",
            "pull": pull_output,
            "restart": restart_output
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    print(f"Webhook server listening on port 9000")
    print(f"Repo path: {REPO_PATH}")
    app.run(host='0.0.0.0', port=9000)
