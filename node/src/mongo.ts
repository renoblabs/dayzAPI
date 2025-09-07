import { MongoClient, Db, Collection } from 'mongodb';
import { MONGODB_URI, DB_NAME } from './config.js';
import pino from 'pino';

const logger = pino({ level: process.env.LOG_LEVEL || 'info' });

// Singleton pattern for MongoDB client
let client: MongoClient | null = null;
let db: Db | null = null;
let isConnecting = false;
let connectionPromise: Promise<Db> | null = null;

/**
 * Get MongoDB database instance, creating connection if needed
 */
export async function getDb(): Promise<Db> {
  if (db) return db;
  if (connectionPromise) return connectionPromise;
  
  isConnecting = true;
  connectionPromise = connectToMongo();
  return connectionPromise;
}

/**
 * Connect to MongoDB and initialize database
 */
async function connectToMongo(): Promise<Db> {
  try {
    logger.info(`Connecting to MongoDB at ${MONGODB_URI.replace(/\/\/([^:]+):([^@]+)@/, '//***:***@')}`);
    
    client = new MongoClient(MONGODB_URI);
    await client.connect();
    
    db = client.db(DB_NAME);
    logger.info(`Connected to MongoDB database: ${DB_NAME}`);
    
    // Ensure indexes
    await ensureIndexes();
    
    // Handle connection errors and cleanup
    client.on('error', (err) => {
      logger.error({ err }, 'MongoDB connection error');
      disconnectMongo();
    });
    
    // Handle app shutdown
    process.on('SIGINT', async () => {
      await disconnectMongo();
      process.exit(0);
    });
    
    process.on('SIGTERM', async () => {
      await disconnectMongo();
      process.exit(0);
    });
    
    return db;
  } catch (err) {
    logger.error({ err }, 'Failed to connect to MongoDB');
    isConnecting = false;
    connectionPromise = null;
    throw err;
  }
}

/**
 * Disconnect from MongoDB
 */
export async function disconnectMongo(): Promise<void> {
  if (client) {
    try {
      await client.close();
      logger.info('Disconnected from MongoDB');
    } catch (err) {
      logger.error({ err }, 'Error disconnecting from MongoDB');
    } finally {
      client = null;
      db = null;
      isConnecting = false;
      connectionPromise = null;
    }
  }
}

/**
 * Ensure all required indexes exist
 */
async function ensureIndexes(): Promise<void> {
  try {
    const db = await getDb();
    
    // Objects collection - compound index on ObjectId and Mod
    const objectsCollection = db.collection('Objects');
    await objectsCollection.createIndex(
      { ObjectId: 1, Mod: 1 },
      { unique: true, background: true }
    );
    logger.info('Ensured index on Objects collection: {ObjectId:1, Mod:1}');
    
    // Additional indexes for other collections can be added here
    
  } catch (err) {
    logger.error({ err }, 'Failed to create indexes');
    throw err;
  }
}

/**
 * Get Objects collection
 */
export async function getObjectsCollection(): Promise<Collection> {
  const db = await getDb();
  return db.collection('Objects');
}

/**
 * Get Players collection
 */
export async function getPlayersCollection(): Promise<Collection> {
  const db = await getDb();
  return db.collection('Players');
}

/**
 * Get a collection by name
 */
export async function getCollection(name: string): Promise<Collection> {
  const db = await getDb();
  return db.collection(name);
}

// Export the connection status checker
export function isConnected(): boolean {
  return client !== null && db !== null;
}
