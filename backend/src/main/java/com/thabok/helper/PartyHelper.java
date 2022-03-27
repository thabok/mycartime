package com.thabok.helper;

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
	
	public static boolean canDriverTakePersons(Person driver, DayOfWeekABCombo combo, boolean isWayBack) {
		int customPreferenceIndex = Util.dowComboToCustomDaysIndex(combo);
		// in case of a partyThere: check if driver wants to be alone in the morning
		if (!isWayBack && driver.customDays.get(customPreferenceIndex).skipMorning) {
			return false;
		}
		// in case of a partyBack: check if driver wants to be alone in the afternoon
		if (isWayBack && driver.customDays.get(customPreferenceIndex).skipAfternoon) {
			return false;
		}
		return true;
	}
	
	public static Party getPartyToupleByPassengerAndDay(Person person, DayPlan referencePlan, boolean isWayBack) {
		for (PartyTouple pt : referencePlan.getPartyTouples()) {
			if (isWayBack && pt.getPartyBack().getPassengers().contains(person)) {
				return pt.getPartyBack();
			} else if (pt.getPartyThere().getPassengers().contains(person)) {
				return pt.getPartyThere();
			}
		}
		return null;
	}

	/**
	 * Returns the party the given person is driving with (as a driver or passenger). May return null
	 */
	public static Party getParty(DayPlan dayPlan, Person person, boolean isWayBack) {
		PartyTouple partyToupleByDriver = getPartyToupleByDriver(dayPlan, person);
		Party party = null;
		if (partyToupleByDriver != null) {
			party = isWayBack ? partyToupleByDriver.getPartyBack() : partyToupleByDriver.getPartyThere();
		} else {
			party = getPartyToupleByPassengerAndDay(person, dayPlan, isWayBack);
		}
		return party;
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
	 * Finds the person(s) best suited to create a party and adds the personToBeSeated as a passenger.
	 * @param persons 
	 */
	public static void createPartiesThisPersonCanJoin(MasterPlan theMasterPlan, Map<Integer, DayPlanInput> inputsPerDay, NumberOfDrivesStatus nods,
			Person personToBeSeated, DayPlan dayPlan, Party partyThere, Party partyBack, List<Person> persons) throws Exception {
		DayOfWeekABCombo combo = dayPlan.getDayOfWeekABCombo();

		// set initial conditions based on requirements 
		boolean checkWayThere = partyThere == null;
		boolean checkWayBack = partyBack == null;
		
		// find best-suited person(s)
		List<Person> driverCandidates = nods.getPersonsSortedByNumberOfDrivesForGivenDay(combo);
		Person driverForWayThere = null;
		Person driverForWayBack = null;
		for (Person driverCandidate : driverCandidates) {
			/*
			 * Skip persons who:
			 * - have already been covered in the dayPlan
			 * - are not active on this day (as per their schedule)
			 */
			if (!TimetableHelper.isPersonActiveOnThisDay(driverCandidate, combo) || Util.alreadyCoveredOnGivenDay(driverCandidate, dayPlan)) {
				continue;
			}

			if (checkWayThere) {
				int candidateStartTime = driverCandidate.getTimeForDowCombo(combo, false);
				if (!canDriverTakePersons(driverCandidate, combo, false)) {
					System.out.println(String.format("  - Driver %s [-->] doesn't take passengers.", driverCandidate));
					continue;
				}
				if (personToBeSeated.getTimeForDowCombo(combo, false) == candidateStartTime) {
					driverForWayThere = driverCandidate;
					checkWayThere = false; // don't search any further
				}
			}
			
			if (checkWayBack) {
				int candidateEndTime = driverCandidate.getTimeForDowCombo(combo, true);
				if (!canDriverTakePersons(driverCandidate, combo, true)) {
					System.out.println(String.format("  - Driver %s [-->] doesn't take passengers.", driverCandidate));
					continue;
				}
				if (personToBeSeated.getTimeForDowCombo(combo, true) == candidateEndTime) {
					driverForWayBack = driverCandidate;
					checkWayBack = false; // don't search any further
				}
			}
				
		}

		/*
		 * Create parties based on driverForWayThere & driverForWayBack
		 */
		if ((partyThere == null && driverForWayThere == null) || (partyBack == null && driverForWayBack == null)) {
			// desperate situation...
			System.out.println(String.format("  - No one found to take %s along -> creating new solo party.", personToBeSeated));
		
			// remove person from any previous parties
			removePersonFromParties(personToBeSeated, partyThere, partyBack);
			// create solo party
			PartyHelper.addSoloParty(dayPlan, personToBeSeated, false, inputsPerDay, theMasterPlan.getDayPlans());

		} else if (personToBeSeated.equals(driverForWayThere) || personToBeSeated.equals(driverForWayBack)) {
			// person to be seated seems to be the best candidate for a new party!
			
			// remove person from any previous parties
			removePersonFromParties(personToBeSeated, partyThere, partyBack);
			// create solo party
			PartyHelper.addSoloParty(dayPlan, personToBeSeated, false, inputsPerDay, theMasterPlan.getDayPlans());
			System.out.println(String.format("  - who would have though: %s is the best candidate for a new party -> creating new solo party.", personToBeSeated));
			
		} else if (driverForWayThere != null && driverForWayThere.equals(driverForWayBack)) {
			// same person for there and back
			
			PartyTouple partyTouple = PartyHelper.addSoloParty(dayPlan, driverForWayThere, false, inputsPerDay, theMasterPlan.getDayPlans());
			partyTouple.getPartyThere().addPassenger(personToBeSeated);
			partyTouple.getPartyBack().addPassenger(personToBeSeated);
			System.out.println(String.format("  - %s creates a new party, %s can join in the morning and afternoon.", driverForWayThere, personToBeSeated));
			
		} else {
			// different persons driving there and back
			if (driverForWayThere != null) {
				PartyTouple partyToupleThere = PartyHelper.addSoloParty(dayPlan, driverForWayThere, false, inputsPerDay, theMasterPlan.getDayPlans());
				partyToupleThere.getPartyThere().addPassenger(personToBeSeated);
				System.out.println(String.format("  - %s creates a new party, %s can join in the morning.", driverForWayThere, personToBeSeated));
			}
			if (driverForWayBack != null) {
				PartyTouple partyToupleBack = PartyHelper.addSoloParty(dayPlan, driverForWayBack, false, inputsPerDay, theMasterPlan.getDayPlans());
				partyToupleBack.getPartyBack().addPassenger(personToBeSeated);
				System.out.println(String.format("  - %s creates a new party, %s can join in the afternoon.", driverForWayBack, personToBeSeated));
			}
			
		}
		
		// always keep up to date!
		nods.update(theMasterPlan, persons);
	}


	public static void removePersonFromParties(Person personToRemove, Party ... parties) {
		for (Party party : parties) {
			if (party != null) {
				party.removePassenger(personToRemove);
			}
		}
	}
	
}
