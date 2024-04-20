package com.thabok.webservice;

import static spark.Spark.before;
import static spark.Spark.get;
import static spark.Spark.options;
import static spark.Spark.port;
import static spark.Spark.post;

import java.nio.file.Files;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CancellationException;

import org.apache.commons.codec.binary.Base64;

import com.google.gson.Gson;
import com.thabok.entities.CustomDay;
import com.thabok.entities.DayPlan;
import com.thabok.entities.MasterPlan;
import com.thabok.entities.NumberOfDrivesStatus;
import com.thabok.entities.PartyTuple;
import com.thabok.entities.Person;
import com.thabok.entities.PlanInputData;
import com.thabok.entities.ProgressObject;
import com.thabok.entities.TimingInfo;
import com.thabok.helper.PlanOptimizationHelper;
import com.thabok.helper.TimetableHelper;
import com.thabok.main.Controller;
import com.thabok.untis.Period;
import com.thabok.untis.WebUntisAdapter;
import com.thabok.util.JsonUtil;
import com.thabok.util.Util;

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
		post("/calculatePlan", (req, res) -> calculatePlan(req, res), JsonUtil.strippedDrivingPlan());
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
			float progressValue = (((float)personCount) / persons.size()) * 0.5f;
			WebService.updateProgress(progressValue, msg);
			Map<Integer, Period> timetable = WebUntisAdapter.getTimetable(person.initials, inputData.scheduleReferenceStartDate);
			person.schedule = TimetableHelper.timetableToSchedule(person, timetable);
		}
		
		// at this point we should be at a progress value of 0.5 (50%)
		Controller controller = new Controller();
		MasterPlan mp;
		if (inputData.preset == null) {
			mp = findBestWeekPlan(controller, persons, 15000);
			// calculate the winning plan once more (for debugging, tracability, etc.)
			
			MasterPlan mp2 = controller.calculateWeekPlan(mp);
			if (!mp.toString().equals(mp2.toString())) {
				throw new IllegalStateException("Traceability plan doesn't match originally calculated plan!");
			}
						
		} else {
//			mp = controller.adaptPreset(inputData.preset);
			mp = controller.calculateWeekPlan(persons, inputData.preset);
		}
