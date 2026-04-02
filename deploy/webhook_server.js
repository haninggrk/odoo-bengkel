#!/usr/bin/env node
/**
 * Simple GitHub Webhook Listener for Auto-Pull (Node.js)
 * Listens for push events and pulls the latest code.
 * 
 * Usage:
 *   1. Run: node webhook_server.js
 *   2. Configure GitHub webhook to point to: http://your-server:9000/webhook
 * 
 * No external dependencies - uses only Node.js built-in modules!
 */

const http = require('http');
const crypto = require('crypto');
const { exec } = require('child_process');

// Configuration
const PORT = 9000;
const REPO_PATH = '/opt/odoo-bengkel/addons/odoo-bengkel';
const WEBHOOK_SECRET = process.env.WEBHOOK_SECRET || 'your-secret-here';
const ODOO_SERVICE = 'odoo';  // systemd service name, set to null to skip restart

function verifySignature(payload, signature) {
    if (!signature || WEBHOOK_SECRET === 'your-secret-here') {
        return true; // Skip verification if no secret configured
    }
    
    const hmac = crypto.createHmac('sha256', WEBHOOK_SECRET);
    const digest = 'sha256=' + hmac.update(payload).digest('hex');
    return crypto.timingSafeEqual(Buffer.from(digest), Buffer.from(signature));
}

function runCommand(command) {
    return new Promise((resolve, reject) => {
        exec(command, { cwd: REPO_PATH, timeout: 60000 }, (error, stdout, stderr) => {
            if (error) {
                reject(error);
            } else {
                resolve(stdout + stderr);
            }
        });
    });
}

async function handleWebhook(req, res) {
    let body = '';
    
    req.on('data', chunk => { body += chunk; });
    
    req.on('end', async () => {
        const signature = req.headers['x-hub-signature-256'];
        const event = req.headers['x-github-event'];
        
        // Verify signature
        if (!verifySignature(body, signature)) {
            res.writeHead(403, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: 'Invalid signature' }));
            return;
        }
        
        // Only handle push events
        if (event !== 'push') {
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ message: `Ignored event: ${event}` }));
            return;
        }
        
        console.log(`[${new Date().toISOString()}] Received push event, pulling...`);
        
        try {
            // Git pull
            const pullOutput = await runCommand('git pull origin main');
            console.log('Pull output:', pullOutput);
            
            // Restart Odoo if configured
            let restartOutput = '';
            if (ODOO_SERVICE) {
                try {
                    restartOutput = await runCommand(`sudo systemctl restart ${ODOO_SERVICE}`);
                    console.log('Restart output:', restartOutput);
                } catch (e) {
                    restartOutput = `Restart failed: ${e.message}`;
                    console.error(restartOutput);
                }
            }
            
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({
                status: 'success',
                pull: pullOutput,
                restart: restartOutput
            }));
            
        } catch (error) {
            console.error('Error:', error.message);
            res.writeHead(500, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: error.message }));
        }
    });
}

const server = http.createServer((req, res) => {
    if (req.method === 'POST' && req.url === '/webhook') {
        handleWebhook(req, res);
    } else if (req.method === 'GET' && req.url === '/health') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ status: 'ok' }));
    } else {
        res.writeHead(404);
        res.end('Not found');
    }
});

server.listen(PORT, '0.0.0.0', () => {
    console.log(`Webhook server listening on port ${PORT}`);
    console.log(`Repo path: ${REPO_PATH}`);
    console.log(`Odoo service: ${ODOO_SERVICE || 'disabled'}`);
});
