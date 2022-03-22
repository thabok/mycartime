package com.thabok.helper;

import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;

import com.thabok.entities.DayOfWeekABCombo;
import com.thabok.entities.DayPlan;
import com.thabok.entities.DayPlanInput;
import com.thabok.entities.MasterPlan;
import com.thabok.entities.NumberOfDrivesStatus;
import com.thabok.entities.Party;
import com.thabok.entities.PartyTouple;
import com.thabok.entities.Person;
import com.thabok.util.Util;

/**
 * Static helper class for anything related to Party management.
 * @author thabok
 */
public class PartyHelper {

	/**
     * Creates a solo party for each designatedDriver (isDesignatedDriver=true) and adds them to the dayPlan.
     * 
     * @param dayPlan the solo parties are added to this dayPlan
     * @param inputsPerDay set of designatedDrivers (must drive, no alternative)
     * @param dayPlans 
     * @throws Exception 
     */
    public static void addPartiesForDesignatedDrivers(DayPlan dayPlan, Map<Integer, DayPlanInput> inputsPerDay, Map<Integer, DayPlan> dayPlans) throws Exception {
        Set<Person> designatedDrivers = inputsPerDay.get(dayPlan.getDayOfWeekABCombo().getUniqueNumber()).designatedDrivers;
    	for (Person driver : designatedDrivers ) {
            addSoloParty(dayPlan, driver, true, inputsPerDay, dayPlans);
        }
    }
    
    
    /**
     * Creates a solo party for the given driver and adds it to the dayPlan.<br>
     * Also registers the driver as a mirror day driver for the mirror day, if he doesn't already drive on that day.
     * 
     * @param dayPlan the created solo party is added to this dayPlan
     * @param driver the driver
     * @param isDesignatedDriver true, if designatedDriver (must drive, no alternative)
     * @param inputsPerDay 
     * @param dayPlans 
     * @return 
     * @throws Exception 
     */
    public static PartyTouple addSoloParty(DayPlan dayPlan, Person driver, boolean isDesignatedDriver, Map<Integer, DayPlanInput> inputsPerDay, Map<Integer, DayPlan> dayPlans) throws Exception {
        // create party touple
    	PartyTouple partyTouple = new PartyTouple();
        
    	// - way there
        Party partyThere = new Party();
        partyThere.setDayOfTheWeekABCombo(dayPlan.getDayOfWeekABCombo());
        partyThere.setDriver(driver);
        partyThere.setWayBack(false);
        int startTime = driver.getTimeForDowCombo(dayPlan.getDayOfWeekABCombo(), false);
        partyThere.setTime(startTime);
        partyTouple.setPartyThere(partyThere);
        
        // - way back
        Party partyBack = new Party();
        partyBack.setDayOfTheWeekABCombo(dayPlan.getDayOfWeekABCombo());
        partyBack.setDriver(driver);
        partyBack.setWayBack(true);
        int endTime = driver.getTimeForDowCombo(dayPlan.getDayOfWeekABCombo(), true);
        partyBack.setTime(endTime);
        partyTouple.setPartyBack(partyBack);
        partyTouple.setDesignatedDriver(isDesignatedDriver);
   
        // add party touple to day plan
        dayPlan.addPartyTouple(partyTouple);

        /*
         *  FIXME: ----------------- Consider to remove this ---------------------
         */
        // register mirror day driver on mirror day
//        DayOfWeekABCombo mirrorCombo = Util.getMirrorCombo(dayPlan.getDayOfWeekABCombo());
//        DayPlan mirrorDayPlan = dayPlans.get(mirrorCombo.getUniqueNumber());
//        boolean driverDrivesOnMirrorDay = TimetableHelper.isPersonActiveOnThisDay(driver, mirrorCombo) && Util.drivesOnGivenDay(driver, mirrorDayPlan);
//        if (!driverDrivesOnMirrorDay) {
//        	DayPlanInput mirrorDayPlanInput = inputsPerDay.get(mirrorCombo.getUniqueNumber());
//        	mirrorDayPlanInput.mirrorDrivers.add(driver);
//        }
//        
//        // de-register mirror day driver for this day
//        inputsPerDay.get(dayPlan.getDayOfWeekABCombo().getUniqueNumber()).mirrorDrivers.remove(driver);
        /*
         *  FIXME: ---------------------- End of section ------------------------
         */
        
        return partyTouple;
    }
    
    /**
	 * Returns true if the party is generally available. This is not the case if the driver
	 * has selected to have no passengers for the morning/afternoon.
	 */
	public static boolean partyIsAvailable(Party party) {
		Person driver = party.getDriver();
		int customPreferenceIndex = Util.dowComboToCustomDaysIndex(party.getDayOfTheWeekABCombo());
		// in case of a partyThere: check if driver wants to be alone in the morning
		if (!party.isWayBack() && driver.customDays.get(customPreferenceIndex).skipMorning) {
			return false;
		}
		// in case of a partyBack: check if driver wants to be alone in the afternoon
		if (party.isWayBack() && driver.customDays.get(customPreferenceIndex).skipAfternoon) {
			return false;
		}
		return true;
		
	}
	
	public static PartyTouple getPartyToupleByPersonAndDay(Person person, DayPlan referencePlan) {
		Optional<PartyTouple> optional = referencePlan.getPartyTouples()
				.stream().filter(refTouple -> person.equals(refTouple.getDriver()))
				.findAny();
		if (optional.isPresent()) {
			return optional.get();
		} else {
			return null;
		}
	}
	
