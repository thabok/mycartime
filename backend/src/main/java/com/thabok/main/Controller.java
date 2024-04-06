package com.thabok.main;

import java.nio.file.Files;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.Stack;
import java.util.stream.Collectors;

import com.thabok.entities.DayOfWeekABCombo;
import com.thabok.entities.DayPlan;
import com.thabok.entities.DayPlanInput;
import com.thabok.entities.MasterPlan;
import com.thabok.entities.NumberOfDrivesStatus;
import com.thabok.entities.Party;
import com.thabok.entities.PartyTuple;
import com.thabok.entities.Person;
import com.thabok.entities.Reason;
import com.thabok.helper.AlternativeDriverHelper;
import com.thabok.helper.PartyHelper;
import com.thabok.helper.PlanOptimizationHelper;
import com.thabok.helper.TimetableHelper;
import com.thabok.io.HtmlDump;
import com.thabok.util.Constants;
import com.thabok.util.Util;

public class Controller {

    public static int referenceWeekStartDate;

    /**
     * Entry point to calulcate a week plan based on a given preset
     */
    public MasterPlan calculateWeekPlan(MasterPlan preset) throws Exception {
    	assert preset != null : "This interface of calculateWeekPlan requires a non-null preset";
    	return calculateWeekPlan(preset.persons, preset);
    }
    
    /**
     * Entry point to calulcate a fresh week plan
     */
    public MasterPlan calculateWeekPlan(List<Person> persons) throws Exception {
    	assert persons != null : "This interface of calculateWeekPlan requires a non-null list of persons";
    	return calculateWeekPlan(persons, null);
    }
    
    public MasterPlan calculateWeekPlan(List<Person> persons, MasterPlan preset) throws Exception {
        
        MasterPlan theMasterPlan = new MasterPlan(persons, preset);
    	HtmlDump.toHtml(theMasterPlan, "/Users/thabok/Git/mycartime/plan_dump_1.html");
        
        /*
         * At this point, we have the following state  (not necessarily for every day):
         * - a bunch of parties for designated drivers
         */

    	/*
    	 * If someone is already driving a lot at this point (more than 4  times), let's try to reduce that
    	 * by adding a tolerance on the wayThere (merges first-lesson with people who have hall-duty 
    	 * before the first lesson).
    	 */
    	AlternativeDriverHelper.findAlternativeForSirDrivesALots(theMasterPlan);
    	HtmlDump.toHtml(theMasterPlan, "/Users/thabok/Git/mycartime/plan_dump_2.html");

    	/*
    	 * Check who can help with a party (based on global number of drives)
    	 */
    	globallyBalancedSelectionOfDrivers(theMasterPlan);
    	
    	
        /*
         * Next up, we add people to existing parties _if possible_ and create new parties _when needed_
         */
        coreAlgorithm(theMasterPlan);
        HtmlDump.toHtml(theMasterPlan, "/Users/thabok/Git/mycartime/plan_dump_3.html");
        
        /*
         * Fill add drives for lazy drivers while trying to optimize:
         * - A/B week symetry
         * - additional parties on days where it's tight
         */
        addPartiesForLazyDrivers(theMasterPlan);
        HtmlDump.toHtml(theMasterPlan, "/Users/thabok/Git/mycartime/plan_dump_4.html");
        
        /*
         * Once we've done everything we can to make sure, no one drives more often than needed
         * it's time to balance the passengers in the different cars. The core algorithm doesn't care about that.
         */
	    // FIXME: currently ignores people's sizes (too many tall people in small cars)
        // FIXME: currently doesn't try to keep passengers with the same driver between A & B week (if possible)
        balancePassengersInCars(theMasterPlan);
        HtmlDump.toHtml(theMasterPlan, "/Users/thabok/Git/mycartime/plan_dump_5.html");
        
        /*
         * Printy printy all the stuffy stuffs
         */
        Util.out.println();
		Util.out.println();
        Util.printDrivingDaysAbMap(theMasterPlan);     
        Util.summarizeNumberOfDrives(theMasterPlan);
        return theMasterPlan;
    }

