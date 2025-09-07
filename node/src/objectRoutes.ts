import { Router, Request, Response } from 'express';
import { getObjectsCollection } from './mongo.js';
import { checkServerAuth, verifyJwt, extractAuth } from './auth.js';
import { isObject, isArray, isEmpty, makeObjectId, sanitizeUpdatePath, parseMaybeNumber } from './utils.js';
import { ALLOW_CLIENT_WRITE, SERVER_AUTH } from './config.js';
import pino from 'pino';

const logger = pino({ level: process.env.LOG_LEVEL || 'info' });
const router = Router();

// Load object route
router.post('/Load/:ObjectId/:mod', async (req: Request, res: Response) => {
  const { ObjectId, mod } = req.params;
  const auth = extractAuth(req);
  const body = req.body;

  try {
    // Check authentication
    if (!checkServerAuth(auth, SERVER_AUTH) && !(await verifyJwt(auth, SERVER_AUTH))) {
      logger.warn(`AUTH ERROR: Bad Auth Token for ${req.url}`);
      res.status(401).json(body);
      return;
    }

    const collection = await getObjectsCollection();
    const query = { ObjectId, Mod: mod };
    const result = await collection.findOne(query);

    if (!result) {
      // Document not found - create if allowed
      if ((checkServerAuth(auth, SERVER_AUTH) || ALLOW_CLIENT_WRITE) && !isEmpty(body)) {
        let newObjectId = ObjectId;
        
        // Generate new ID if requested
        if (ObjectId === "NewObject") {
          newObjectId = makeObjectId();
          body.ObjectId = newObjectId;
          logger.info(`Item called as NewObject for ${mod} Generating ID ${newObjectId}`);
        }
        
        logger.info(`Can't find Object for mod ${mod} with ID ${ObjectId} Creating it now`);
        const doc = { ObjectId: newObjectId, Mod: mod, Data: body };
        await collection.insertOne(doc);
      }
      
      res.status(201).json(body);
      return;
    }
    
    // Document found
    if (result.Data !== undefined) {
      res.status(200).json(result.Data);
    } else {
      res.status(203).json(body);
    }
  } catch (err) {
    logger.error({ err }, `ERROR in /Load/${ObjectId}/${mod}`);
    res.status(203).json(body);
  }
});

// Save object route
router.post('/Save/:ObjectId/:mod', async (req: Request, res: Response) => {
  const { ObjectId, mod } = req.params;
  const auth = extractAuth(req);
  const body = req.body;

  try {
    // Check authentication
    if (!checkServerAuth(auth, SERVER_AUTH) && !(await verifyJwt(auth, SERVER_AUTH) && ALLOW_CLIENT_WRITE)) {
      logger.warn(`AUTH ERROR: Bad Auth Token for ${req.url}`);
      res.status(401).json(body);
      return;
    }

    const collection = await getObjectsCollection();
    let objectId = ObjectId;

    // Generate new ID if requested
    if (objectId === "NewObject") {
      objectId = makeObjectId();
      body.ObjectId = objectId;
    }

    const query = { ObjectId: objectId, Mod: mod };
    const updateDoc = { 
      $set: { 
        ObjectId: objectId, 
        Mod: mod, 
        Data: body 
      } 
    };
    const options = { upsert: true };

    const result = await collection.updateOne(query, updateDoc, options);
    
    if (result.matchedCount === 1 || result.upsertedCount === 1) {
      logger.info(`Updated ${mod} Data for Object: ${objectId}`);
      res.status(201).json(body);
    } else {
      logger.warn(`Error with Updating ${mod} Data for Object: ${objectId}`);
      res.status(203).json(body);
    }
  } catch (err) {
    logger.error({ err }, `ERROR in /Save/${ObjectId}/${mod}`);
    res.status(203).json(body);
  }
});

// Update object route
router.post('/Update/:ObjectId/:mod', async (req: Request, res: Response) => {
  const { ObjectId, mod } = req.params;
  const auth = extractAuth(req);
  const { Element, Value, Operation = "set" } = req.body;

  try {
    // Check authentication
    if (!checkServerAuth(auth, SERVER_AUTH) && !(await verifyJwt(auth, SERVER_AUTH) && ALLOW_CLIENT_WRITE)) {
      logger.warn(`AUTH ERROR: Bad Auth Token for ${req.url}`);
      res.status(401).json({ 
        Status: "Error", 
        Error: "Invalid Auth", 
        Element: "", 
        Mod: mod, 
        ID: ObjectId 
      });
      return;
    }

    const collection = await getObjectsCollection();
    const query = { ObjectId, Mod: mod };
    const options = { upsert: false };

    // Sanitize element path
    const sanitizedElement = sanitizeUpdatePath(Element);
    
    // Process value based on type
    let processedValue;
    if (isObject(Value) || isArray(Value)) {
      processedValue = Value;
    } else {
      processedValue = parseMaybeNumber(Value);
    }

    // Create update document based on operation
    const updatePath = `Data.${sanitizedElement}`;
    let updateDoc: any = {};
    
    switch (Operation) {
      case "pull":
        updateDoc = { $pull: { [updatePath]: processedValue } };
        break;
      case "push":
        updateDoc = { $push: { [updatePath]: processedValue } };
        break;
      case "unset":
        updateDoc = { $unset: { [updatePath]: processedValue } };
        break;
      case "mul":
        updateDoc = { $mul: { [updatePath]: processedValue } };
        break;
      case "rename":
        updateDoc = { $rename: { [updatePath]: processedValue } };
        break;
      case "pullAll":
        updateDoc = { $pullAll: { [updatePath]: processedValue } };
        break;
      default: // "set" is default
        updateDoc = { $set: { [updatePath]: processedValue } };
    }

    const result = await collection.updateOne(query, updateDoc, options);
    
    if (result.matchedCount >= 1) {
      logger.info(`Updated ${Element} for ${mod} Data for ObjectId: ${ObjectId}`);
      res.status(200).json({ 
        Status: "Success", 
        Element, 
        Mod: mod, 
        ID: ObjectId 
      });
    } else {
      logger.warn(`Error with Updating ${Element} for ${mod} Data for ObjectId: ${ObjectId}`);
      res.status(203).json({ 
        Status: "NotFound", 
        Element, 
        Mod: mod, 
        ID: ObjectId 
      });
    }
  } catch (err) {
    logger.error({ err }, `ERROR in /Update/${ObjectId}/${mod}`);
    res.status(203).json({ 
      Status: "Error", 
      Element: req.body.Element, 
      Mod: mod, 
      ID: ObjectId 
    });
  }
});

export default router;
