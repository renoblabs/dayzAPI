import { config } from 'dotenv';

// Load environment variables from .env file if present
config();

// Helper functions for parsing environment variables
const parseNumber = (value: string | undefined, defaultValue: number): number => {
  if (!value) return defaultValue;
  const parsed = parseInt(value, 10);
  return isNaN(parsed) ? defaultValue : parsed;
};

const parseBoolean = (value: string | undefined, defaultValue: boolean): boolean => {
  if (!value) return defaultValue;
  return value.toLowerCase() === 'true';
};

const parseStringArray = (value: string | undefined): string[] => {
  if (!value) return [];
  return value.split(',').map(item => item.trim()).filter(Boolean);
};

// Environment variables with defaults
export const PORT = parseNumber(process.env.PORT, 8080);

export const MONGODB_URI = process.env.MONGODB_URI || 'mongodb://placeholder:27017';
if (MONGODB_URI === 'mongodb://placeholder:27017') {
  console.warn('Warning: Using placeholder MONGODB_URI. Set the MONGODB_URI environment variable for production.');
}

export const DB_NAME = process.env.DB_NAME || 'hivekit';

// SERVER_AUTH can be a single string or comma-separated list
export const SERVER_AUTH = parseStringArray(process.env.SERVER_AUTH);
if (SERVER_AUTH.length === 0) {
  // Generate a random string if not provided
  const randomAuth = Math.random().toString(36).substring(2, 15);
  SERVER_AUTH.push(randomAuth);
  console.warn(`Warning: No SERVER_AUTH provided. Using generated value: ${randomAuth}`);
}

export const REQUEST_LIMIT_RPS = parseNumber(process.env.REQUEST_LIMIT_RPS, 10);
export const BODY_LIMIT_BYTES = parseNumber(process.env.BODY_LIMIT_BYTES, 65536); // 64KB
export const LOG_LEVEL = process.env.LOG_LEVEL || 'info';
export const ALLOW_CLIENT_WRITE = parseBoolean(process.env.ALLOW_CLIENT_WRITE, false);
export const VERSION = process.env.VERSION || 'dev';
export const ALLOWLIST_CIDRS = parseStringArray(process.env.ALLOWLIST_CIDRS);

// Admin dashboard settings
export const ADMIN_ENABLED = parseBoolean(process.env.ADMIN_ENABLED, false);
export const ADMIN_USER    = process.env.ADMIN_USER || '';
export const ADMIN_PASS    = process.env.ADMIN_PASS || '';

// Export the config as a single object for convenience
export default {
  PORT,
  MONGODB_URI,
  DB_NAME,
  SERVER_AUTH,
  REQUEST_LIMIT_RPS,
  BODY_LIMIT_BYTES,
  LOG_LEVEL,
  ALLOW_CLIENT_WRITE,
  VERSION,
  ALLOWLIST_CIDRS,
  ADMIN_ENABLED,
  ADMIN_USER,
  ADMIN_PASS
};