    private Map<DayOfWeekABCombo, Set<Person>> findPossiblePartyStarters(MasterPlan theMasterPlan) {
    	// at this point, we have some designated drivers (or replacement drivers)
    	Map<DayOfWeekABCombo, Set<Person>> possiblePartyStartersByCombo = new HashMap<>();
    	for (DayPlan dp : theMasterPlan.getDayPlans().values()) {
    		DayPlanInput pool = theMasterPlan.inputsPerDay.get(dp.getDayOfWeekABCombo().getUniqueNumber());
    		// find times where there are more people than we could place in existing parties (demand > supply)
    		Set<Person> sbPersonsInParties = new HashSet<>();
    		Set<Person> hbPersonsInParties = new HashSet<>();
    		for (PartyTuple pt : dp.getPartyTuples()) {
    			sbPersonsInParties.add(pt.getSchoolboundParty().getDriver());
    			sbPersonsInParties.addAll(pt.getSchoolboundParty().getPassengers());
    			hbPersonsInParties.add(pt.getHomeboundParty().getDriver());
    			hbPersonsInParties.addAll(pt.getHomeboundParty().getPassengers());
    		}
    		
    		// add possibel party starters to the set
    		Set<Person> possiblePartyStarters = new HashSet<>();
    		collectCandidatesAndPlaceFromPool(dp, possiblePartyStarters, pool.personsByFirstLesson, sbPersonsInParties, true);
    		collectCandidatesAndPlaceFromPool(dp, possiblePartyStarters, pool.personsByLastLesson, hbPersonsInParties, false);
    		
    		// put possiblePartyStarters set into Map per day-combo
    		possiblePartyStartersByCombo.put(dp.getDayOfWeekABCombo(), possiblePartyStarters);
    	}
    	return possiblePartyStartersByCombo;
    }
    
    /**
     * Collects party starter candidates where the supply (plan) doesn't meet the demand (pool).
     * Places people into parties where the supply (plan) meets the demand (pool).
     *  
     * @param dp
     * @param possiblePartyStarters
     * @param pool
     * @param ignoreList
     * @param isSchoolbound 
     */
    private void collectCandidatesAndPlaceFromPool(DayPlan dp, Set<Person> possiblePartyStarters, Map<Integer, List<Person>> pool, Set<Person> ignoreList, boolean isSchoolbound) {
    	for (Integer startTime : pool.keySet()) {
			List<Party> partiesMatchingStartTime = dp.getPartyTuples().stream().map(pt -> isSchoolbound ? pt.getSchoolboundParty() : pt.getHomeboundParty()).filter(party -> Util.isTimeDifferenceAcceptable(party.getTime(), startTime)).collect(Collectors.toList());
			Set<Person> personsInPool = pool.get(startTime).stream().filter(p -> !ignoreList.contains(p)).collect(Collectors.toSet());
			int demand = personsInPool.size();
			int supply = 0;
			for (Party p : partiesMatchingStartTime) { supply += p.getNumberOfFreeSeats(); }
			if (demand > supply) {
				possiblePartyStarters.addAll(personsInPool);
			} else {
				// all members of this pool timeslot can be placed (supply >= demand)
				for (Party p : partiesMatchingStartTime) {
					while (!personsInPool.isEmpty() &&  p.getNumberOfFreeSeats() > 0) {
						Person sbPersonFromPool = personsInPool.iterator().next();
						p.addPassenger(sbPersonFromPool, "supply >= demand for this timeslot");
						personsInPool.remove(sbPersonFromPool);
					}
				}
			}
		}
    }
    
