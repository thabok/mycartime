package com.thabok.util;

import java.util.HashMap;
import java.util.Map;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonElement;

import spark.ResponseTransformer;

/**
 * JsonUtil serves as a helper class to serialize objects into json.
 */
public class JsonUtil {

	private static Gson g = new GsonBuilder().setDateFormat("yyyy-MM-dd'T'HH:mm:ss'+0200'").create();
    /**
     * 
     * A helper method to serialize objects into json.
     *
     * @param object the object to serialize
     * @return the serialized object (String)
     */
    public static String toJson(Object object) {
    	return g.toJson(object).replace("\\\"", "'");
    }

    /**
     * 
     * A helper method to serialize objects into json.
     *
     * @param object the object to serialize
     * @return the serialized object (String)
     */
    public static String toHtml(Object object) {
        return object.toString();
    }

    public static JsonElement jsonObject(Object ... keyvaluepairs) throws Exception {
		if ((keyvaluepairs.length % 2) != 0) {
			throw new Exception("Every key must have a value.");
		}
		Map<Object, Object> map = new HashMap<>();
		for (int i = 0; i < keyvaluepairs.length; i=i+2) {
			map.put(keyvaluepairs[i], keyvaluepairs[i+1]);
		}
		return g.toJsonTree(map);
		
	}
    
    /**
     * 
     * Json Response Transformer (to Json)
     *
     * @return the transformed response
     */
    public static ResponseTransformer json() {
        return JsonUtil::toJson;
    }

    public static ResponseTransformer html() {
        return JsonUtil::toHtml;
    }

}
