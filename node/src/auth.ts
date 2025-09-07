import { Request } from 'express';
import { verify } from 'jsonwebtoken';
import pino from 'pino';

const logger = pino({ level: process.env.LOG_LEVEL || 'info' });

/**
 * Check if server auth token is valid
 * Matches original CheckServerAuth behavior
 */
export function checkServerAuth(token: string | undefined, serverAuth: string[]): boolean {
  if (!token) return false;
  
  // Check if token is in serverAuth array
  return serverAuth.includes(token);
}

/**
 * Verify JWT token using the first server auth as secret
 * Matches original CheckAuth behavior
 */
export function verifyJwt(token: string | undefined, serverAuth: string[]): Promise<boolean> {
  if (!token || serverAuth.length === 0) return Promise.resolve(false);
  
  // Use first server auth as signing secret
  const signingSecret = serverAuth[0];
  
  return new Promise((resolve) => {
    verify(token, signingSecret, (err, decoded) => {
      if (err) {
        if (err.name === "TokenExpiredError") {
          logger.warn(`Error: Auth Token is expired, it expired at ${err.expiredAt}`);
        } else if (err.name === "JsonWebTokenError") {
          logger.warn("Auth Token is not valid");
        } else {
          logger.warn(err);
        }
        resolve(false);
      } else {
        resolve(true);
      }
    });
  });
}

/**
 * Extract auth key from request headers
 * Simplified version of original ExtractAuthKey middleware
 */
export function extractAuth(req: Request): string {
  return req.headers['auth-key'] as string || '';
}

/**
 * Generate a JWT token for a player
 * Matches original makeAuthToken behavior
 */
export function makeAuthToken(guid: string, serverAuth: string[]): string {
  if (serverAuth.length === 0) {
    throw new Error('No server auth tokens configured');
  }
  
  const jwt = require('jsonwebtoken');
  const player = { GUID: guid };
  
  // Token expires in 46.5 minutes (2800 seconds)
  // Tokens renew every 21-23 minutes ensuring that if the API is down
  // at the time of renewal, token will last till next retry
  return jwt.sign(player, serverAuth[0], { expiresIn: 2800 });
}

/**
 * Extract auth key middleware
 * Sets 'auth-key' header from various sources
 */
export function extractAuthMiddleware(req: Request, res: any, next: () => void): void {
  let contentType = req.headers['content-type'] || "application/json";
  
  if (typeof contentType === 'string' && contentType.match(/^(text\/|application\/|multipart\/|audio\/|image\/|video\/)/i)) {
    req.headers['auth-key'] = req.headers['auth-key'] || '';
  } else {
    req.headers['auth-key'] = req.headers['auth-key'] || req.headers['content-type'] || '';
    req.headers['content-type'] = 'application/json';
  }
  
  next();
}