    private void globallyBalancedSelectionOfDrivers(MasterPlan theMasterPlan) throws Exception {
    	
    	
    	//FIXME broken af
    	if (System.out.equals(Util.out)) {
    		HtmlDump.toHtml(theMasterPlan, "/Users/thabok/Git/mycartime/plan_dump_gbsod.html");
    		// attempt a maximum of 20 iterations, end if no further progress is being made
    		for (int i=1; i<25; i++) {
    			Map<DayOfWeekABCombo, Set<Person>> possiblePartyStarters = findPossiblePartyStarters(theMasterPlan);
        		if (possiblePartyStarters.isEmpty()) { break; }
    			createMirroredParties(theMasterPlan, possiblePartyStarters);
    			// backup old dump
    			Files.copy(Paths.get("/Users/thabok/Git/mycartime/plan_dump_gbsod.html"), Paths.get("/Users/thabok/Git/mycartime/plan_dump_gbsod_old.html"), StandardCopyOption.REPLACE_EXISTING);
    			HtmlDump.toHtml(theMasterPlan, "/Users/thabok/Git/mycartime/plan_dump_gbsod.html");
    		}
    	}
	}

	private void createMirroredParties(MasterPlan theMasterPlan, Map<DayOfWeekABCombo, Set<Person>> possiblePartyStarters) throws Exception {

		// 1. try to find people who
		// - with no. drives <= (Constants.EXPECTED_DRIVING_DAYS_THRESHOLD - 2)
		// - who can drive on a given day and its mirror day (e.g. day 1 and day 8 or day 9 and day 2) 
		
		Set<DayOfWeekABCombo> coveredCombos = new HashSet<>();
		for (DayOfWeekABCombo combo : possiblePartyStarters.keySet()) {
			// skip combos for which we already have a candidate (created via mirror combo)
			if (!coveredCombos.contains(combo)) {
				NumberOfDrivesStatus nods = new NumberOfDrivesStatus(theMasterPlan);
    			DayOfWeekABCombo mirrorCombo = Util.getMirrorCombo(combo);
    			Set<Person> todaysCandidates = possiblePartyStarters.get(combo);
    			Set<Person> mirrorDaysCandidates = possiblePartyStarters.get(mirrorCombo);
    			// create a set that only contains candidates that are present in both sets
    			Set<Person> intersection = new HashSet<>(todaysCandidates);
    			intersection.retainAll(mirrorDaysCandidates);
    			intersection.retainAll(intersection);
    			
    			List<Person> personsSortedByNumberOfDrives = nods.getPersonsSortedByNumberOfDrive(true);
    			// there are valid candidates for both days
    			for (Person personWithLowNods : personsSortedByNumberOfDrives) {
    				boolean nodsBelowThreshold = nods.getNumberOfDrives().get(personWithLowNods) < (Constants.EXPECTED_DRIVING_DAYS_THRESHOLD - 2);
    				if (nodsBelowThreshold && intersection.contains(personWithLowNods)) {
    					DayPlan dp1 = theMasterPlan.get(combo.getUniqueNumber());
    					DayPlan dp2 = theMasterPlan.get(mirrorCombo.getUniqueNumber());
    					// first remove person from (could be a passenger somewhere)
    					PartyHelper.removePersonFromParties(personWithLowNods, dp1.getAllParties());
    					PartyHelper.removePersonFromParties(personWithLowNods, dp2.getAllParties());
    					// create solo party
    					PartyHelper.addSoloParty(dp1, personWithLowNods, "balancedSelectionOfDrivers", Reason.BALANCED_SELECTION_OF_DRIVERS);
    					PartyHelper.addSoloParty(dp2, personWithLowNods, "balancedSelectionOfDrivers", Reason.BALANCED_SELECTION_OF_DRIVERS);
    					Util.out.println("Adding party for " + personWithLowNods + " - " + combo + ", " + mirrorCombo);

    					// these combos can be skipped in future loop iterations
    					coveredCombos.add(combo);
    					coveredCombos.add(mirrorCombo);
    					break;
    				}
    			}
			}
		}
		
		// 2. try the same but ignore mirror days
		for (DayOfWeekABCombo combo : possiblePartyStarters.keySet()) {
			// skip combos for which we already have a candidate
			if (!coveredCombos.contains(combo)) {
				NumberOfDrivesStatus nods = new NumberOfDrivesStatus(theMasterPlan);
    			Set<Person> todaysCandidates = possiblePartyStarters.get(combo);
    			
    			List<Person> personsSortedByNumberOfDrives = nods.getPersonsSortedByNumberOfDrive(true);
    			// there are valid candidates for both days
    			for (Person personWithLowNods : personsSortedByNumberOfDrives) {
    				boolean nodsBelowThreshold = nods.getNumberOfDrives().get(personWithLowNods) < (Constants.EXPECTED_DRIVING_DAYS_THRESHOLD - 1);
    				if (nodsBelowThreshold && todaysCandidates.contains(personWithLowNods)) {
    					DayPlan dp = theMasterPlan.get(combo.getUniqueNumber());
    					// first remove person from (could be a passenger somewhere)
    					PartyHelper.removePersonFromParties(personWithLowNods, dp.getAllParties());
    					// create solo party
    					PartyHelper.addSoloParty(dp, personWithLowNods, "balancedSelectionOfDrivers", Reason.BALANCED_SELECTION_OF_DRIVERS);
    					Util.out.println("Adding party for " + personWithLowNods + " - " + combo);
    					
    					// these combos can be skipped in future loop iterations
    					coveredCombos.add(combo);
    					break;
    				}
    			}
			}
		}
	}

