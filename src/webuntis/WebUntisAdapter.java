package webuntis;

import java.io.IOException;
import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;
import java.util.TreeMap;

import org.apache.hc.client5.http.classic.methods.HttpPost;
import org.apache.hc.client5.http.impl.classic.CloseableHttpClient;
import org.apache.hc.client5.http.impl.classic.CloseableHttpResponse;
import org.apache.hc.client5.http.impl.classic.HttpClients;
import org.apache.hc.core5.http.ContentType;
import org.apache.hc.core5.http.HttpEntity;
import org.apache.hc.core5.http.ParseException;
import org.apache.hc.core5.http.io.entity.EntityUtils;
import org.apache.hc.core5.http.io.entity.StringEntity;

import com.google.gson.Gson;

public class WebUntisAdapter {
	
	private static final String JSESSIONID = "JSESSIONID";
	private static final String JSON_RPC_VERSION = "2.0";
	private static final String APP_ACCESS_ID = "id1234";
	private static final String SCHOOL_NAME = "NG%20Wilhelmshaven";
	private static final String URL_SCHOOL_NGW = "https://cissa.webuntis.com/WebUntis/jsonrpc.do?school=" + SCHOOL_NAME;

	public static String sessionId = null;
	
	public static Map<Integer, TimetableItem>  getTimetable(String teacherInitials) {
		Map<String, Object> params = new HashMap<>();
		Map<String, Object> options = new HashMap<>();
		Map<String, Object> teacher = new HashMap<>();
		teacher.put("id", teacherInitials);
		teacher.put("type", 2);
		teacher.put("keyType", "name");
		options.put("element", teacher);
		options.put("teacherFields", Arrays.asList("id", "name", "externalkey"));
		options.put("startDate", 20200831);
		options.put("endDate", 20200904);
		params.put("options", options);
		String response = execute("getTimetable", params);
//		System.out.println(response);
		TimetableWrapper timetableWrapper = new Gson().fromJson(response, TimetableWrapper.class);
		Map<Integer, TimetableItem> comingAndGoing = new HashMap<>();
		for (TimetableItem item : timetableWrapper.result) {
			TimetableItem timetableItem = comingAndGoing.get(item.date);
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
		return new TreeMap<>(comingAndGoing);
	}
	
	public static String login(String user, String password) {
		
		Map<String, Object> params = new HashMap<>();
		params.put("user", user);
		params.put("password", password);
		params.put("client", "Java");
		
		String responseString = execute("authenticate", params);
        
        Map<?,?> m1 = new Gson().fromJson(responseString, Map.class);
        Map<?,?> m2 = (Map<?,?>) m1.get("result");
        sessionId = (String) m2.get("sessionId");
		
		return sessionId;
	}
	
	public static String logout() throws Exception {
		
		if (sessionId == null) throw new Exception("Not logged in!");
		
		Map<String, Object> params = new HashMap<>();
		
		Map<String, Object> obj = new HashMap<>();
		
		obj.put("method", "logout");
		obj.put("id", APP_ACCESS_ID);
		obj.put("jsonrpc", JSON_RPC_VERSION);
		obj.put("params", params);
		
        String responseString = post(obj);
        
        sessionId = null;
        
		return responseString;
	}
	
	
	public static String execute(String methodName, Map<String, Object> params) {
				
		Map<String, Object> obj = new HashMap<>();
		obj.put("method", methodName);
		obj.put("id", APP_ACCESS_ID);
		obj.put("jsonrpc", JSON_RPC_VERSION);
		obj.put("params", params);
		
		return post(obj);
	}

	private static String post(Object payload) {
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
		return responseString;
	}
	
}