//		Util.writeStringToFile("/Users/thabok/Downloads/plan_" + System.currentTimeMillis() + ".txt", mp);
		
		storePersonsTimesPerDayPlan(mp);
		// impact analysis of fix for issue #11 (PlanOptimizationHelper)
		PlanOptimizationHelper.printTightnessOverview(mp);
		
		clearDataFromPlan(mp);
		
		return mp;
	}
	
	
	
	private void clearDataFromPerson(Person p) {
		p.schedule = null;
		p.customDays = null;
	}
	
	/**
	 * Collect time infos per person for each day plan
	 * this data is required to correctly adapt the party times when passengers are moved
	 **/ 
	private void storePersonsTimesPerDayPlan(MasterPlan mp) {
		for (DayPlan dp : mp.getDayPlans().values()) {
			for (Person p : mp.persons) {
				if (TimetableHelper.isPersonActiveOnThisDay(p, dp.getDayOfWeekABCombo())) {
					TimingInfo timingInfo = TimetableHelper.getTimingInfoForDay(p, dp.getDayOfWeekABCombo());
					dp.schoolboundTimesByInitials.put(p.initials, timingInfo.getStartTime());
					dp.homeboundTimesByInitials.put(p.initials, timingInfo.getEndTime());
				}
			}
		}
	}
	private void clearDataFromPlan(MasterPlan mp) {
		mp.persons = null;
		mp.inputsPerDay = null;
		mp.key = null;
		
		for (DayPlan dp : mp.getDayPlans().values()) {
			for (PartyTuple pt : dp.getPartyTuples()) {
				clearDataFromPerson(pt.getPartyThere().getDriver());
				pt.getPartyThere().getPassengers().forEach(p -> clearDataFromPerson(p));
				
				clearDataFromPerson(pt.getPartyBack().getDriver());
				pt.getPartyBack().getPassengers().forEach(p -> clearDataFromPerson(p));
			}
		}
	}

	/**
	 * Attempts to find the best plan out of a randomly generated set of plans. Uses
	 * the metrics gt4 and gt5, indicating the number of persons who drive more than
	 * 4 / 5 times respectivly. These metrics are being minimized.
	 * 
	 * Additional property to minimize (prioritized):
	 * (1) People driving on a day that violates their customPrefs while having passengers
	 * (2) ...
	 */
	private MasterPlan findBestWeekPlan(Controller controller, List<Person> persons, int iterationsWithoutImprovementLimit) throws Exception {
		MasterPlan mp = null;
		int lowestNoPersonsWithMoreThan4Drives = 100;
		int lowestNoPersonsWithMoreThan5Drives = 100;
		int lowestNoInvoluntaryDrives = 100;
		int estimatedTotal = Math.round(iterationsWithoutImprovementLimit * 1.3f);
		int iterationsWithoutImprovement = 0;
		int i = 0;
		while (iterationsWithoutImprovement < iterationsWithoutImprovementLimit) {
			// whenever the user cancels: return best candidate
			if (isCancelled) {
				return mp;
			}
			
			Collections.shuffle(persons);
			float progressValue = 0.5f + ((float) i++ / estimatedTotal) * 0.5f;
			MasterPlan mpCandidate = controller.calculateWeekPlan(persons);
			int gt4 = calculateNumberOfPersonsAboveThreshold(mpCandidate, 4);
			int gt5 = calculateNumberOfPersonsAboveThreshold(mpCandidate, 5);
			int involuntaryDrives = calculateNumberOfInvoluntaryDrives(mpCandidate);
			WebService.updateProgress(progressValue, "Calculating plan... (persons with more than four drives: " + lowestNoPersonsWithMoreThan4Drives + ")");
			if (gt4 < lowestNoPersonsWithMoreThan4Drives) {
				System.out.println("Found a better plan (gt4): " + lowestNoPersonsWithMoreThan4Drives + " -> " + gt4);
				lowestNoPersonsWithMoreThan4Drives = gt4;
				lowestNoPersonsWithMoreThan5Drives = gt5;
				mp = mpCandidate;
				iterationsWithoutImprovement = 0;
			} else if (gt4 == lowestNoPersonsWithMoreThan4Drives && gt5 < lowestNoPersonsWithMoreThan5Drives) {
				System.out.println("Found a better plan (gt5): " + lowestNoPersonsWithMoreThan5Drives + " -> " + gt5);
				lowestNoPersonsWithMoreThan4Drives = gt4;
				lowestNoPersonsWithMoreThan5Drives = gt5;
				mp = mpCandidate;
				iterationsWithoutImprovement = 0;
			} else if (gt4 == lowestNoPersonsWithMoreThan4Drives && gt5 == lowestNoPersonsWithMoreThan5Drives && involuntaryDrives < lowestNoInvoluntaryDrives) {
				System.out.println("Found a better plan (invol.drives): " + lowestNoInvoluntaryDrives + " -> " + involuntaryDrives);
				lowestNoInvoluntaryDrives = involuntaryDrives;
				mp = mpCandidate;
				iterationsWithoutImprovement = 0;
			} else {
				iterationsWithoutImprovement++;
			}
		}
		return mp;
	}

	private int calculateNumberOfInvoluntaryDrives(MasterPlan mpCandidate) {
		int numberOfInvoluntaryDrives = 0;
		for (DayPlan dayPlan : mpCandidate.getDayPlans().values()) {
			for (PartyTuple tuple : dayPlan.getPartyTuples()) {
				Person driver = tuple.getDriver();
				CustomDay customDay = driver.customDays.get(dayPlan.getDayOfWeekABCombo().getUniqueNumber());
				boolean passengersHomebound = !tuple.getPartyThere().getPassengers().isEmpty();
				boolean passengersSchoolbound = !tuple.getPartyBack().getPassengers().isEmpty();
				if (customDay != null && customDay.drivingSkip && (passengersSchoolbound || passengersHomebound)) {
					// unvoluntary drive with passengers
					numberOfInvoluntaryDrives++;
				}
			}
		}
		return numberOfInvoluntaryDrives;
	}

	private int calculateNumberOfPersonsAboveThreshold(MasterPlan mpCandidate, int threshold) {
		NumberOfDrivesStatus nods = new NumberOfDrivesStatus(mpCandidate);
		int gtThreshold = 0;
		for (int noDrives : nods.getNumberOfDrives().values()) {
			if (noDrives > threshold) gtThreshold++; 
		}
		return gtThreshold;
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
			if (reqUrl != null && !reqUrl.contains("/progress")) {
				System.out.println("Incoming " + reqMethod + " request to " + reqUrl + ": " + reqBody);
			}
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