	/**
     * Ensure no one drives less than 4 times:
     * - Add parties on days where it's tight (capacity close to 100%)
     * - Add parties to complete unmatched mirror days
     * @param theMasterPlan 
     * @throws Exception 
     */
    private void addPartiesForLazyDrivers(MasterPlan theMasterPlan) throws Exception {
    	List<Person> personsToConsider = new ArrayList<>(theMasterPlan.persons);
        while (true) {
            NumberOfDrivesStatus nods = new NumberOfDrivesStatus(theMasterPlan);
            Person lowNodsPerson = Util.getPersonWithLowestNumberOfDrives(personsToConsider, nods.getNumberOfDrives());
            if (nods.getNumberOfDrives().get(lowNodsPerson) >= 4) {
                // we're done here
                break;
            }
            // create party for this person
            List<DayPlan> dayPlans = getAvailableDays(theMasterPlan, lowNodsPerson);
            if (dayPlans.isEmpty()) {
            	personsToConsider.remove(lowNodsPerson);
            	continue;
            }
            DayPlan dayPlan = PlanOptimizationHelper.getDayPlanForLazyDriver(dayPlans, lowNodsPerson);
            Party partyThere = PartyHelper.getParty(dayPlan, lowNodsPerson, false);
            Party partyBack  = PartyHelper.getParty(dayPlan, lowNodsPerson, true);
            PartyHelper.removePersonFromParties(lowNodsPerson, partyThere, partyBack);
            PartyHelper.addSoloParty(dayPlan, lowNodsPerson, "addPartiesForLazyDrivers", Reason.LAZY_DRIVER);
            Util.out.println("Creating lazy driver party for " + lowNodsPerson + " on " + dayPlan.getDayOfWeekABCombo());
        }
    }
    
    /**
     * Return the available days. If there are missing mirror days, only those will be returned.
     */
    private List<DayPlan> getAvailableDays(MasterPlan theMasterPlan, Person lowNodsPerson) {
    	List<DayPlan> dayPlans = Util.getMissingMirrorDays(theMasterPlan, lowNodsPerson).stream()
        		.filter(dp -> {
	                boolean generallyAvailable = TimetableHelper.isPersonActiveOnThisDay(lowNodsPerson, dp.getDayOfWeekABCombo());
	                boolean notAlreadyDriving = !Util.drivesOnGivenDay(lowNodsPerson, dp);
	                boolean drivingSkipRequested = lowNodsPerson.getCustomPrefsForCombo(dp.getDayOfWeekABCombo()).drivingSkip;
	                return generallyAvailable && notAlreadyDriving && !drivingSkipRequested;
	            })
	            .collect(Collectors.toList());
        if (dayPlans.isEmpty()) {
            dayPlans = theMasterPlan.getDayPlans().values().stream()
                .filter(dp -> {
                    boolean generallyAvailable = TimetableHelper.isPersonActiveOnThisDay(lowNodsPerson, dp.getDayOfWeekABCombo());
                    boolean notAlreadyDriving = !Util.drivesOnGivenDay(lowNodsPerson, dp);
                    boolean drivingSkipRequested = lowNodsPerson.getCustomPrefsForCombo(dp.getDayOfWeekABCombo()).drivingSkip;
                    return generallyAvailable && notAlreadyDriving && !drivingSkipRequested;
                })
                .collect(Collectors.toList());
        }
		return dayPlans;
	}

