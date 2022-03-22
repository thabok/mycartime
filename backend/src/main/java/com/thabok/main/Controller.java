package com.thabok.main;

import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

import com.thabok.entities.DayOfWeekABCombo;
import com.thabok.entities.DayPlan;
import com.thabok.entities.DayPlanInput;
import com.thabok.entities.MasterPlan;
import com.thabok.entities.NumberOfDrivesStatus;
import com.thabok.entities.Party;
import com.thabok.entities.PartyTouple;
import com.thabok.entities.Person;
import com.thabok.helper.AlternativeDriverHelper;
import com.thabok.helper.ControllerInitHelper;
import com.thabok.helper.PartyHelper;
import com.thabok.helper.TimetableHelper;
import com.thabok.util.Util;

public class Controller {

	public static int referenceWeekStartDate;
	private Map<Integer, DayPlanInput> inputsPerDay = new HashMap<>();;
	private List<Person> persons;

	public Controller(List<Person> persons) {
		this.persons = persons;
		for (DayOfWeekABCombo dayOfWeekABCombo : Util.weekdayListAB) {
			DayPlanInput dpi = new DayPlanInput();
			dpi.personsByFirstLesson = ControllerInitHelper.getPersonsByStartTime(persons, dayOfWeekABCombo);
			dpi.personsByLastLesson = ControllerInitHelper.getPersonsByEndTime(persons, dayOfWeekABCombo);
			dpi.designatedDrivers = ControllerInitHelper.getDesignatedDrivers(dpi, persons, dayOfWeekABCombo);
			inputsPerDay.put(dayOfWeekABCombo.getUniqueNumber(), dpi);
		}
	}


	/**
	 * Main method to come up with a driving plan for the a & b week
	 * 
	 * @return the two-week-plan
	 * @throws Exception 
	 */
	public MasterPlan calculateWeekPlan() throws Exception {
		
		// this plan will be filled, optimized and finally proudly presented
		MasterPlan theMasterPlan = new MasterPlan(inputsPerDay);
		
		/*
		 * At this point, we have the following state  (not necessarily for every day):
		 * - a bunch of parties for designated drivers
		 */

		/*
		 * If someone is already driving a lot at this point (more than 4  times), let's try to reduce that
		 * by letting adding a tolerance on the wayThere (merges first-lesson with people who have hall-duty 
		 * before the first lesson).
		 */
		AlternativeDriverHelper.findAlternativeForSirDrivesALots(theMasterPlan, persons, inputsPerDay);
		
		/*
		 * Next up, we add people to existing parties _if possible_ and create new parties _when needed_
		 */
		coreAlgorithm(theMasterPlan);
		
		// TODO: Evaluate if "createPartyForPersonsWithZeroDrives(...)" is still needed / helps / hurts
		System.out.println();
		System.out.println(theMasterPlan);
		Util.summarizeNumberOfDrives(theMasterPlan, persons);
		System.out.println();
		
		return theMasterPlan;
	}

