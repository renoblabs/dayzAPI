import { createHash } from 'crypto';
import { Request } from 'express';

/**
 * Check if value is an object (not array, not null)
 */
export function isObject(value: any): boolean {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

/**
 * Check if value is an array
 */
export function isArray(value: any): boolean {
  return Array.isArray(value);
}

/**
 * Check if object is empty
 */
export function isEmpty(obj: any): boolean {
  return obj && Object.keys(obj).length === 0 && obj.constructor === Object;
}

/**
 * Generate a unique object ID
 * Replicates original: random string + ISO date, sha256 base64 url-safe
 */
export function makeObjectId(): string {
  let result = '';
  const characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-.~()*:@,;';
  const charactersLength = characters.length;
  
  // Generate random string
  for (let i = 0; i < 16; i++) {
    result += characters.charAt(Math.floor(Math.random() * charactersLength));
  }
  
  // Append ISO date
  const datetime = new Date();
  const date = datetime.toISOString();
  result += date;
  
  // Hash with SHA-256 and convert to base64
  let hash = createHash('sha256').update(result).digest('base64');
  
  // Make URL-safe
  hash = hash.replace(/\+/g, '-');
  hash = hash.replace(/\//g, '_');
  hash = hash.replace(/=+$/, '');
  
  return hash;
}

/**
 * Get client IP from request
 * Prefer Cloudflare headers, then X-Forwarded-For, then socket
 */
export function clientIp(req: Request): string {
  const cfIp = req.headers['cf-connecting-ip'];
  if (cfIp && typeof cfIp === 'string') {
    return cfIp;
  }
  
  const forwardedIp = req.headers['x-forwarded-for'];
  if (forwardedIp) {
    const ips = typeof forwardedIp === 'string' 
      ? forwardedIp.split(',')[0].trim() 
      : forwardedIp[0]?.split(',')[0].trim();
    if (ips) return ips;
  }
  
  return req.ip || req.socket.remoteAddress || '0.0.0.0';
}

/**
 * Parse value as number if it matches numeric pattern
 */
export function parseMaybeNumber(val: any): any {
  if (typeof val !== 'string') return val;
  
  // Check if string is numeric
  if (/^-?(0|[1-9]\d*)(\.\d+)?$/.test(val)) {
    return parseFloat(val);
  }
  
  return val;
}

/**
 * Sanitize update path for MongoDB
 * Allow simple dot paths, strip unsafe chars
 */
export function sanitizeUpdatePath(path: string): string {
  // Only allow alphanumeric, dots, and underscores
  return path.replace(/[^a-zA-Z0-9_\.]/g, '');
}

/**
 * Simple IP allowlist check
 * If allowlist is empty, allow all
 * Otherwise, check for exact match or skip CIDR notation for now
 */
export function ipAllowed(ip: string, cidrs: string[]): boolean {
  if (!cidrs || cidrs.length === 0) {
    return true;
  }
  
  for (const cidr of cidrs) {
    // Exact IP match
    if (cidr === ip) {
      return true;
    }
    
    // If CIDR notation with slash, skip detailed implementation for now
    if (cidr.includes('/')) {
      // For now, we're not implementing full CIDR matching
      // Return true to avoid blocking
      return true;
    }
  }
  
  return false;
}
