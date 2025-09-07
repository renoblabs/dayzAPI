import express, { Request, Response, NextFunction } from 'express';
import helmet from 'helmet';
import rateLimit from 'express-rate-limit';
import pino from 'pino';
import pinoHttp from 'pino-http';
import { randomUUID } from 'crypto';
import { Registry, collectDefaultMetrics } from 'prom-client';
import { PORT, REQUEST_LIMIT_RPS, BODY_LIMIT_BYTES, VERSION, ALLOWLIST_CIDRS } from './config.js';
import { clientIp, ipAllowed } from './utils.js';
import objectRoutes from './objectRoutes.js';
import { extractAuthMiddleware } from './auth.js';
import { getDb } from './mongo.js';
import adminRouter from './admin.js';

const app = express();
const logger = pino({ level: process.env.LOG_LEVEL || 'info' });

const metricsRegistry = new Registry();
collectDefaultMetrics({ register: metricsRegistry });

app.use(helmet());

app.use((req: Request, res: Response, next: NextFunction) => {
  const id = req.headers['x-request-id'] as string || randomUUID();
  (req as any).id = id;
  res.setHeader('X-Request-ID', id);
  next();
});

app.use(pinoHttp({ logger }));

app.use((req: Request, res: Response, next: NextFunction) => {
  if (!ipAllowed(clientIp(req), ALLOWLIST_CIDRS)) {
    res.status(403).json({ error: 'IP not allowed' });
    return;
  }
  next();
});

app.use(rateLimit({
  windowMs: 1000,
  max: REQUEST_LIMIT_RPS,
  standardHeaders: true,
  legacyHeaders: false
}));

app.use(express.json({ limit: BODY_LIMIT_BYTES }));

app.use(extractAuthMiddleware);

app.get('/health', async (_req: Request, res: Response) => {
  try {
    await getDb();
    res.json({ ok: true, version: VERSION });
  } catch {
    res.status(500).json({ ok: false, version: VERSION });
  }
});

app.get('/metrics', async (_req: Request, res: Response) => {
  res.set('Content-Type', metricsRegistry.contentType);
  res.end(await metricsRegistry.metrics());
});

// optional read-only admin dashboard
app.use('/admin', adminRouter);

app.use('/Object', objectRoutes);

app.use((err: any, _req: Request, res: Response, _next: NextFunction) => {
  logger.error({ err }, 'Unhandled error');
  if (err?.type === 'entity.too.large') {
    res.status(413).json({ error: `Request body exceeds limit of ${BODY_LIMIT_BYTES} bytes` });
    return;
  }
  res.status(500).json({ error: 'Internal Server Error' });
});

app.listen(PORT, '0.0.0.0', async () => {
  try {
    await getDb();
    logger.info({ port: PORT, version: VERSION }, 'Server started');
  } catch (err) {
    logger.error({ err }, 'Failed to connect to MongoDB on startup');
  }
});
