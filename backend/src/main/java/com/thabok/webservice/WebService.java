package com.thabok.webservice;

import static spark.Spark.before;
import static spark.Spark.get;
import static spark.Spark.options;
import static spark.Spark.port;
import static spark.Spark.post;

import java.lang.reflect.Type;
import java.util.List;
import java.util.Map;

import org.apache.commons.codec.binary.Base64;

import com.google.gson.Gson;
import com.google.gson.reflect.TypeToken;
import com.thabok.entities.Person;
import com.thabok.entities.Schedule;
import com.thabok.entities.WeekPlan;
import com.thabok.main.Controller;
import com.thabok.untis.TimetableItem;
import com.thabok.untis.WebUntisAdapter;
import com.thabok.util.JsonUtil;
import com.thabok.util.Util;

import spark.Request;
import spark.Response;


public class WebService {

	public WebService() {
		// oh yeah!
		port(1337);
		enableCORS("*");
		before((req, res) -> logIncomingRequest(req));
		get("/check", (req, res) -> true, JsonUtil.json());
		post("/checkConnection", (req, res) -> checkConnection(req, res), JsonUtil.json());
		post("/login", (req, res) -> login(req, res), JsonUtil.json());
		post("/calculatePlan", (req, res) -> calculatePlan(req, res), JsonUtil.json());
		post("/logout", (req, res) -> logout(req, res), JsonUtil.json());
	}

	/**
	 * Main method to calculate a week plan for the carpool party.<br>
	 * IMPORTANT: user must be logged in to use this method!
	 * @param req the incoming request
	 * @param res the response
	 * @return the week plan
	 * @throws Exception things can go wrong...
	 */
	public Object calculatePlan(Request req, Response res) throws Exception {
		Type typeToken = new TypeToken<List<Person>>() {}.getType();
		List<Person> persons = new Gson().fromJson(req.body(), typeToken);
		for (Person person : persons) {
			Map<Integer, TimetableItem> timetable = WebUntisAdapter.getTimetable(person.initials);
			Schedule schedule = Util.timetableToSchedule(timetable);
			person.schedule = schedule;
		}
		Controller controller = new Controller(persons);
		WeekPlan wp = controller.calculateGoodPlan(1000);
		controller.summarizeNumberOfDrives(wp);
		WebUntisAdapter.logout();
		return wp;
	}

	public WebPkg login(Request req, Response res) {
		String json = req.body();
		WebCredentials credentials = new Gson().fromJson(json, WebCredentials.class);
		WebPkg pkg = new WebPkg();
		pkg.topic = "login";
		try {
			WebUntisAdapter.login(credentials.username, decode(credentials.hash));
			pkg.value = true;
		} catch (Exception e) {
			res.status(403);
			pkg.message = e.getMessage();
			pkg.value = false;
		}
		return pkg;
	}
	
	public WebPkg logout(Request req, Response res) {
		WebPkg pkg = new WebPkg();
		pkg.topic = "logout";
		try {
			WebUntisAdapter.logout();
			pkg.value = true;
		} catch (Exception e) {
			pkg.value = false;
			pkg.message = e.getMessage();
		}
		return pkg;
	}
	
	public WebPkg checkConnection(Request req, Response res) throws Exception {
		WebPkg pkg = login(req, res);
		if ((boolean) pkg.value == true) {
			WebUntisAdapter.logout();
		}
		return pkg;
	}

	/*
	 ************************************************************************************************
	 * Utility functions
	 ************************************************************************************************
	 */
	
	/**
	 * decodes a base64 encoded string
	 * @param hash the encoded string
	 * @return the decoded string
	 */
	private String decode(String hash) {
		return new String(Base64.decodeBase64(hash));
	}
	
	/**
	 * This method is executed before an incoming request is handled. It logs the incoming request. 
	 * @param req the incoming request
	 */
	private void logIncomingRequest(Request req) {
		try {
			String reqBody = req.body();
			String reqUrl = req.url();
			String reqMethod = req.requestMethod();
			System.out.println("Incoming " + reqMethod + " request to " + reqUrl + ": " + reqBody);
		} catch (Exception e) {
			System.err.println("Couldn't log incoming request. " + e.toString());
		}
	}
	
	/**
	 * Enables CORS on requests. This method is an initialization method and should
	 * be called once.
	 * 
	 * @param origin the allowed origins
	 */
	private static void enableCORS(final String origin) {
		options("/*", (request, response) -> {
			String accessControlRequestHeaders = request.headers("Access-Control-Request-Headers");
			if (accessControlRequestHeaders != null) {
				response.header("Access-Control-Allow-Headers", accessControlRequestHeaders);
			}
			String accessControlRequestMethod = request.headers("Access-Control-Request-Method");
			if (accessControlRequestMethod != null) {
				response.header("Access-Control-Allow-Methods", accessControlRequestMethod);
			}
			return "OK";
		});
		before((request, response) -> {
			response.header("Access-Control-Allow-Origin", origin);
			response.type("application/json");
		});
	}
}
