package com.thabok.helper;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Map.Entry;
import java.util.Set;

import com.thabok.entities.CustomDay;
import com.thabok.entities.DayOfWeekABCombo;
import com.thabok.entities.DayPlan;
import com.thabok.entities.DayPlanInput;
import com.thabok.entities.MasterPlan;
import com.thabok.entities.NumberOfDrivesStatus;
import com.thabok.entities.Party;
import com.thabok.entities.PartyTouple;
import com.thabok.entities.Person;
import com.thabok.entities.Reason;
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
            addSoloParty(dayPlan, driver, inputsPerDay, "designated driver", Reason.DESIGNATED_DRIVER);
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
     * @param lazyDriver 
     * @param dayPlans 
     * @return 
     * @throws Exception 
     */
    public static PartyTouple addSoloParty(DayPlan dayPlan, Person driver, Map<Integer, DayPlanInput> inputsPerDay, String reasonPhrase, Reason reason) throws Exception {
    	CustomDay driverPreferences = Util.getCustomDayObject(driver, dayPlan.getDayOfWeekABCombo());
    	// create party touple
    	PartyTouple partyTouple = new PartyTouple();
    	
    	// - way there
        Party partyThere = new Party(reasonPhrase);
        partyThere.setDayOfTheWeekABCombo(dayPlan.getDayOfWeekABCombo());
        partyThere.setDriver(driver);
        partyThere.setWayBack(false);
        int startTime = driver.getTimeForDowCombo(dayPlan.getDayOfWeekABCombo(), false);
        partyThere.setTime(startTime);
        if (driverPreferences.skipMorning) {
        	partyThere.setReason(Reason.LONELY_DRIVER);
        } else {
        	partyThere.setReason(reason);
        }
        partyTouple.setPartyThere(partyThere);
        
        // - way back
        Party partyBack = new Party(reasonPhrase);
        partyBack.setDayOfTheWeekABCombo(dayPlan.getDayOfWeekABCombo());
        partyBack.setDriver(driver);
        partyBack.setWayBack(true);
        int endTime = driver.getTimeForDowCombo(dayPlan.getDayOfWeekABCombo(), true);
        partyBack.setTime(endTime);
        if (driverPreferences.skipAfternoon) {
        	partyBack.setReason(Reason.LONELY_DRIVER);
        } else {
        	partyBack.setReason(reason);
        }
        partyTouple.setPartyBack(partyBack);
        partyTouple.setDesignatedDriver(Reason.DESIGNATED_DRIVER == reason);
   
        // add party touple to day plan
        dayPlan.addPartyTouple(partyTouple);

        return partyTouple;
    }
    
    /**
	 * Returns true if the party is generally available. This is not the case if the driver
	 * has selected to have no passengers for the morning/afternoon.
	 */
	public static boolean partyIsAvailable(Party party) {
		return canDriverTakePersons(party.getDriver(), party.getDayOfTheWeekABCombo(), party.isWayBack());
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
			} else if (!isWayBack && pt.getPartyThere().getPassengers().contains(person)) {
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
	 * @param reasonPhrase 
	 * @param persons 
	 */
	public static void createPartiesThisPersonCanJoin(MasterPlan theMasterPlan, Map<Integer, DayPlanInput> inputsPerDay, NumberOfDrivesStatus nods,
			Person personToBeSeated, DayPlan dayPlan, Party partyThere, Party partyBack, String reasonPhrase) throws Exception {
		DayOfWeekABCombo combo = dayPlan.getDayOfWeekABCombo();

		// set initial conditions based on requirements 
		boolean checkWayThere = partyThere == null;
		boolean checkWayBack = partyBack == null;
		
		// find best-suited person(s)
		List<Person> driverCandidates = nods.getPersonsSortedByNumberOfDrivesForGivenDay(combo);
		Person driverForWayThere = null;
		Person secondDriverForWayThere = null;
		Person driverForWayBack = null;
		Person secondDriverForWayBack = null;
		for (Person driverCandidate : driverCandidates) {
			/*
			 * Skip persons who:
			 * - have already been covered in the dayPlan
			 * - are not active on this day (as per their schedule)
			 * - didn't request to not drive on the day in question
			 */
			if (!TimetableHelper.isPersonActiveOnThisDay(driverCandidate, combo)
					|| Util.alreadyCoveredOnGivenDay(driverCandidate, dayPlan)
					|| Util.getCustomDayObject(driverCandidate, combo).drivingSkip) {
				continue;
			}

			if (checkWayThere) {
				int candidateStartTime = driverCandidate.getTimeForDowCombo(combo, false);
				if (!canDriverTakePersons(driverCandidate, combo, false)) {
					Util.out.println(String.format("  - Driver %s [-->] doesn't take passengers.", driverCandidate));
				} else {
					boolean timeMatches = personToBeSeated.getTimeForDowCombo(combo, false) == candidateStartTime;
					boolean timeMatchesWithTolerance = Util.isTimeDifferenceAcceptable(personToBeSeated.getTimeForDowCombo(combo, false), candidateStartTime);
					if (timeMatches) {
						driverForWayThere = driverCandidate;
						checkWayThere = false; // don't search any further
					} else if (timeMatchesWithTolerance) {
						secondDriverForWayThere = driverCandidate;
					}
				}
			}
			
			if (checkWayBack) {
				int candidateEndTime = driverCandidate.getTimeForDowCombo(combo, true);
				if (!canDriverTakePersons(driverCandidate, combo, true)) {
					Util.out.println(String.format("  - Driver %s [-->] doesn't take passengers.", driverCandidate));
				} else {
					boolean timeMatches = personToBeSeated.getTimeForDowCombo(combo, true) == candidateEndTime;
					boolean timeMatchesWithTolerance = Util.isTimeDifferenceAcceptable(personToBeSeated.getTimeForDowCombo(combo, true), candidateEndTime);
					if (timeMatches) {
						driverForWayBack = driverCandidate;
						checkWayBack = false; // don't search any further
					} else if (timeMatchesWithTolerance) {
						secondDriverForWayBack = driverCandidate;
					}
				}
			}
		}
		
		// switch to second driver if first choice (exact match) is not available
		int threshold = 5;
		if (driverForWayThere == null || (nods.getNumberOfDrives().get(driverForWayThere) > threshold && secondDriverForWayThere != null && nods.getNumberOfDrives().get(secondDriverForWayThere) <= threshold)) {
			driverForWayThere = secondDriverForWayThere; // can't be worse than this
		}
		if (driverForWayBack == null || (nods.getNumberOfDrives().get(driverForWayBack) > threshold && secondDriverForWayBack != null && nods.getNumberOfDrives().get(secondDriverForWayBack) <= threshold)) {
			driverForWayBack = secondDriverForWayBack; // can't be worse than this
		}

		/*
		 * Create parties based on driverForWayThere & driverForWayBack
		 */
		if ((partyThere == null && driverForWayThere == null) || (partyBack == null && driverForWayBack == null)) {
			// desperate situation...
			Util.out.println(String.format("  - No one found to take %s along -> creating new solo party.", personToBeSeated));
		
			// remove person from any previous parties
			removePersonFromParties(personToBeSeated, partyThere, partyBack);
			// create solo party
			addSoloParty(dayPlan, personToBeSeated, inputsPerDay, reasonPhrase + " > No one found to take " + personToBeSeated + " along -> needs solo party", Reason.ACCOMMODATE_PERSON);

		} else if (personToBeSeated.equals(driverForWayThere) || personToBeSeated.equals(driverForWayBack)) {
			// person to be seated seems to be the best candidate for a new party!
			
			// remove person from any previous parties
			removePersonFromParties(personToBeSeated, partyThere, partyBack);
			// create solo party
			addSoloParty(dayPlan, personToBeSeated, inputsPerDay, reasonPhrase + " > " + personToBeSeated + " is the best candidate for the party -> solo party", Reason.ACCOMMODATE_PERSON);
			Util.out.println(String.format("  - who would have thought: %s is the best candidate for a new party -> creating new solo party.", personToBeSeated));
			
		} else if (driverForWayThere != null && driverForWayThere.equals(driverForWayBack)) {
			// same person for there and back
			
			PartyTouple partyTouple = addSoloParty(dayPlan, driverForWayThere, inputsPerDay, reasonPhrase + " > same persons for there and back", Reason.ACCOMMODATE_PERSON);
			partyTouple.getPartyThere().addPassenger(personToBeSeated, reasonPhrase + " > same persons for there and back");
			partyTouple.getPartyBack().addPassenger(personToBeSeated, reasonPhrase + " > same persons for there and back");
			Util.out.println(String.format("  - %s creates a new party, %s can join in the morning and afternoon.", driverForWayThere, personToBeSeated));
			
		} else {
			// different persons driving there and back
			if (driverForWayThere != null) {
				PartyTouple partyToupleThere = addSoloParty(dayPlan, driverForWayThere, inputsPerDay, reasonPhrase + " > different persons for there and back", Reason.ACCOMMODATE_PERSON);
				partyToupleThere.getPartyThere().addPassenger(personToBeSeated, reasonPhrase + " > different persons for there and back");
				Util.out.println(String.format("  - %s creates a new party, %s can join in the morning.", driverForWayThere, personToBeSeated));
			}
			if (driverForWayBack != null) {
				PartyTouple partyToupleBack = addSoloParty(dayPlan, driverForWayBack, inputsPerDay, reasonPhrase + " > different persons for there and back", Reason.ACCOMMODATE_PERSON);
				partyToupleBack.getPartyBack().addPassenger(personToBeSeated, reasonPhrase + " > different persons for there and back");
				Util.out.println(String.format("  - %s creates a new party, %s can join in the afternoon.", driverForWayBack, personToBeSeated));
			}
			
		}
		
		// always keep up to date!
		nods.update(theMasterPlan);
	}


	public static void removePersonFromParties(Person personToRemove, Party ... parties) {
		for (Party party : parties) {
			if (party != null) {
				party.removePassenger(personToRemove);
			}
		}
	}
	
    public static Map<Integer, List<Party>> getPartiesByStartOrEndTime(List<Party> parties, boolean applyTolerances) {
    	Map<Integer, List<Party>> partiesByStartOrEndTime = new HashMap<>(); 
        // place persons into groups based on start/end time
        for (Party party : parties) {
        	if (PartyHelper.partyIsAvailable(party)) {
	            if (!partiesByStartOrEndTime.containsKey(party.getTime())) {
	                List<Party> list = new ArrayList<>();
	                partiesByStartOrEndTime.put(party.getTime(), list);
	            }
	            partiesByStartOrEndTime.get(party.getTime()).add(party);
        	}
        }
        if (!applyTolerances) {
        	return partiesByStartOrEndTime;
        }
        // merge stuff if tolerance shall be considered
        Map<Integer, List<Party>> partiesByTimeMerged = new HashMap<>();
        int lastReferenceTime = 0;
        List<Entry<Integer, List<Party>>> sortedEntries = new ArrayList<>(partiesByStartOrEndTime.entrySet());
        sortedEntries.sort((e1, e2) -> e1.getKey().compareTo(e2.getKey()));
        for (Entry<Integer, List<Party>> entry : sortedEntries) {
        	if (!Util.isTimeDifferenceAcceptable(entry.getKey(), lastReferenceTime)) {
                lastReferenceTime = entry.getKey();
                partiesByTimeMerged.put(lastReferenceTime, new ArrayList<>());
            }
        	partiesByTimeMerged.get(lastReferenceTime).addAll(entry.getValue());
        }
        return partiesByTimeMerged;
    }
	
}