	/**
	 * Adds people to existing parties _if possible_ and create new parties _when needed_<br>
	 * - Persons to be placed are sorted based on their number of total drives (desc)<br>
	 * - For the creation of parties, we prefer people with a low noDrives for the resp. week, ideally already driving on the mirror day
	 */
	private void coreAlgorithm(MasterPlan theMasterPlan) throws Exception {
		NumberOfDrivesStatus nods = new NumberOfDrivesStatus(theMasterPlan, persons);
		Set<Person> coveredPersons = new HashSet<>(persons.size());
		while (coveredPersons.size() < persons.size()) {
			List<Person> frequentDriversSortedDesc = nods.getPersonsSortedByNumberOfDrive(false);
			Person person = Util.getNextUnhandledDriver(frequentDriversSortedDesc, coveredPersons);
			System.out.println();
			System.out.println(String.format(">>> %s (%s/%s) <<<", person, (coveredPersons.size() + 1), persons.size()));
			System.out.println();
			// iterate over the days
			for (DayOfWeekABCombo combo : Util.weekdayListAB) {
				// skip irrelevant or already covered days
				DayPlan dayPlan = theMasterPlan.get(combo.getUniqueNumber());
				boolean activeOnThisDay = TimetableHelper.isPersonActiveOnThisDay(person, combo);
				boolean coveredOnWayThere = Util.alreadyCoveredOnGivenDay(person, dayPlan, false);
				boolean coveredOnWayBack = Util.alreadyCoveredOnGivenDay(person, dayPlan, true);
				boolean alreadyCoveredOnThisDay = coveredOnWayThere && coveredOnWayBack;
				if (!activeOnThisDay || alreadyCoveredOnThisDay) {
					continue;
				}
				System.out.print(String.format("Trying to place %s (%s): ", person, combo));
				System.out.println("[" + (!coveredOnWayThere ? "-->" : "   ") + "|" + (!coveredOnWayThere ? "<--" : "   ") + "]");
				
				// try to find parties for this person
				for (PartyTouple pt : dayPlan.getPartyTouples()) {
					if (!coveredOnWayThere) {
						int startTime = person.getTimeForDowCombo(combo, false);
						// check if start time matches, etc.
						Party partyThere = pt.getPartyThere();
						if (partyThere.getTime() == startTime && PartyHelper.partyIsAvailable(partyThere) && partyThere.hasAFreeSeat()) {
							partyThere.addPassenger(person);
							coveredOnWayThere = true;
							System.out.println(String.format("  - Successfully placed %s with %s [-->]", person, pt.getDriver()));
						}
					}
					if (!coveredOnWayBack) {
						int endTime = person.getTimeForDowCombo(combo, true);
						// check if end time matches, etc.
						Party partyBack = pt.getPartyBack();
						if (partyBack.getTime() == endTime && PartyHelper.partyIsAvailable(partyBack) && partyBack.hasAFreeSeat()) {
							partyBack.addPassenger(person);
							coveredOnWayBack = true;
							System.out.println(String.format("  - Successfully placed %s with %s [<--]", person, pt.getDriver()));
						}
					}
				}
				
				// if not possible -> find 1-2 persons who can create a party (from the list of lazyDrivers)
				if (!coveredOnWayThere || !coveredOnWayBack) {
					System.out.println(String.format("  - %s could not be placed for there and back. Searching for a suitable person to start a new party:", person));
					PartyHelper.createPartiesThisPersonCanJoin(theMasterPlan, inputsPerDay, nods, person, dayPlan, coveredOnWayThere, coveredOnWayBack, persons);
				}
				
				// add frequentDriverPerson to covered persons
				coveredPersons.add(person);
			}
		}
	}

	
	@SuppressWarnings("unused")
	private void createPartyForPersonsWithZeroDrives(MasterPlan theMasterPlan) throws Exception {
		Person personWithLowestNumberOfDrives = getPersonWithLowestNumberOfDrives(theMasterPlan);
		// create parties until everybody drives at least 2 times
		while (new NumberOfDrivesStatus(theMasterPlan, persons).getNumberOfDrives().get(personWithLowestNumberOfDrives) < 2) {
			
			// FIXME: FILTERING NEEDED - CURRENTLY PARTIES CAN BE CREATED ON THE SAME DAY FOR PERSONS THAT COULD SHARE A RIDE!
			
			// 1. Get day with lowest number of partyTouples where the given person is active
			DayPlan dayPlanWithLowestNoParties = null;
			for (DayPlan dayPlan : theMasterPlan.getDayPlans().values()) {
				boolean relevantOnGivenDay = TimetableHelper.isPersonActiveOnThisDay(personWithLowestNumberOfDrives, dayPlan.getDayOfWeekABCombo());
				if (relevantOnGivenDay && (dayPlanWithLowestNoParties == null || dayPlan.getPartyTouples().size() < dayPlanWithLowestNoParties.getPartyTouples().size())) {
					dayPlanWithLowestNoParties = dayPlan;
				}
			}
			
			// 2. create a party for the given person on the given day
			System.out.println(String.format("Adding party for %s on %s", personWithLowestNumberOfDrives, dayPlanWithLowestNoParties.getDayOfWeekABCombo()));
			PartyHelper.addSoloParty(dayPlanWithLowestNoParties, personWithLowestNumberOfDrives, false, inputsPerDay, theMasterPlan.getDayPlans());
			
			// 3. update loop condition
			personWithLowestNumberOfDrives = getPersonWithLowestNumberOfDrives(theMasterPlan);
		}
		
	}


	private Person getPersonWithLowestNumberOfDrives(MasterPlan theMasterPlan) {
		Person personWithLowestNumberOfDrives = null;
		Map<Person, Integer> numberOfDrives = new NumberOfDrivesStatus(theMasterPlan, persons).getNumberOfDrives();
		for (Person person : persons) {
			if (personWithLowestNumberOfDrives == null || numberOfDrives.get(person) < numberOfDrives.get(personWithLowestNumberOfDrives) /* evenLower */) {
				personWithLowestNumberOfDrives = person;
			}
		}
		return personWithLowestNumberOfDrives;
	}


	/**
	 * Adapts the given plan to work with the updated
	 * <br>- persons' schedule
	 * <br>- persons' personal preferences 
	 * 
	 * @param preset the old plan - the new one should stay as close as possible to this
	 * @return the adapted plan
	 */
	public MasterPlan adaptPreset(MasterPlan preset) {
		// TODO Auto-generated method stub
		return null;
	}

}
