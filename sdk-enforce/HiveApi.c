class HiveApi
{
    static string HIVE_URL = "https://hive.placeholder";
    static string HIVE_KEY = "changeme";
    static int HIVE_WRITES_ENABLED = 0;
    static int HIVE_TIMEOUT_MS = 800;
    static int HIVE_RETRY = 1;
    static int HIVE_LOG_INTERVAL_MS = 60000;
    static int BODY_LIMIT_BYTES = 65536;
    
    static ref map<string, string> s_kvCache = new map<string, string>();
    static ref map<string, int> s_lastLog = new map<string, int>();
    
    static bool SaveKV(string key, string json)
    {
        if (HIVE_WRITES_ENABLED == 0)
        {
            return true;
        }
        
        if (json.Length() > BODY_LIMIT_BYTES)
        {
            LogOnce("payload_size", "HiveApi: Payload size exceeds limit");
            return false;
        }
        
        string url = HIVE_URL + "/v1/state/" + key;
        
        RestContext ctx = GetRestContext();
        RestRequest req = new RestRequest(url, ERestMethod.PUT);
        req.SetHeader("X-API-Key", HIVE_KEY);
        req.SetHeader("Content-Type", "application/json");
        req.SetTimeout(HIVE_TIMEOUT_MS);
        
        string body = "{\"v\":" + json + "}";
        req.SetBody(body);
        
        HiveRestCb callback = new HiveRestCb();
        callback.m_onSuccess = func(RestResponse response)
        {
            s_kvCache.Set(key, json);
        };
        
        callback.m_onError = func(RestResponse response)
        {
            if (HIVE_RETRY > 0)
            {
                int jitter = Math.RandomInt(50, 150);
                Enqueue(func() { SaveKV(key, json); }, 100 + jitter);
            }
            
            LogOnce("save_error", "HiveApi: Failed to save KV for key: " + key);
        };
        
        ctx.Send(req, callback);
        return true;
    }
    
    static string LoadKV(string key)
    {
        string cachedValue = "";
        if (s_kvCache.Find(key, cachedValue))
        {
            return cachedValue;
        }
        
        string url = HIVE_URL + "/v1/state/" + key;
        
        RestContext ctx = GetRestContext();
        RestRequest req = new RestRequest(url, ERestMethod.GET);
        req.SetHeader("X-API-Key", HIVE_KEY);
        req.SetTimeout(HIVE_TIMEOUT_MS);
        
        HiveRestCb callback = new HiveRestCb();
        callback.m_onSuccess = func(RestResponse response)
        {
            string responseBody = response.GetBody();
            s_kvCache.Set(key, responseBody);
        };
        
        callback.m_onError = func(RestResponse response)
        {
            if (response.GetCode() != 404 && HIVE_RETRY > 0)
            {
                int jitter = Math.RandomInt(50, 150);
                Enqueue(func() { LoadKV(key); }, 100 + jitter);
            }
            
            if (response.GetCode() != 404)
            {
                LogOnce("load_error", "HiveApi: Failed to load KV for key: " + key);
            }
        };
        
        ctx.Send(req, callback);
        return "";
    }
    
    static bool CreateTransfer(string steamId, string src, string dst, string payloadJson, out string token)
    {
        token = "";
        
        if (HIVE_WRITES_ENABLED == 0)
        {
            return true;
        }
        
        if (payloadJson.Length() > BODY_LIMIT_BYTES)
        {
            LogOnce("payload_size", "HiveApi: Payload size exceeds limit");
            return false;
        }
        
        string url = HIVE_URL + "/v1/transfer";
        
        RestContext ctx = GetRestContext();
        RestRequest req = new RestRequest(url, ERestMethod.POST);
        req.SetHeader("X-API-Key", HIVE_KEY);
        req.SetHeader("Content-Type", "application/json");
        req.SetTimeout(HIVE_TIMEOUT_MS);
        
        string body = "{\"steam_id\":\"" + steamId + "\",\"src_server\":\"" + src + "\",\"dst_server\":\"" + dst + "\",\"payload\":" + payloadJson + ",\"ttl_minutes\":60}";
        req.SetBody(body);
        
        HiveRestCb callback = new HiveRestCb();
        callback.m_onSuccess = func(RestResponse response)
        {
            string responseBody = response.GetBody();
            JsonReader reader = new JsonReader();
            ref JsonValue jsonData = reader.ReadFromString(responseBody);
            
            if (jsonData && jsonData.IsObject())
            {
                JsonValue tokenValue = jsonData.GetMember("token");
                if (tokenValue && tokenValue.IsString())
                {
                    token = tokenValue.GetString();
                }
            }
        };
        
        callback.m_onError = func(RestResponse response)
        {
            if (HIVE_RETRY > 0)
            {
                int jitter = Math.RandomInt(50, 150);
                Enqueue(func() { CreateTransfer(steamId, src, dst, payloadJson, token); }, 100 + jitter);
            }
            
            LogOnce("transfer_error", "HiveApi: Failed to create transfer");
        };
        
        ctx.Send(req, callback);
        return true;
    }
    
    static bool ClaimTransfer(string steamId, string token, out string payloadJson)
    {
        payloadJson = "";
        
        if (token.Length() == 0)
        {
            return false;
        }
        
        string url = HIVE_URL + "/v1/transfer/claim";
        
        RestContext ctx = GetRestContext();
        RestRequest req = new RestRequest(url, ERestMethod.POST);
        req.SetHeader("X-API-Key", HIVE_KEY);
        req.SetHeader("Content-Type", "application/json");
        req.SetTimeout(HIVE_TIMEOUT_MS);
        
        string body = "{\"steam_id\":\"" + steamId + "\",\"token\":\"" + token + "\"}";
        req.SetBody(body);
        
        HiveRestCb callback = new HiveRestCb();
        callback.m_onSuccess = func(RestResponse response)
        {
            string responseBody = response.GetBody();
            JsonReader reader = new JsonReader();
            ref JsonValue jsonData = reader.ReadFromString(responseBody);
            
            if (jsonData && jsonData.IsObject())
            {
                JsonValue payloadValue = jsonData.GetMember("payload");
                if (payloadValue)
                {
                    JsonWriter writer = new JsonWriter();
                    payloadJson = writer.WriteToString(payloadValue);
                    s_kvCache.Set("claim_" + token, payloadJson);
                }
            }
        };
        
        callback.m_onError = func(RestResponse response)
        {
            if (response.GetCode() != 410 && HIVE_RETRY > 0)
            {
                int jitter = Math.RandomInt(50, 150);
                Enqueue(func() { ClaimTransfer(steamId, token, payloadJson); }, 100 + jitter);
            }
            
            if (response.GetCode() != 410)
            {
                LogOnce("claim_error", "HiveApi: Failed to claim transfer");
            }
        };
        
        ctx.Send(req, callback);
        
        string cachedValue = "";
        if (s_kvCache.Find("claim_" + token, cachedValue))
        {
            payloadJson = cachedValue;
            return true;
        }
        
        return false;
    }
    
    static void LogOnce(string key, string msg)
    {
        int currentTime = GetGame().GetTime();
        int lastTime = 0;
        
        if (s_lastLog.Find(key, lastTime))
        {
            if (currentTime - lastTime < HIVE_LOG_INTERVAL_MS)
            {
                return;
            }
        }
        
        s_lastLog.Set(key, currentTime);
        Print(msg);
    }
    
    static void Enqueue(func fn, int delayMs)
    {
        GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(fn, delayMs, false);
    }
    
    static RestContext GetRestContext()
    {
        return GetRestApi().GetRestContext();
    }
};

class HiveRestCb : RestCallback
{
    func m_onSuccess;
    func m_onError;
    
    override void OnSuccess(RestResponse response)
    {
        if (m_onSuccess)
        {
            m_onSuccess.Invoke(response);
        }
    }
    
    override void OnError(RestResponse response)
    {
        if (m_onError)
        {
            m_onError.Invoke(response);
        }
    }
};
