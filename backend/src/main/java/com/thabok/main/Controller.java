package com.thabok.main;

import java.time.DayOfWeek;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

import com.thabok.entities.DayPlan;
import com.thabok.entities.DayPlanInput;
import com.thabok.entities.Party;
import com.thabok.entities.PartyTouple;
import com.thabok.entities.Person;
import com.thabok.entities.Rule;
import com.thabok.entities.TimingInfo;
import com.thabok.entities.WeekPlan;

public class Controller {

	private List<Person> persons;
	private Map<Person, Integer> numberOfDrives;
	private List<Rule> rules = new ArrayList<>();
	private Map<DayOfWeek, DayPlanInput> inputsPerDay;
	public static List<DayOfWeek> weekdays = Arrays.asList(DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY, DayOfWeek.THURSDAY, DayOfWeek.FRIDAY);
	
	public Controller(List<Person> persons) {
		this.persons = persons;
		numberOfDrives = new HashMap<>();
		persons.forEach(p -> numberOfDrives.put(p, 0));
	}
	
	public WeekPlan calculateGoodPlan(int iterations) throws Exception {
		float bestScore = -1f;
		float worstScore = 1f;
		WeekPlan bestPlan = null;
		WeekPlan worstPlan = null;
		for (int i = 0; i < iterations; i++) {
			WeekPlan weekPlan = calculateWeekPlan();
			float fitness = getFitness(weekPlan, false);
			if (fitness > bestScore) {
				bestScore = fitness;
				bestPlan = weekPlan;
			}
			if (fitness < worstScore) {
				worstScore = fitness;
				worstPlan = weekPlan;
			}
		}
		System.out.println("Best Score: " + bestScore);
		return bestPlan;
	}
	
	public String summarizeNumberOfDrives(WeekPlan wp) {
		String summary = "";
		persons.forEach(p -> numberOfDrives.put(p, 0));
		for (DayPlan dp : wp.getDayPlans().values()) {
			for (PartyTouple pt : dp.getPartyTouples()) {
				numberOfDrives.put(pt.getDriver(), numberOfDrives.get(pt.getDriver()) + 1);
			}
		}
		for (Person p : numberOfDrives.keySet()) {
			String s = "- " + p.getName() + ": " + numberOfDrives.get(p);
			System.out.println(s);
			summary += s + "\n";
		}
		wp.summary = summary;
		return summary;
	}
	
	public void printOverview(WeekPlan wp) {
		for (DayPlan dayPlan : wp.getDayPlans().values()) {
			System.out.println(dayPlan.getDayOfWeek());
			Map<Integer, List<PartyTouple>> partyTouplesByFirstLesson = new HashMap<>();
			for (PartyTouple pt : dayPlan.getPartyTouples()) {
				int firstLesson = pt.getDriver().schedule.getTimingInfoPerDay().get(dayPlan.getDayOfWeek()).getFirstLesson();
				List<PartyTouple> list = partyTouplesByFirstLesson.get(firstLesson);
				if (list == null) {
					list = new ArrayList<>();
					partyTouplesByFirstLesson.put(firstLesson, list);
				}
				list.add(pt);
			}
			for (int firstLesson : partyTouplesByFirstLesson.keySet()) {
				System.out.println("[" + firstLesson + "]");
				for (PartyTouple pt : partyTouplesByFirstLesson.get(firstLesson)) {
					System.out.println(pt);
				}
			}
			System.out.println();
		}
	}
	
	public void initialize() {
		inputsPerDay = new HashMap<>();
		persons.forEach(p -> numberOfDrives.put(p, 0));
		for (DayOfWeek dayOfWeek : weekdays) {
			DayPlanInput dpi = new DayPlanInput();
			dpi.personsByFirstLesson = getPersonsByFirstLesson(persons, dayOfWeek);
			dpi.personsByLastLesson = getPersonsByLastLesson(persons, dayOfWeek);
			dpi.designatedDrivers = getDesignatedDrivers(dpi.personsByFirstLesson, dpi.personsByLastLesson);
			inputsPerDay.put(dayOfWeek, dpi);
			dpi.designatedDrivers.forEach(driver -> {
				Integer number = numberOfDrives.get(driver);
				numberOfDrives.put(driver, number + 1);
			});
		}
	}
	