	public static PartyTouple getPartyToupleByPassengerAndDay(Person person, DayPlan referencePlan, boolean isWayBack) {
		for (PartyTouple pt : referencePlan.getPartyTouples()) {
			if (isWayBack && pt.getPartyBack().getPassengers().contains(person)) {
				return pt;
			} else if (pt.getPartyThere().getPassengers().contains(person)) {
				return pt;
			}
		}
		return null;
	}


	public static PartyTouple getPartyToupleByDriver(DayPlan dayPlan, Person driver) {
		for (PartyTouple pt : dayPlan.getPartyTouples()) {
			if (pt.getDriver().equals(driver)) {
				return pt;
			}
		}
		return null;
	}
	
	/**
	 * Finds the person(s) best suited to create a party and adds the frequenDriverPerson as a passenger.
	 * @param persons 
	 */
	public static void createPartiesThisPersonCanJoin(MasterPlan theMasterPlan, Map<Integer, DayPlanInput> inputsPerDay, NumberOfDrivesStatus nods,
			Person frequentDriverPerson, DayPlan dayPlan, boolean coveredOnWayThere, boolean coveredOnWayBack, List<Person> persons) throws Exception {
		DayOfWeekABCombo combo = dayPlan.getDayOfWeekABCombo();

		// set initial conditions based on requirements 
		boolean checkWayThere = !coveredOnWayThere;
		boolean checkWayBack = !coveredOnWayBack;
		
		// find best-suited person(s)
		List<Person> driverCandidates = nods.getPersonsSortedByNumberOfDrivesForGivenDay(combo);
		
		// FIXME: find out why this creates parties for Svenja who's already driving a lot!
		//         (maybe consider global drives, not just current week...)
		
		if (checkWayThere) {
			for (Person driverCandidate : driverCandidates) {
				/*
				 * Skip persons who:
				 * - have already been covered in the dayPlan
				 * - are the same person as the frequent driver we try to seat
				 * - are not active on this day (as per their schedule)
				 */
				if (frequentDriverPerson.equals(driverCandidate) || !TimetableHelper.isPersonActiveOnThisDay(driverCandidate, combo) || Util.alreadyCoveredOnGivenDay(driverCandidate, dayPlan)) {
					continue;
				}
	
				int candidateStartTime = driverCandidate.getTimeForDowCombo(combo, false);
				int candidateEndTime = driverCandidate.getTimeForDowCombo(combo, true);
			
				if (frequentDriverPerson.getTimeForDowCombo(combo, false) == candidateStartTime) {
					// Create party for person and add frequentDriver
					PartyTouple newPartyTouple = PartyHelper.addSoloParty(dayPlan, driverCandidate, false, inputsPerDay, theMasterPlan.getDayPlans());
					if (!partyIsAvailable(newPartyTouple.getPartyThere())) {
						System.out.println(String.format("  - New party driven by %s [-->] doesn't take passengers.", driverCandidate));
						continue;
					}
					System.out.println(String.format("  - Successfully placed %s into a new party. Driver: %s [-->]", frequentDriverPerson, driverCandidate));
					newPartyTouple.getPartyThere().addPassenger(frequentDriverPerson);
					checkWayThere = false;
					// Check if by chance this also satisfies the frequentDriver's way-back-needs
					if (checkWayBack && newPartyTouple.getPartyBack().getTime() == candidateEndTime) {
						newPartyTouple.getPartyBack().addPassenger(frequentDriverPerson);
						checkWayBack = false;
						System.out.println(String.format("  - Successfully placed %s into a new party. Driver: %s [<--]", frequentDriverPerson, driverCandidate));
					}
					break;
				}
			}
		}
		
		// always keep up to date!
		nods.update(theMasterPlan, persons);
		driverCandidates = nods.getPersonsSortedByNumberOfDrivesForGivenDay(combo);
		
		if (checkWayBack) {
			for (Person driverCandidate : driverCandidates) {
				/*
				 * Skip persons who:
				 * - have already been covered in the dayPlan
				 * - are the same person as the frequent driver we try to seat
				 * - are not active on this day (as per their schedule)
				 */
				if (frequentDriverPerson.equals(driverCandidate) || !TimetableHelper.isPersonActiveOnThisDay(driverCandidate, combo) || Util.alreadyCoveredOnGivenDay(driverCandidate, dayPlan)) {
					continue;
				}
	
				int candidateEndTime = driverCandidate.getTimeForDowCombo(combo, true);
				
				if (frequentDriverPerson.getTimeForDowCombo(combo, true) == candidateEndTime) {
					// Create party for person and add frequentDriver
					PartyTouple newPartyTouple = PartyHelper.addSoloParty(dayPlan, driverCandidate, false, inputsPerDay, theMasterPlan.getDayPlans());
					if (!partyIsAvailable(newPartyTouple.getPartyThere())) {
						System.out.println(String.format("  - New party driven by %s [-->] doesn't take passengers.", driverCandidate));
						continue;
					}
					System.out.println(String.format("  - Successfully placed %s into a new party. Driver: %s [<--]", frequentDriverPerson, driverCandidate));
					newPartyTouple.getPartyThere().addPassenger(frequentDriverPerson);
					checkWayBack = false;
					break;
				}
			}
		}
		
		// always keep up to date!
		nods.update(theMasterPlan, persons);
	}
	
}