	/**
     * Balances the passengers in equivalent parties to prevent the "party bus vs. lonely driver" situation
     */
    private void balancePassengersInCars(MasterPlan theMasterPlan) {
        for (DayPlan dp : theMasterPlan.getDayPlans().values()) {
            int mirrorDayNumber = Util.getRefComboInt(dp.getDayOfWeekABCombo().getUniqueNumber());
            DayPlan referenceDayPlan = theMasterPlan.getDayPlans().get(mirrorDayNumber);

            List<Party> partiesThere = dp.getPartyTuples().stream()
				.map(pt -> pt.getSchoolboundParty())
				.filter(p -> PartyHelper.partyIsAvailable(p))
				.collect(Collectors.toList());
            List<Party> partiesBack = dp.getPartyTuples().stream()
				.map(pt -> pt.getHomeboundParty())
				.filter(p -> PartyHelper.partyIsAvailable(p))
				.collect(Collectors.toList());
            
            Map<Integer, List<Party>> wayTherePartiesByStartTime = PartyHelper.getPartiesByStartOrEndTime(partiesThere, true);
            Map<Integer, List<Party>> wayBackPartiesByEndTime = PartyHelper.getPartiesByStartOrEndTime(partiesBack, true);
            
            wayTherePartiesByStartTime.values().forEach(eqParties -> balancePassengers(eqParties, referenceDayPlan));
            wayBackPartiesByEndTime.values().forEach(eqParties -> balancePassengers(eqParties, referenceDayPlan));

            dp.passengersBalanced = true;
//            for (PartyTuple pt : dp.getPartyTuples()) {
//            	asdf(pt.getPartyThere(), partiesThere);
//            	asdf(pt.getPartyBack(), partiesBack);
//            }
        }
    }
    
    private void asdf(Party party, List<Party> availableParties) {
    	List<Person> unmatchedPassengers = party.getPassengers().stream().filter(passenger -> party.getTime() != passenger.getTimeForDowCombo(party.getDayOfTheWeekABCombo(), party.isWayBack())).collect(Collectors.toList());
    	for (Person unmatchedPassenger : unmatchedPassengers) {
    		List<Party> list = PartyHelper.getPartiesByStartOrEndTime(availableParties, false).get(unmatchedPassenger.getTimeForDowCombo(party.getDayOfTheWeekABCombo(), party.isWayBack()));
    		if (list != null && !list.isEmpty()) {
    			System.out.println("Unmatched passenger " + unmatchedPassenger + " drives with " + party + " (" + party.getTime() + ") although he could be driving with " + list.get(0) + "(" + list.get(0).getTime() + ")");
    		}
    	}
    }