	public WeekPlan calculateWeekPlan() throws Exception {
		initialize();
		WeekPlan wp = new WeekPlan();
		Collections.shuffle(weekdays);
		for (DayOfWeek dayOfWeek : weekdays) {
			wp.put(dayOfWeek, calculateDayPlan(dayOfWeek));
		}
		wp.setWeekDayPermutation(new ArrayList<>(weekdays));
		return wp;
	}
	
	private Person findDriver(Set<Person> possibleDrivers) {
		Person driver = null;
		int noDrives = 100;
		for (Person person : possibleDrivers) {
			Integer currentNoDrives = numberOfDrives.get(person);
			if (currentNoDrives < noDrives) {
				driver = person;
				noDrives = currentNoDrives;
				if (noDrives == 0) {
					break; // can't get any better
				}
			}
		}
		return driver;
	}

	/**
	 * Calculates the fitness of a dayPlan. The result is a value between 0 and 1 (1 being the unrealistic ideal).
	 * Checks the following criteria:
	 * 	- average no driving days per person (the lower the better)
	 *  - difference between min & max no driving days (the lower the better)
	 * 	- missed global rules (have all mandatory rules been fulfilled? if not -> total fitness = 0)
	 *  - missed global guidelines (have all guidelines been fulfilled? if not reduced fitness; 2/5 guidelines missed -> 40% guideline penalty)
	 * @param weekPlan
	 * @return fitness
	 */
	public float getFitness(WeekPlan weekPlan, boolean print) {
		// Rules
		List<Rule> nonGlobalRules = rules.stream().filter(rule -> rule.isMandatory && "GLOBAL".equals(rule.scope)).collect(Collectors.toList());
		for (Rule rule : nonGlobalRules) {
			if (!matches(weekPlan, rule)) {
				System.out.println("WeekPlan doesn't match rule: \n" + weekPlan + "\n" + rule);
				return 0f;
			}
		}
		float totalDayPlanFitness = 0f;
		Map<Person, Integer> drivingDaysPerPerson = new HashMap<>();
		Integer minDrivingDays = null;
		Integer maxDrivingDays = null;
		int totalDrivingDays = 0;
		for (DayPlan dayPlan : weekPlan.getDayPlans().values()) {
			float dayPlanFitness = getFitness(dayPlan);
			if (dayPlanFitness == 0f) {
				return 0f;
			} else {
				totalDayPlanFitness += dayPlanFitness;
			}
			for (PartyTouple pt : dayPlan.getPartyTouples()) {
				Person driver = pt.getDriver();
				Integer amount = drivingDaysPerPerson.get(driver);
				if (amount == null) {
					drivingDaysPerPerson.put(driver, 1);
				} else {
					drivingDaysPerPerson.put(driver, amount + 1);
				}
			}
		}
		// initial fitness based on avg day plan fitness
		float avgDayPlanFitness = totalDayPlanFitness / (float) 5;
		float fitness = avgDayPlanFitness;
		for (Person person : persons) {
			Integer drivingDays = drivingDaysPerPerson.get(person);
			drivingDays = drivingDays == null ? 0 : drivingDays;
			if (minDrivingDays == null || minDrivingDays > drivingDays) {
				minDrivingDays = drivingDays;
			}
			if (maxDrivingDays == null || maxDrivingDays < drivingDays) {
				maxDrivingDays = drivingDays;
			}
			totalDrivingDays += drivingDays;
		}
		float avgDrivingDaysPerPerson = totalDrivingDays / (float) persons.size();
		// fitness penalty based on min-max difference
		float minMaxDiffPenalty = maxDrivingDays == minDrivingDays ? 0f : 1 - (1f / (1 + maxDrivingDays - minDrivingDays));
		fitness -= 0.3f * fitness * minMaxDiffPenalty;
		// fitness penalty based on avg driving days
		float avgDrivingDaysPenalty = avgDrivingDaysPerPerson / (float) 5; // 0 < value <= 1; the lower the better
		fitness -= 0.3f * fitness * avgDrivingDaysPenalty;
		
		if (print) {
			System.out.println("Avg. Driving Days p.P.: " + avgDrivingDaysPerPerson);
			System.out.println("Min. Driving Days: " + minDrivingDays);
			System.out.println("Max. Driving Days: " + maxDrivingDays);
		}
		return fitness;
	}
	
