// Node.js fallback for Python Flask app
const http = require('http');
const port = process.env.PORT || 8000;

const server = http.createServer((req, res) => {
    res.writeHead(200, { 'Content-Type': 'text/html' });
    res.end(`
    <html>
    <head>
        <title>European Travel Planner</title>
        <style>
            body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
            .container { max-width: 600px; margin: 0 auto; }
            .error { color: #d63384; margin: 20px 0; }
            .info { color: #0d6efd; margin: 20px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 European Travel Planner</h1>
            <div class="error">
                <h2>Deployment Issue</h2>
                <p>The Python Flask application couldn't start on Railway.</p>
            </div>
            <div class="info">
                <h3>Alternative Deployment Options:</h3>
                <p><strong>Heroku:</strong> <a href="https://heroku.com/deploy?template=https://github.com/Chedly25/trip">One-Click Deploy</a></p>
                <p><strong>Render:</strong> <a href="https://render.com">Deploy from GitHub</a></p>
                <p><strong>Local:</strong> Clone repo and run <code>python app_runner.py</code></p>
            </div>
            <div class="info">
                <h3>Features Ready:</h3>
                <ul style="text-align: left;">
                    <li>✅ Claude AI integration</li>
                    <li>✅ Real-time route planning</li>
                    <li>✅ Weather and accommodations</li>
                    <li>✅ Interactive maps</li>
                    <li>✅ Production security</li>
                </ul>
            </div>
        </div>
    </body>
    </html>
    `);
});

server.listen(port, '0.0.0.0', () => {
    console.log(`Fallback server running on port ${port}`);
});