package com.thabok.webservice;

import static spark.Spark.before;
import static spark.Spark.get;
import static spark.Spark.options;
import static spark.Spark.port;
import static spark.Spark.post;

import java.util.List;
import java.util.Map;
import java.util.concurrent.CancellationException;

import com.google.gson.Gson;
import com.thabok.entities.Person;
import com.thabok.entities.ProgressObject;
import com.thabok.entities.TwoWeekPlan;
import com.thabok.main.Controller;
import com.thabok.untis.Period;
import com.thabok.untis.WebUntisAdapter;
import com.thabok.util.JsonUtil;
import com.thabok.util.PlanInputData;
import com.thabok.util.Util;

import org.apache.commons.codec.binary.Base64;

import spark.Request;
import spark.Response;


public class WebService {

	private static ProgressObject progress = new ProgressObject();
	public static boolean isCancelled;

	public WebService() {
		port(getPort(1337));
		enableCORS("*");
		before((req, res) -> logIncomingRequest(req));
		get("/check", (req, res) -> true, JsonUtil.json());
		post("/checkConnection", (req, res) -> checkConnection(req, res), JsonUtil.json());
		post("/login", (req, res) -> login(req, res), JsonUtil.json());
		post("/calculatePlan", (req, res) -> calculatePlan(req, res), JsonUtil.json());
		post("/cancel", (req, res) -> cancel(req, res), JsonUtil.json());
		get("/progress", (req, res) -> getProgress(req, res), JsonUtil.json());
		post("/logout", (req, res) -> logout(req, res), JsonUtil.json());
	}

	private Object getProgress(Request req, Response res) {
		return progress;
	}

	private Object cancel(Request req, Response res) {
		return isCancelled = true;
	}

	private int getPort(int defaultPort) {
		int portAsInt = defaultPort; //default port
		String port = System.getProperty("app.port");
		try {
			portAsInt = Integer.parseInt(port);
		} catch (NumberFormatException e) {
			System.err.println("No (or invalid) port value specified. Falling back to default port " + defaultPort);
		}
		return portAsInt;
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
		isCancelled = false;
		PlanInputData inputData = new Gson().fromJson(req.body(), PlanInputData.class);
		List<Person> persons = inputData.persons;
		Controller.referenceWeekStartDate = inputData.scheduleReferenceStartDate;
		int personCount = 0;
		for (Person person : persons) {
			if (isCancelled) {
				throw new CancellationException("The operation was cancelled by the user.");
			}
			personCount++;
			String msg = "Fetching timetable for " + person.firstName + " " + person.lastName + " (" + person.initials + ")";
			System.out.println(msg);
			float progressValue = (((float)personCount) / persons.size()) * 0.95f;
			WebService.updateProgress(progressValue, msg);
			Map<Integer, Period> timetable = WebUntisAdapter.getTimetable(person.initials, inputData.scheduleReferenceStartDate);
			person.schedule = Util.timetableToSchedule(timetable);
		}
		// at this point we should be at a progress value of 0.95 (95%)
		Controller controller = new Controller(persons);
		TwoWeekPlan wp = controller.calculateGoodPlan(1000);
		controller.summarizeNumberOfDrives(wp);
		WebUntisAdapter.logout();
		return wp;
	}

	/** 
	 * Updates the progress object which can be queried via GET /progress
	 */
	public static void updateProgress(float f, String msg) {
		progress.value = f;
		progress.message = msg;
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