	private boolean matches(WeekPlan weekPlan, Rule rule) {
		return true;
	}

	/**
	 * Calculates the fitness of a dayPlan. The result is a value between 0 and 1 (1 being the unrealistic ideal).
	 * Checks the following criteria:
	 * 	- missed rules: have all mandatory rules been fulfilled? if not -> total fitness = 0
	 * 	- partiesPersonRatio (50% impact on fitness)
	 *  - missed guidelines: have all guidelines been fulfilled? if not reduced fitness; 2/5 guidelines missed -> 40% guideline penalty.  (50% impact on fitness)
	 * @param dayPlan
	 * @return fitness
	 */
	public float getFitness(DayPlan dayPlan) {
		// Rules
		List<Rule> nonGlobalRules = rules.stream().filter(rule -> rule.isMandatory && !"GLOBAL".equals(rule.scope)).collect(Collectors.toList());
		for (Rule rule : nonGlobalRules) {
			if (!matches(dayPlan, rule)) {
				System.out.println("DayPlan doesn't match rule: \n" + dayPlan + "\n" + rule);
				return 0f;
			}
		}
		// Guidelines
		float fitness = 1.0f;
		List<Rule> nonGlobalGuidelines = rules.stream().filter(rule -> !rule.isMandatory && !"GLOBAL".equals(rule.scope)).collect(Collectors.toList());
		int noGuidelines = nonGlobalGuidelines.size();
		int missedGuidelines = 0;
		float missedGuidelinesRatio = 0f; // 0 <= mGR <= 1
		if (noGuidelines > 0) {
			for (Rule guideline : nonGlobalGuidelines) {
				if (!matches(dayPlan, guideline)) {
					System.out.println("DayPlan doesn't match guideline: \n" + dayPlan + "\n" + guideline);
					missedGuidelines++;
				}
			}
			missedGuidelinesRatio = missedGuidelines / (float) noGuidelines;
			fitness -= 0.5f * missedGuidelinesRatio;
		}
		return fitness;
	}
	
	private boolean matches(DayPlan dayPlan, Rule guideline) {
		return true;
	}

