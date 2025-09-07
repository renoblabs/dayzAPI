import { Router, Request, Response, NextFunction } from 'express';
import { ADMIN_ENABLED, ADMIN_USER, ADMIN_PASS } from './config.js';
import { getObjectsCollection } from './mongo.js';
import pino from 'pino';

const logger = pino({ level: process.env.LOG_LEVEL || 'info' });
const router = Router();

// If admin is disabled, return 404 for all routes
if (!ADMIN_ENABLED) {
  router.use('*', (_req: Request, res: Response) => {
    res.status(404).send('Not Found');
  });
} else {
  // Basic Auth middleware
  router.use((req: Request, res: Response, next: NextFunction) => {
    // Skip auth check for assets if needed
    if (req.path.startsWith('/assets/')) {
      return next();
    }

    const authHeader = req.headers.authorization;
    
    if (!authHeader || !authHeader.startsWith('Basic ')) {
      res.status(401)
        .set('WWW-Authenticate', 'Basic realm="HiveKit Admin"')
        .send('Authentication required');
      return;
    }

    const base64Credentials = authHeader.split(' ')[1];
    const credentials = Buffer.from(base64Credentials, 'base64').toString('utf-8');
    const [username, password] = credentials.split(':');

    if (username !== ADMIN_USER || password !== ADMIN_PASS) {
      logger.warn({ ip: req.ip }, 'Failed admin login attempt');
      res.status(401)
        .set('WWW-Authenticate', 'Basic realm="HiveKit Admin"')
        .send('Invalid credentials');
      return;
    }

    next();
  });

  // Admin home page
  router.get('/', (_req: Request, res: Response) => {
    res.send(`
      <!DOCTYPE html>
      <html lang="en">
      <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>HiveKit Admin</title>
        <style>
          body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
          }
          h1 {
            border-bottom: 1px solid #eee;
            padding-bottom: 10px;
          }
          .search-form {
            background: #f5f5f5;
            padding: 15px;
            border-radius: 4px;
            margin-bottom: 20px;
          }
          .form-group {
            margin-bottom: 10px;
          }
          label {
            display: inline-block;
            width: 80px;
          }
          input, button {
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
          }
          button {
            background: #4a90e2;
            color: white;
            border: none;
            cursor: pointer;
          }
          button:hover {
            background: #357ae8;
          }
          table {
            width: 100%;
            border-collapse: collapse;
          }
          th, td {
            text-align: left;
            padding: 12px;
            border-bottom: 1px solid #ddd;
          }
          th {
            background-color: #f2f2f2;
          }
          .json-viewer {
            margin-top: 20px;
            background: #f8f8f8;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 10px;
            white-space: pre-wrap;
            font-family: monospace;
            max-height: 400px;
            overflow: auto;
          }
          .loading {
            text-align: center;
            padding: 20px;
            font-style: italic;
            color: #666;
          }
          .error {
            background: #ffebee;
            color: #c62828;
            padding: 10px;
            border-radius: 4px;
            margin-bottom: 20px;
          }
          .actions {
            display: flex;
            gap: 5px;
          }
        </style>
      </head>
      <body>
        <h1>HiveKit Admin</h1>
        
        <div class="search-form">
          <div class="form-group">
            <label for="mod">Mod:</label>
            <input type="text" id="mod" placeholder="Filter by mod">
          </div>
          
          <div class="form-group">
            <label for="query">ObjectId:</label>
            <input type="text" id="query" placeholder="Search by ObjectId prefix">
          </div>
          
          <div class="form-group">
            <label for="limit">Limit:</label>
            <input type="number" id="limit" value="50" min="1" max="200">
          </div>
          
          <button id="search-btn">Search</button>
        </div>
        
        <div id="error" class="error" style="display: none;"></div>
        
        <div id="results">
          <div id="loading" class="loading" style="display: none;">Loading...</div>
          <table id="results-table" style="display: none;">
            <thead>
              <tr>
                <th>ObjectId</th>
                <th>Mod</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody id="results-body"></tbody>
          </table>
        </div>
        
        <div id="json-viewer" class="json-viewer" style="display: none;"></div>
        
        <script>
          document.addEventListener('DOMContentLoaded', function() {
            const searchBtn = document.getElementById('search-btn');
            const modInput = document.getElementById('mod');
            const queryInput = document.getElementById('query');
            const limitInput = document.getElementById('limit');
            const resultsTable = document.getElementById('results-table');
            const resultsBody = document.getElementById('results-body');
            const loadingEl = document.getElementById('loading');
            const errorEl = document.getElementById('error');
            const jsonViewer = document.getElementById('json-viewer');
            
            // Initial search on page load
            fetchObjects();
            
            // Search button click
            searchBtn.addEventListener('click', function() {
              fetchObjects();
            });
            
            function fetchObjects() {
              const mod = modInput.value.trim();
              const query = queryInput.value.trim();
              const limit = Math.min(Math.max(parseInt(limitInput.value) || 50, 1), 200);
              
              // Update UI
              errorEl.style.display = 'none';
              resultsTable.style.display = 'none';
              loadingEl.style.display = 'block';
              jsonViewer.style.display = 'none';
              
              // Build query string
              const params = new URLSearchParams();
              if (mod) params.append('mod', mod);
              if (query) params.append('q', query);
              params.append('limit', limit.toString());
              
              // Fetch data
              fetch(\`/admin/api/objects?\${params.toString()}\`)
                .then(response => {
                  if (!response.ok) {
                    throw new Error(\`HTTP error! Status: \${response.status}\`);
                  }
                  return response.json();
                })
                .then(data => {
                  displayResults(data);
                })
                .catch(error => {
                  errorEl.textContent = \`Error: \${error.message}\`;
                  errorEl.style.display = 'block';
                  loadingEl.style.display = 'none';
                });
            }
            
            function displayResults(data) {
              // Clear previous results
              resultsBody.innerHTML = '';
              
              // Update UI
              loadingEl.style.display = 'none';
              
              if (data.items.length === 0) {
                errorEl.textContent = 'No results found.';
                errorEl.style.display = 'block';
                return;
              }
              
              // Display results
              data.items.forEach(item => {
                const row = document.createElement('tr');
                
                const idCell = document.createElement('td');
                idCell.textContent = item.ObjectId;
                row.appendChild(idCell);
                
                const modCell = document.createElement('td');
                modCell.textContent = item.Mod;
                row.appendChild(modCell);
                
                const actionsCell = document.createElement('td');
                actionsCell.className = 'actions';
                
                const viewBtn = document.createElement('button');
                viewBtn.textContent = 'View Data';
                viewBtn.addEventListener('click', function() {
                  jsonViewer.textContent = JSON.stringify(item.Data, null, 2);
                  jsonViewer.style.display = 'block';
                });
                actionsCell.appendChild(viewBtn);
                
                row.appendChild(actionsCell);
                resultsBody.appendChild(row);
              });
              
              resultsTable.style.display = 'table';
            }
          });
        </script>
      </body>
      </html>
    `);
  });

  // API endpoint to get objects
  router.get('/api/objects', async (req: Request, res: Response) => {
    try {
      const mod = req.query.mod as string;
      const query = req.query.q as string;
      const limit = Math.min(Math.max(parseInt(req.query.limit as string) || 50, 1), 200);
      
      // Build filter
      const filter: any = {};
      
      if (mod) {
        filter.Mod = mod;
      }
      
      if (query) {
        // Escape special regex characters to prevent ReDoS
        const escapedQuery = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        filter.ObjectId = { $regex: `^${escapedQuery}`, $options: 'i' };
      }
      
      const collection = await getObjectsCollection();
      
      // Get total count (without limit)
      const total = await collection.countDocuments(filter);
      
      // Get items with limit
      const items = await collection
        .find(filter)
        .limit(limit)
        .toArray();
      
      res.json({
        items,
        total
      });
    } catch (err) {
      logger.error({ err }, 'Error fetching objects for admin');
      res.status(500).json({ error: 'Failed to fetch objects' });
    }
  });
}

export default router;
