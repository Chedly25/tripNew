const { spawn } = require('child_process');
const path = require('path');

// Try different Python executables
const pythonCommands = ['python3', 'python', '/usr/bin/python3', '/usr/bin/python'];

function findPython() {
    return new Promise((resolve, reject) => {
        let tried = 0;
        
        pythonCommands.forEach(cmd => {
            const child = spawn(cmd, ['--version'], { stdio: 'pipe' });
            
            child.on('close', (code) => {
                tried++;
                if (code === 0) {
                    console.log(`Found Python: ${cmd}`);
                    resolve(cmd);
                } else if (tried === pythonCommands.length) {
                    reject(new Error('No Python found'));
                }
            });
            
            child.on('error', () => {
                tried++;
                if (tried === pythonCommands.length) {
                    reject(new Error('No Python found'));
                }
            });
        });
    });
}

async function startApp() {
    try {
        const pythonCmd = await findPython();
        console.log(`Starting Flask app with ${pythonCmd}`);
        
        const child = spawn(pythonCmd, ['wsgi.py'], {
            stdio: 'inherit',
            env: { ...process.env }
        });
        
        child.on('close', (code) => {
            console.log(`Python app exited with code ${code}`);
            process.exit(code);
        });
        
    } catch (error) {
        console.error('Failed to start Python app:', error.message);
        
        // Fallback - try to run directly
        console.log('Attempting direct Python execution...');
        require('./wsgi.js'); // We'll create this
    }
}

startApp();