	public DayPlan calculateDayPlan(DayOfWeek dayOfWeek) throws Exception {
		DayPlan dayPlan = new DayPlan();
		DayPlanInput dpi = inputsPerDay.get(dayOfWeek);
		dayPlan.setDayOfWeek(dayOfWeek);
		
		List<Person> personsForThisDay = persons.stream().filter(p -> p.schedule.getTimingInfoPerDay().get(dayOfWeek) != null).collect(Collectors.toList());
		
		/*
		 * PART 1: Solo drivers
		 */
		
		// add parties for solo drivers
		addPartiesForDesignatedDrivers(dayOfWeek, dayPlan, dpi.designatedDrivers);

		/*
		 * PART 2: There & back matches
		 * - for each first & last lesson combo: find the set of people that match and are not designated drivers
		 * - if set is not empty: create parties 
		 */
		Set<Person> coveredPersons = new HashSet<>(dpi.designatedDrivers);
		
		// This threshold defines how many drives a driver may already have to be considered. This will be increased in the while-loop if needed
		int driverConsiderationThreshold = 0;
		// Do this until all persons have been covered
		while (coveredPersons.size() < personsForThisDay.size()) {
			for (Person remainingPerson : personsForThisDay) {
				if (coveredPersons.contains(remainingPerson)) {
					continue;
				}
				List<PartyTouple> candidatesThere = new ArrayList<>();
				List<PartyTouple> candidatesBack = new ArrayList<>();
				for (PartyTouple pt : dayPlan.getPartyTouples()) {
					if (remainingPerson.schedule.getTimingInfoPerDay().get(dayOfWeek).getFirstLesson() == pt
							.getDriver().schedule.getTimingInfoPerDay().get(dayOfWeek).getFirstLesson()) {
						// remaining person could join this party (->)
						candidatesThere.add(pt);
					}
					if (remainingPerson.schedule.getTimingInfoPerDay().get(dayOfWeek).getLastLesson() == pt
							.getDriver().schedule.getTimingInfoPerDay().get(dayOfWeek).getLastLesson()) {
						// remaining person could join this party (<-)
						candidatesBack.add(pt);
					}
				}
				PartyTouple ptThere = getPreferredPartyTouple(remainingPerson, candidatesThere, false,
						dpi.designatedDrivers);
				PartyTouple ptBack = getPreferredPartyTouple(remainingPerson, candidatesBack, true,
						dpi.designatedDrivers);
				if (ptThere == null || ptBack == null) {
					if (numberOfDrives.get(remainingPerson) > driverConsiderationThreshold) {
						// this driver already has more drives than the threshold
						// look for another driver or reconsider when the threshold has been increased (while-loop)
						continue;
					}
					// no party available for one of the ways, create own party for others to join
					addSoloParty(dayPlan, remainingPerson, false);
					numberOfDrives.put(remainingPerson, numberOfDrives.get(remainingPerson) + 1);
				} else {
					ptThere.getPartyThere().addPassenger(remainingPerson);
					ptBack.getPartyBack().addPassenger(remainingPerson);
				}
				coveredPersons.add(remainingPerson);
			}
			// increases the driver consideration threshold to make sure we cover everyone eventually
			driverConsiderationThreshold++;
		}
		return dayPlan;
	}

	private PartyTouple getPreferredPartyTouple(Person personLookingForParty, List<PartyTouple> candidates, boolean isWayBack, Set<Person> designatedDrivers) {
		PartyTouple bestCandidate = null;
		Party bestParty = null;
		int bestCandidatesFreeSeats = -1;
		for (PartyTouple candidate : candidates) {
			int currentNoFreeSeats;
			int noPassengerSeats = candidate.getDriver().getNoPassengerSeats();
			Party party = isWayBack ? candidate.getPartyBack() : candidate.getPartyThere();
			int noPassengers = party.getPassengers().size();
			currentNoFreeSeats = noPassengerSeats - noPassengers;
			if (!(currentNoFreeSeats > 0)) continue;
			if (bestCandidatesFreeSeats < currentNoFreeSeats
					|| (bestCandidatesFreeSeats == currentNoFreeSeats && getPreferenceScore(party, designatedDrivers) > getPreferenceScore(bestParty, designatedDrivers))) {
				bestCandidate = candidate;
				bestParty = party;
				bestCandidatesFreeSeats = currentNoFreeSeats;
			}
		}
		return bestCandidate;
	}

	private int getPreferenceScore(Party party, Set<Person> designatedDrivers) {
		if (party == null) {
			return -1;
		}
		int score = 0;
		if (designatedDrivers.contains(party.getDriver())) score++;
		if (!(party.getDriver().getNoPassengerSeats() > party.getPassengers().size())) score = -10;
		return score;
	}