	/**
	 * Takes a list of equivalent parties and balances the passengers
	 */
    private void balancePassengers(List<Party> equivalentParties, DayPlan referenceDayPlan) {
        if (equivalentParties.size() > 1) {

			// remove all passengers from the parties
        	Stack<Person> passengersBuffer = new Stack<>();
        	equivalentParties.forEach(p -> passengersBuffer.addAll(p.removePassengers()));

        	// distribute perfect matches (based on time)
        	Stack<Person> passengersWithNoPerfectMatch = new Stack<>();
        	Map<Party, Integer> skipNextNTimes = new HashMap<>(equivalentParties.size());
        	equivalentParties.forEach(p -> skipNextNTimes.put(p, 0));
			while (!passengersBuffer.isEmpty()) {
				Person peekedPassenger = passengersBuffer.peek();
				int passengerTime = peekedPassenger.getTimeForDowCombo(equivalentParties.get(0).getDayOfTheWeekABCombo(), equivalentParties.get(0).isWayBack());
				Optional<Party> optPerfectMatch = equivalentParties.stream()
						.filter(p -> p.hasAFreeSeat() && p.getTime() == passengerTime)
						.sorted((p1, p2) -> skipNextNTimes.get(p1).compareTo(skipNextNTimes.get(p2)))
						.findFirst();
				if (optPerfectMatch.isPresent()) {
					Party perfectMatch = optPerfectMatch.get();
					perfectMatch.addPassenger(passengersBuffer.pop(), "balancePassengersInCars > balancePassengers > distrubute perfect matches");
					skipNextNTimes.put(perfectMatch, skipNextNTimes.get(perfectMatch) + 1);
				} else {
					passengersWithNoPerfectMatch.push(passengersBuffer.pop());
				}
			}
			
			// redistribute remaining passengers in a round-robin fashion
			int eqPartiesIndex = 0;
			while (!passengersWithNoPerfectMatch.isEmpty()) {
				// get party based on index and add passenger if possible
				Party party = equivalentParties.get(eqPartiesIndex);
				
				// add passenger to party if possible
				if (skipNextNTimes.get(party) > 0) {
					// party has received perfect matches, skip until other parties 
					// had the chance to add the same number of passengers
					skipNextNTimes.put(party, skipNextNTimes.get(party) - 1);
				} else {
					if (party.hasAFreeSeat()) {
						party.addPassenger(passengersWithNoPerfectMatch.pop(), "balancePassengersInCars > balancePassengers > redistrubute round-robin");
					}
				}

				// round-robin index iteration
				eqPartiesIndex = (eqPartiesIndex + 1) % equivalentParties.size();
			}

		}
        
        
    }


    /**
     * Adds people to existing parties _if possible_ and create new parties _when needed_<br>
     * - Persons to be placed are sorted based on their number of total drives (desc)<br>
     * - For the creation of parties, we prefer people with a low noDrives for the resp. week, ideally already driving on the mirror day<br>
     * - The result is still slightly imbalanced, due to the nature of the approach<br>
     * - Also the passengers need to be rebalanced (there may be to parties at the same time with one full car and one pretty empty car)
     */
    private void coreAlgorithm(MasterPlan theMasterPlan) throws Exception {
        NumberOfDrivesStatus nods = new NumberOfDrivesStatus(theMasterPlan);
        Set<Person> coveredPersons = new HashSet<>(theMasterPlan.persons.size());
        while (coveredPersons.size() < theMasterPlan.persons.size()) {
            List<Person> frequentDriversSortedDesc = nods.getPersonsSortedByNumberOfDrive(false);
            Person person = Util.getNextUnhandledDriver(frequentDriversSortedDesc, coveredPersons);
            Util.out.println(String.format("\n>>> %s (%s/%s) <<<\n", person, (coveredPersons.size() + 1), theMasterPlan.persons.size()));
            // first process missing mirror days in case 'person' is picked to start their own party 
            for (DayPlan dp : Util.getMissingMirrorDays(theMasterPlan, person)) {
                findOrCreateParty(theMasterPlan, nods, coveredPersons, frequentDriversSortedDesc, person, dp.getDayOfWeekABCombo(), "coreAlgorithm > findOrCreateParty > MissingMirrorDays");
            }
            // iterate over the days
            for (DayOfWeekABCombo combo : Util.weekdayListAB) {
                findOrCreateParty(theMasterPlan, nods, coveredPersons, frequentDriversSortedDesc, person, combo, "coreAlgorithm > findOrCreateParty > RemainingDays");
            }
            // add frequentDriverPerson to covered persons
            coveredPersons.add(person);
        }
    }


