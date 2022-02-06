package com.thabok.untis;

import java.io.IOException;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.stream.Collectors;

import org.apache.http.HttpEntity;
import org.apache.http.ParseException;
import org.apache.http.client.methods.CloseableHttpResponse;
import org.apache.http.client.methods.HttpPost;
import org.apache.http.entity.ContentType;
import org.apache.http.entity.StringEntity;
import org.apache.http.impl.client.CloseableHttpClient;
import org.apache.http.impl.client.HttpClients;
import org.apache.http.util.EntityUtils;

import com.google.gson.Gson;
import com.thabok.util.Util;

public class WebUntisAdapter {
    
    private static final String JSESSIONID = "JSESSIONID";
    private static final String JSON_RPC_VERSION = "2.0";
    private static final String APP_ACCESS_ID = "id1234";
    private static final String SCHOOL_NAME = "NG%20Wilhelmshaven";
    private static final String URL_SCHOOL_NGW = "https://cissa.webuntis.com/WebUntis/jsonrpc.do?school=" + SCHOOL_NAME;
//	private static final String CACHE_FILE = "/Users/thabok/Git/mycartime/webuntis-cache.json";
    
    public static String sessionId = null;
    
    private static Map<String, String> requestResultCache = new HashMap<>();
    
    private static Map<Integer, Period>  getTimetableBasedOnStartDate(String teacherInitials, int startDate) throws Exception {
        if (teacherInitials == null || teacherInitials.isEmpty()) {
            throw new Exception("No teacher initials specified.");
        }
        if (sessionId == null) {
            throw new Exception("Must be logged in to query data from WebUntis.");
        }
        Map<String, Object> params = new HashMap<>();
        Map<String, Object> options = new HashMap<>();
        Map<String, Object> teacher = new HashMap<>();
        teacher.put("id", teacherInitials);
        teacher.put("type", 2);
        teacher.put("keyType", "name");
        options.put("element", teacher);
        options.put("teacherFields", Arrays.asList("id", "name", "externalkey"));
        options.put("startDate", startDate);
        options.put("endDate", Util.calculateDateNumber(startDate, 4));
        params.put("options", options);
        String response = execute("getTimetable", params);
        TimetableWrapper timetableWrapper = new Gson().fromJson(response, TimetableWrapper.class);
        Map<Integer, Period> comingAndGoing = new HashMap<>();
        try {
        	List<Period> relevantPeriods = timetableWrapper.result.stream()
        			.filter(p -> Util.isPeriodRelevant(p, teacherInitials))
        			.collect(Collectors.toList());
            for (Period item : relevantPeriods) {
                Period timetableItem = comingAndGoing.get(item.date);
                if (timetableItem == null) {
                    comingAndGoing.put(item.date, item);
                } else {
                    if (item.startTime < timetableItem.startTime) {
                        timetableItem.startTime = item.startTime;
                    }
                    if (item.endTime > timetableItem.endTime) {
                        timetableItem.endTime = item.endTime;
                    }
                }
            }
        } catch (Exception e) {
            String msg = e.getMessage();
            try {
                msg = (String) timetableWrapper.error.get("message");
            } catch (Exception e1) {
            }
            throw new Exception(msg);
        }
        return new TreeMap<>(comingAndGoing);
    }

    public static Map<Integer, Period>  getTimetable(String teacherInitials, int scheduleReferenceStartDate) throws Exception {
        Map<Integer, Period> timetable = getTimetableBasedOnStartDate(teacherInitials, scheduleReferenceStartDate);
        int bWeekStartDate = Util.calculateDateNumber(scheduleReferenceStartDate, 7);
        timetable.putAll(getTimetableBasedOnStartDate(teacherInitials, bWeekStartDate));
		return timetable;
    }
    
    public static String login(String user, String password) throws Exception {
        Map<String, Object> params = new HashMap<>();
        params.put("user", user);
        params.put("password", password);
        params.put("client", "Java");
        
        // load cache from file
//        if (requestResultCache.isEmpty() && CACHE_FILE != null) {
//        	String content = Util.readStringFromFile(CACHE_FILE);
//        	if (content != null && !content.isBlank()) {
//        		Type type = new TypeToken<Map<String, String>>() {
//    			}.getType();
//            	requestResultCache = new Gson().fromJson(content, type);
//        	}
//        }
        
        String responseString = execute("authenticate", params);
        
        Map<?,?> m1 = new Gson().fromJson(responseString, Map.class);
        try {
            Map<?,?> m2 = (Map<?,?>) m1.get("result");
            sessionId = (String) m2.get("sessionId");
        } catch (Exception e) {
            String s = e.getMessage();
            try {
                s = (String)((Map<?,?>) m1.get("error")).get("message");
            } catch (Exception e1) {
            }
            throw new Exception(s);
        }
        
        return sessionId;
    }
    
    public static String logout() throws Exception {
        
//        if (sessionId == null) throw new Exception("Not logged in!");
        
        Map<String, Object> params = new HashMap<>();
        
        String responseString = execute("logout", params);
        
        sessionId = null;
        
        // store cache in file
//        if (CACHE_FILE != null) {
//        	String content = JsonUtil.toJson(requestResultCache);
//        	Util.writeStringToFile(CACHE_FILE, content);
//        }
        
        return responseString;
    }
    
    
    public static String execute(String methodName, Map<String, Object> params) {
                
        Map<String, Object> obj = new HashMap<>();
        obj.put("method", methodName);
        obj.put("id", APP_ACCESS_ID);
        obj.put("jsonrpc", JSON_RPC_VERSION);
        obj.put("params", params);
        
        String requestId = methodName;
        try {
        	if (params.get("options") != null) {
        		requestId += "-" + ((Map<?,?>)((Map<?,?>)params.get("options")).get("element")).get("id");
        		requestId += "-" + ((Map<?,?>)params.get("options")).get("startDate");
        	}
		} catch (Exception e) {
			e.printStackTrace();
		}
        
        return post(obj, requestId);
    }

    private static String post(Object payload, String requestId) {
    	// try cache
//    	String cachedResult = requestResultCache.get(requestId);
//    	if (cachedResult != null) {
//    		return cachedResult;
//    	}
    	// real request
        String responseString = null;
        HttpPost post = new HttpPost(URL_SCHOOL_NGW);
        String json = new Gson().toJson(payload);
        HttpEntity body = new StringEntity(json, ContentType.APPLICATION_JSON);
        post.setEntity(body);
        post.addHeader("Content-Type", "application/json");
        try (CloseableHttpClient httpClient = HttpClients.createDefault()) {
            if (sessionId != null) {
                post.addHeader("Cookie", JSESSIONID + "=" + sessionId);
            }
            CloseableHttpResponse response = httpClient.execute(post);
            HttpEntity entity = response.getEntity();
            responseString = EntityUtils.toString(entity);
        } catch (IOException e) {
            System.err.println("IO Exception during request.");
            e.printStackTrace();
        } catch (ParseException e) {
            System.err.println("Response could not be parsed.");
            e.printStackTrace();
        }
        // cache result
        requestResultCache.put(requestId, responseString);
        return responseString;
    }
    
}