	private void addPartiesForDesignatedDrivers(DayOfWeek dayOfWeek, DayPlan dayPlan, Set<Person> designatedDrivers) throws Exception {
		for (Person driver : designatedDrivers ) {
			addSoloParty(dayPlan, driver, true);
		}
	}
	
	private void addSoloParty(DayPlan dayPlan, Person driver, boolean isDesignatedDriver) throws Exception {
		PartyTouple partyTouple = new PartyTouple();
		
		Party partyThere = new Party();
		partyThere.setDayOfTheWeek(dayPlan.getDayOfWeek());
		partyThere.setDriver(driver);
		partyThere.setWayBack(false);
		partyTouple.setPartyThere(partyThere);
		
		Party partyBack = new Party();
		partyBack.setDayOfTheWeek(dayPlan.getDayOfWeek());
		partyBack.setDriver(driver);
		partyBack.setWayBack(true);
		partyTouple.setPartyBack(partyBack);
		partyTouple.setDesignatedDriver(isDesignatedDriver);		
		dayPlan.addPartyTouple(partyTouple);
	}

	/**
	 * Returns a map of persons grouped by their first lesson.
	 * 
	 * @param dayOfWeek the day of the week needed to query the persons' schedules
	 * @return a map of persons grouped by their first lesson
	 */
	private Map<Integer, List<Person>> getPersonsByFirstLesson(List<Person> persons, DayOfWeek dayOfWeek) {
		Map<Integer, List<Person>> personsByFirstLesson = new HashMap<>(); 
		// place persons into groups based on first-lesson
		for (Person person : persons) {
			TimingInfo timingInfo = person.schedule.getTimingInfoPerDay().get(dayOfWeek);
			if (timingInfo != null) {
				int firstLesson = timingInfo.getFirstLesson();
				if (!personsByFirstLesson.containsKey(firstLesson)) {
					List<Person> list = new ArrayList<>();
					personsByFirstLesson.put(firstLesson, list);
				}
				personsByFirstLesson.get(firstLesson).add(person);
			}
		}
		return personsByFirstLesson;
	}

	/**
	 * Returns a map of persons grouped by their last lesson.
	 * 
	 * @param dayOfWeek the day of the week needed to query the persons' schedules
	 * @return a map of persons grouped by their last lesson
	 */
	private Map<Integer, List<Person>> getPersonsByLastLesson(List<Person> persons, DayOfWeek dayOfWeek) {
		Map<Integer, List<Person>> personsByLastLesson = new HashMap<>(); 
		// place persons into groups based on first-lesson
		for (Person person : persons) {
			TimingInfo timingInfo = person.schedule.getTimingInfoPerDay().get(dayOfWeek);
			if (timingInfo != null) {
				int lastLesson = timingInfo.getLastLesson();
				if (!personsByLastLesson.containsKey(lastLesson)) {
					List<Person> list = new ArrayList<>();
					personsByLastLesson.put(lastLesson, list);
				}
				personsByLastLesson.get(lastLesson).add(person);
			}
		}
		return personsByLastLesson;
	}

	/**
	 * Returns a set of persons that need to drive anyway because they are the only one in a time slot
	 * @param personsByFirstLesson map with persons by first lesson slot
	 * @param personsByLastLesson map with persons by last lesson slot
	 * @return a set of persons that need to drive anyway because they are the only one in a time slot
	 */
	private Set<Person> getDesignatedDrivers(Map<Integer, List<Person>> personsByFirstLesson,
			Map<Integer, List<Person>> personsByLastLesson) {
		Set<Person> designatedDrivers = new HashSet<>();
		for (List<Person> persons : personsByFirstLesson.values()) {
			if (persons.size() == 1) {
				designatedDrivers.add(persons.iterator().next());
			}
		}
		for (List<Person> persons : personsByLastLesson.values()) {
			if (persons.size() == 1) {
				designatedDrivers.add(persons.iterator().next());
			}
		}
		return designatedDrivers;
	}

	
}