    private void findOrCreateParty(MasterPlan theMasterPlan, NumberOfDrivesStatus nods, Set<Person> coveredPersons,
            List<Person> frequentDriversSortedDesc, Person person, DayOfWeekABCombo combo, String reasonPhrase) throws Exception {
        // skip irrelevant or already covered days
        DayPlan dayPlan = theMasterPlan.get(combo.getUniqueNumber());
        boolean activeOnThisDay = TimetableHelper.isPersonActiveOnThisDay(person, combo);
        Party partyThere = PartyHelper.getParty(dayPlan, person, false);
        Party partyBack = PartyHelper.getParty(dayPlan, person, true);
        Party partyThereWithWaitingTime = null;
        Party partyBackWithWaitingTime = null;
        
        boolean alreadyCoveredOnThisDay = (partyThere != null) && (partyBack != null);
        if (!activeOnThisDay || alreadyCoveredOnThisDay) {
            return;
        }
        nods.update(theMasterPlan);
        Util.out.print(String.format("[%s] Trying to place %s (%s): ", combo, person, nods.getNumberOfDrives().get(person)));
        Util.out.println("[" + (!((partyThere != null)) ? "-->" : "   ") + "|" + (!((partyBack != null)) ? "<--" : "   ") + "]");
        
        // try to find parties for this person
        for (PartyTuple pt : dayPlan.getPartyTuples()) {
            Party[] partiesToJoinThere = findPartyToJoin(person, pt, partyThere, partyThereWithWaitingTime, combo, false, reasonPhrase + " > findPartyToJoin");
            partyThere = partiesToJoinThere[0];
            partyThereWithWaitingTime = partiesToJoinThere[1];
            Party[] partiesToJoinBack = findPartyToJoin(person, pt, partyBack, partyBackWithWaitingTime, combo, true, reasonPhrase + " > findPartyToJoin");
            partyBack = partiesToJoinBack[0];
            partyBackWithWaitingTime = partiesToJoinBack[1];
        }
        
        // if we don't have matches for both ways, consider party with waiting time
        if (partyThere == null && partyThereWithWaitingTime != null) {
            partyThere = partyThereWithWaitingTime;
            partyThere.addPassenger(person, reasonPhrase);
        }
        if (partyBack == null && partyBackWithWaitingTime != null) {
            partyBack = partyBackWithWaitingTime;
            partyBack.addPassenger(person, reasonPhrase);
        }
        
        // if not possible -> find 1-2 persons who can create a party
        if ((partyThere == null) || (partyBack == null)) {
            if (partyThere == null) Util.out.println("  - Didn't find a party to join for the morning.");
            if (partyBack == null) Util.out.println("  - Didn't find a party to join for the afternoon.");
            Util.out.println("  - Searching for a suitable person to start a new party...");
            PartyHelper.createPartiesThisPersonCanJoin(theMasterPlan, theMasterPlan.inputsPerDay, nods, person, dayPlan, partyThere, partyBack, reasonPhrase);
        }
    }

    private Party[] findPartyToJoin(Person person, PartyTuple pt, Party party, Party partyWithWaitingTime, DayOfWeekABCombo combo, boolean isWayBack, String reasonPhrase) {
        Party[] parties = { party, partyWithWaitingTime };
        if (parties[0] == null) {
            int time = person.getTimeForDowCombo(combo, isWayBack);
            // check if end time matches, etc.
            parties[0] = isWayBack ? pt.getHomeboundParty() : pt.getSchoolboundParty();
            boolean isAvailable = PartyHelper.partyIsAvailable(parties[0]) && parties[0].hasAFreeSeat();
            if (parties[0].getTime() == time && isAvailable) {
                parties[0].addPassenger(person, reasonPhrase);
                Util.out.println(String.format("  - %s can ride with %s in the %s", person, pt.getDriver(), (isWayBack ? "afternoon" : "morning")));
            } else if (parties[1] == null && Util.isTimeDifferenceAcceptable(parties[0].getTime(), time) && isAvailable) {
                parties[1] = parties[0];
                parties[0] = null;
                Util.out.println(String.format("  - %s can ride with %s in the %s (if nothing better comes up: %s minutes waiting time)",
                        person, pt.getDriver(), (isWayBack ? "afternoon" : "morning"), Util.getTimeDifference(parties[1].getTime(), time)));
                
            } else {
                parties[0] = null;
            }
        }
        return parties;
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
    	throw new IllegalStateException("adaptPreset(): Not fully implemented!");
    }

}
