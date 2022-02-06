package com.thabok.main;

import java.time.DayOfWeek;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.concurrent.CancellationException;
import java.util.stream.Collectors;

import com.thabok.entities.DayOfWeekABCombo;
import com.thabok.entities.DayPlan;
import com.thabok.entities.DayPlanInput;
import com.thabok.entities.Party;
import com.thabok.entities.PartyTouple;
import com.thabok.entities.Person;
import com.thabok.entities.Rule;
import com.thabok.entities.SwapJob;
import com.thabok.entities.TimingInfo;
import com.thabok.entities.TwoWeekPlan;
import com.thabok.util.Util;
import com.thabok.webservice.WebService;

public class Controller {

	private static final int EXPECTED_DRIVES_NUMBER = 4;
	private static final float MIN_MAX_DIFF_PENALTY_FACTOR = 		 0.5f; // 0.3f;
	private static final float AVERAGE_DRIVING_DAYS_PENALTY_FACTOR = 0.3f; // 0.3f;
	private static final float MISSED_GUIDELINE_FACTOR = 			 0.5f; // 0.5f;
	private static final Comparator<Party> SEATING_ORDER = new Comparator<Party>() {

		@Override
		public int compare(Party o1, Party o2) {
			int r = 0;
			int freeSeats1 = o1.getDriver().getNoPassengerSeats() - o1.getPassengers().size();
			int freeSeats2 = o2.getDriver().getNoPassengerSeats() - o2.getPassengers().size();
			if (freeSeats1 == freeSeats2 && freeSeats1 == 1 && o1.getDriver().getNoPassengerSeats() == 4) {
				r = -1;
			} else {
				r = Integer.compare(freeSeats1, freeSeats2);
			}
			// multiple with -1 to have the list sorted descending (by free seats), not ascending
			return r * (-1);
		}
	};
	
	private List<Person> persons;
	private Map<Person, Integer> numberOfDrives_Total;
	private Map<Person, Integer> numberOfDrives_A;
	private Map<Person, Integer> numberOfDrives_B;
    private List<Rule> rules = new ArrayList<>();
    private Map<DayOfWeekABCombo, DayPlanInput> inputsPerDay;
	private List<DayOfWeekABCombo> preset;
    public static List<DayOfWeek> weekdays = Arrays.asList(DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY, DayOfWeek.THURSDAY, DayOfWeek.FRIDAY);
    public static int referenceWeekStartDate;
    
    public Controller(List<Person> persons) {
        this.persons = persons;
        numberOfDrives_Total = new HashMap<>();
    	numberOfDrives_A = new HashMap<>();
    	numberOfDrives_B = new HashMap<>();
    	persons.forEach(p -> numberOfDrives_Total.put(p, 0));
    	persons.forEach(p -> numberOfDrives_A.put(p, 0));
    	persons.forEach(p -> numberOfDrives_B.put(p, 0));
    }
    
    public Controller(List<Person> persons, List<DayOfWeekABCombo> preset) {
    	this.persons = persons;
    	numberOfDrives_Total = new HashMap<>();
    	numberOfDrives_A = new HashMap<>();
    	numberOfDrives_B = new HashMap<>();
        persons.forEach(p -> numberOfDrives_Total.put(p, 0));
    	persons.forEach(p -> numberOfDrives_A.put(p, 0));
    	persons.forEach(p -> numberOfDrives_B.put(p, 0));
        this.preset = preset;
	}

	public TwoWeekPlan calculateGoodPlan(int iterations) throws Exception {
        String msg = "Evaluating possible driving plans";
        float bestScore = -1f;
        TwoWeekPlan bestPlan = null;
        for (int i = 0; i < iterations; i++) {
            if (WebService.isCancelled) {
                throw new CancellationException("The operation was cancelled by the user.");
            }
            TwoWeekPlan weekPlan = calculateWeekPlan();
            float fitness = getFitness(weekPlan, false);
            if (fitness > bestScore) {
                bestScore = fitness;
                bestPlan = weekPlan;
            }
            float progressValue = 0.5f + (((float) (i+1) / iterations) * 0.5f);
            WebService.updateProgress(progressValue, msg);
        }
        System.out.println("Best Score: " + bestScore);
        return bestPlan;
    }
    
    public String summarizeNumberOfDrives(TwoWeekPlan wp) {
        String summary = "";
        persons.forEach(p -> numberOfDrives_Total.put(p, 0));
        for (DayPlan dp : wp.getDayPlans().values()) {
            for (PartyTouple pt : dp.getPartyTouples()) {
                numberOfDrives_Total.put(pt.getDriver(), numberOfDrives_Total.get(pt.getDriver()) + 1);
            }
        }
        for (Person p : numberOfDrives_Total.keySet()) {
            String s = "- " + p.getName() + ": " + numberOfDrives_Total.get(p);
            System.out.println(s);
            summary += s + "\n";
        }
        wp.summary = summary;
        return summary;
    }
    
    public void printOverview(TwoWeekPlan wp) {
        for (DayPlan dayPlan : wp.getDayPlans().values()) {
            System.out.println(dayPlan.getDayOfWeekABCombo());
            Map<Integer, List<PartyTouple>> partyTouplesByFirstLesson = new HashMap<>();
            for (PartyTouple pt : dayPlan.getPartyTouples()) {
                int firstLesson = pt.getDriver().schedule.getTimingInfoPerDay().get(dayPlan.getDayOfWeekABCombo().getUniqueNumber()).getFirstLesson();
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
    	// shuffle lists to get new combinations
    	if (this.preset == null) {
//          Collections.shuffle(this.persons);
    		Collections.shuffle(Util.weekdayListAB);
    	} else {
    		Util.weekdayListAB = this.preset;
    	}
    	
        inputsPerDay = new HashMap<>();
        for (DayOfWeekABCombo dayOfWeekABCombo : Util.weekdayListAB) {
            DayPlanInput dpi = new DayPlanInput();
            dpi.personsByFirstLesson = getPersonsByFirstLesson(persons, dayOfWeekABCombo);
            dpi.personsByLastLesson = getPersonsByLastLesson(persons, dayOfWeekABCombo);
            dpi.designatedDrivers = getDesignatedDrivers(dpi, persons, dayOfWeekABCombo);
            inputsPerDay.put(dayOfWeekABCombo, dpi);
            dpi.designatedDrivers.forEach(driver -> {
                Map<Person, Integer> mapForThisWeek = getNumberOfDrivesMap(dayOfWeekABCombo.isWeekA());
                incrementNumberOfDrives(mapForThisWeek, driver);
            });
        }
    }
    
    public TwoWeekPlan calculateWeekPlan() throws Exception {
//        Date start = new Date();
    	
    	initialize();
        TwoWeekPlan wp = new TwoWeekPlan();
        wp.setWeekDayPermutation(new ArrayList<>(Util.weekdayListAB));
        for (DayOfWeekABCombo dayOfWeekABCombo : wp.getWeekDayPermutation()) {
            DayOfWeekABCombo referenceCombo = getReferenceCombo(wp.getWeekDayPermutation(), dayOfWeekABCombo);
            DayPlan referencePlan = wp.get(referenceCombo);
            wp.put(dayOfWeekABCombo, calculateDayPlan(dayOfWeekABCombo, referencePlan));
        }
        
//        Date middle = new Date();
        
        // final polishing
        balanceWeekPlan(wp);
        
//        Date end = new Date();
        
//        System.out.println();
//        System.out.println("Phase 1 (week plan): " + (middle.getTime() - start.getTime()) + " ms");
//        System.out.println("Phase 2 (balancing): " + (end.getTime() - middle.getTime()) + " ms");
//        System.out.println("Total              : " + (end.getTime() - start.getTime()) + " ms");
        
        return wp;
    }

    /**
	     * Calculates the dayPlan. Tries to stay as close as possible to the referencePlan (same day in different A/B week).
	     * @param dayOfWeekABCombo the dayOfWeekABCombo, will calculate a plan for this one 
	     * @param referencePlan referencePlan for same day in different A/B week. May be null!
	     * @return the calculated dayPlan.
	     * @throws Exception
	     */
	    public DayPlan calculateDayPlan(DayOfWeekABCombo dayOfWeekABCombo, DayPlan referencePlan) throws Exception {
	        DayPlan dayPlan = new DayPlan();
	        DayPlanInput dpi = inputsPerDay.get(dayOfWeekABCombo);
	        dayPlan.setDayOfWeekABCombo(dayOfWeekABCombo);
	        
	        List<Person> personsForThisDay = persons.stream().filter(p -> Util.isPersonActiveOnThisDay(p, dayOfWeekABCombo)).collect(Collectors.toList());
	        
	        /*
	         * PART 1: Designated Drivers + Mirror days
	         */
	        Set<Person> coveredPersons = initialSoloPartyTouples(dayOfWeekABCombo, referencePlan, dayPlan, dpi, personsForThisDay);
	        
	        // TODO: only add solo parties for other persons if nobody else has a mirror-day-match
	        
	        /*
	         * PART 2: There & back matches
	         * - for each first & last lesson combo: find the set of people that match and are not designated drivers
	         * - if set is not empty: create parties 
	         */
	        
	        // This threshold defines how many drives a driver may already have to be considered. This will be increased in the while-loop if needed
	        int driverConsiderationThreshold = getInitialDriverConsiderationThreshold(dayOfWeekABCombo.isWeekA());
	        // Do this until all persons have been covered
	        while (coveredPersons.size() < personsForThisDay.size()) {
	    		for (Person remainingPerson : personsForThisDay) {
	        		findPartyForPerson(remainingPerson, dayPlan, coveredPersons, driverConsiderationThreshold, dpi);
	        	}
	            // increases the driver consideration threshold to make sure we cover everyone eventually
	            driverConsiderationThreshold++;
	        }
	        // Performs balancing to prevent one car
	        // from filling up and the first person that doesn't
	        // fit anymore drives alone while the other car is full
	        balanceEquivalentParties(dayPlan, referencePlan, null);
	        return dayPlan;
	    }

	/**
     * Massages the week plan to minimize the gap between
     * persons who drive often and those who drive rarely.
     * 
     * @param wp the otherwise finished week plan candidate
     * @throws Exception 
     */
    private void balanceWeekPlan(TwoWeekPlan wp) throws Exception {
        Integer minDrivingDays = null;
        Integer maxDrivingDays = null;
        for (Person person : persons) {
            Integer drivingDays = numberOfDrives_Total.get(person);
            drivingDays = drivingDays == null ? 0 : drivingDays;
            if (minDrivingDays == null || minDrivingDays > drivingDays) {
                minDrivingDays = drivingDays;
            }
            if (maxDrivingDays == null || maxDrivingDays < drivingDays) {
                maxDrivingDays = drivingDays;
            }
        }
		if (maxDrivingDays - minDrivingDays > 1) {// difference to big: balance!
			
			// 0. Since 2 is not implemented, skip those cases:
			if (minDrivingDays % 2 == 0 /* even value -> there may be some without mirror days */) {
				return;
			}
			
			// 1. identify persons with available mirror days (e.g. they drive on Mon-A but not on Mon-B)
			createSoloPartiesForMirrorDays(wp, minDrivingDays);
			
			// 2. process left-over persons by using days with lowest number of partyTouples
			if (minDrivingDays % 2 == 0 /* even value -> there may be some without mirror days */) {
//				createSoloPartiesForLeftOvers(wp, drivingDaysPerPerson, minDrivingDays);
				System.err.println("Attention!");
				System.err.println("Not implemented!");
				System.err.println("Balance Week Plan when minNumberDrivingDays is even!");
			}
			
			// 3. rebalance parties accross all dayPlans while considering the preferredPartyPeople approach
			balancePartiesOnWeekPlan(wp, maxDrivingDays);
		}
	}

	private void balancePartiesOnWeekPlan(TwoWeekPlan wp, Integer maxDrivingDays) throws Exception {
		Set<Person> frequentDrivers = numberOfDrives_Total.entrySet().stream()
				.filter(e -> e.getValue() == maxDrivingDays)
				.map(e -> e.getKey()).collect(Collectors.toSet());
		for (DayPlan dayPlan : wp.getDayPlans().values()) {
			DayOfWeekABCombo referenceCombo = getReferenceCombo(wp.getWeekDayPermutation(), dayPlan.getDayOfWeekABCombo());
            DayPlan referencePlan = wp.get(referenceCombo);
			balanceEquivalentParties(dayPlan, referencePlan, frequentDrivers);
		}
		
	}

	private void createSoloPartiesForMirrorDays(TwoWeekPlan wp, Integer minDrivingDays) throws Exception {
		for (Person person : persons) {
            Integer drivingDays = numberOfDrives_Total.get(person);
            drivingDays = drivingDays == null ? 0 : drivingDays;
            if (drivingDays == minDrivingDays) {
            	// list of days where person drives in the other week
            	List<DayOfWeekABCombo> mirrorDays = Util.findMirrorDay(wp, person);
            	// attempt can fail if person has an empty schedule on that day
            	boolean mirrorDayPartyCreated = attemptToCreateMirrorDaySoloParty(wp, person, mirrorDays);
            	if (!mirrorDayPartyCreated) {
            		attemptToCreateMirrorDaySoloParty(wp, person, wp.getWeekDayPermutation());
            	}
            }
		}
		
	}

	private boolean attemptToCreateMirrorDaySoloParty(TwoWeekPlan wp, Person person, List<DayOfWeekABCombo> combos)
			throws Exception {
		boolean partyCreated = false;
		for (DayOfWeekABCombo combo : combos) {
			DayPlan dayPlan = wp.get(combo);
			if (person.schedule.getTimingInfoPerDay().get(combo.getUniqueNumber()) != null) {
				// timing info could be null if person has no lessons on that day
				// remove person from current parties
				for (PartyTouple pt : dayPlan.getPartyTouples()) {
					if (pt.getPartyThere().getPassengers().contains(person)) {
						pt.getPartyThere().getPassengers().remove(person);
					}
					if (pt.getPartyBack().getPassengers().contains(person)) {
						pt.getPartyBack().getPassengers().remove(person);
					}
				}
				// create solo party
				addSoloParty(dayPlan, person, false);
				partyCreated = true;
				break;
			}
		}
		return partyCreated;
	}

	/**
     * Returns the other dayOfTheWeekCombo with the same day but different A/B
     * 
     * @param combos
     * @param dayOfWeekABCombo
     * @return the other dayOfTheWeekCombo with the same day but different A/B
     * @throws Exception 
     */
    private DayOfWeekABCombo getReferenceCombo(List<DayOfWeekABCombo> combos, DayOfWeekABCombo dayOfWeekABCombo) throws Exception {
        for (DayOfWeekABCombo combo : combos) {
            if (combo.getDayOfWeek().equals(dayOfWeekABCombo.getDayOfWeek()) && (combo.isWeekA() != dayOfWeekABCombo.isWeekA()) ) {
                // same week day, different A/B part
                return combo;
            }
        }
        throw new Exception("Could not find matching reference combo for " + dayOfWeekABCombo);
    }

    /**
     * Calculates the fitness of a dayPlan. The result is a value between 0 and 1 (1 being the unrealistic ideal).
     * Checks the following criteria:
     *     - average no driving days per person (the lower the better)
     *  - difference between min & max no driving days (the lower the better)
     *     - missed global rules (have all mandatory rules been fulfilled? if not -> total fitness = 0)
     *  - missed global guidelines (have all guidelines been fulfilled? if not reduced fitness; 2/5 guidelines missed -> 40% guideline penalty)
     * @param weekPlan
     * @return fitness
     */
    public float getFitness(TwoWeekPlan weekPlan, boolean print) {
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
        float avgDayPlanFitness = totalDayPlanFitness / (float) 10;
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
        float minMaxDiffPenalty = (maxDrivingDays - minDrivingDays) * MIN_MAX_DIFF_PENALTY_FACTOR;
        fitness -= MIN_MAX_DIFF_PENALTY_FACTOR * fitness * minMaxDiffPenalty;
        // fitness penalty based on avg driving days
        float avgDrivingDaysPenalty = avgDrivingDaysPerPerson / (float) 10; // 0 < value <= 1; the lower the better
        fitness -= AVERAGE_DRIVING_DAYS_PENALTY_FACTOR * fitness * avgDrivingDaysPenalty;
        
        if (print) {
            System.out.println("Avg. Driving Days p.P.: " + avgDrivingDaysPerPerson);
            System.out.println("Min. Driving Days: " + minDrivingDays);
            System.out.println("Max. Driving Days: " + maxDrivingDays);
        }
        return fitness;
    }
    
    private boolean matches(TwoWeekPlan weekPlan, Rule rule) {
        return true;
    }

    /**
     * Calculates the fitness of a dayPlan. The result is a value between 0 and 1 (1 being the unrealistic ideal).
     * Checks the following criteria:
     *     - missed rules: have all mandatory rules been fulfilled? if not -> total fitness = 0
     *     - partiesPersonRatio (50% impact on fitness)
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
            fitness -= MISSED_GUIDELINE_FACTOR * missedGuidelinesRatio;
        }
        return fitness;
    }
    
    private boolean matches(DayPlan dayPlan, Rule guideline) {
        return true;
    }

    private Set<Person> initialSoloPartyTouples(DayOfWeekABCombo dayOfWeekABCombo, DayPlan referencePlan,
			DayPlan dayPlan, DayPlanInput dpi, List<Person> personsForThisDay) throws Exception {
		Set<Person> coveredPersons;
		if (referencePlan == null) {
        	addPartiesForDesignatedDrivers(dayPlan, dpi.designatedDrivers);
        	coveredPersons = new HashSet<>(dpi.designatedDrivers);
        } else {
        	coveredPersons = new HashSet<>();
        	for (Person p : personsForThisDay) {
        		PartyTouple mirrorDayPartyTouple = Util.getMirrorDayPartyTouple(p, referencePlan);
//        		boolean belowThreshold = numberOfDrives_Total.get(p) < EXPECTED_DRIVES_NUMBER;
        		boolean belowWeekThreshold = getNumberOfDrives(p, dayOfWeekABCombo.isWeekA()) < (EXPECTED_DRIVES_NUMBER / 2); 
        		boolean belowTotalThreshold = numberOfDrives_Total.get(p) < EXPECTED_DRIVES_NUMBER;
        		boolean drivesOnRefDay = mirrorDayPartyTouple != null;
        		boolean designatedDriver = dpi.designatedDrivers.contains(p);
        		if (designatedDriver) {
        			addSoloParty(dayPlan, p, true);
        			coveredPersons.add(p);
        		} else if (drivesOnRefDay && belowWeekThreshold && belowTotalThreshold) {        			
        			addSoloParty(dayPlan, p, false);
        			Integer number = getNumberOfDrives(p, dayOfWeekABCombo.isWeekA());
        			getNumberOfDrivesMap(dayOfWeekABCombo.isWeekA()).put(p, number + 1);
        			coveredPersons.add(p);
        		}/* else {
        			if (drivesOnRefDay) {
        				System.out.println(p.firstName + " not picked because belowWeekThreshold: " + belowWeekThreshold + ", belowTotalThreshold: " + belowTotalThreshold);
        			}
        		}*/
        	}
        }
		return coveredPersons;
	}

    private void findPartyForPerson(Person person, DayPlan dayPlan, Set<Person> coveredPersons, int driverConsiderationThreshold, DayPlanInput dpi) throws Exception {
    	if (coveredPersons.contains(person)) {
    		return;
    	}
    	DayOfWeekABCombo dayOfWeekABCombo = dayPlan.getDayOfWeekABCombo();
        List<PartyTouple> candidatesThere = new ArrayList<>();
        List<PartyTouple> candidatesBack = new ArrayList<>();
        for (PartyTouple pt : dayPlan.getPartyTouples()) {
            boolean timeThereMatches = person.getLesson(dayOfWeekABCombo, false) == pt.getPartyThere().getLesson();
            boolean partyThereIsAvailable = Util.partyIsAvailable(pt.getPartyThere());
            if (timeThereMatches && partyThereIsAvailable) {
                // remaining person could join this party (->)
                candidatesThere.add(pt);
            }
            boolean timeBackMatches = person.getLesson(dayOfWeekABCombo, true) == pt.getPartyBack().getLesson();
            boolean partyBackIsAvailable = Util.partyIsAvailable(pt.getPartyBack());
            if (timeBackMatches && partyBackIsAvailable) {
                // remaining person could join this party (<-)
                candidatesBack.add(pt);
            }
        }
        PartyTouple ptThere = getPreferredPartyTouple(person, candidatesThere, false,
                dpi.designatedDrivers);
        PartyTouple ptBack = getPreferredPartyTouple(person, candidatesBack, true,
                dpi.designatedDrivers);
        if (ptThere == null || ptBack == null) {
            if (alreadyDrivesTooMuch(person, driverConsiderationThreshold, dayOfWeekABCombo)) {
                // this driver already has more drives than the threshold
                // look for another driver or reconsider when the threshold has been increased (while-loop)
                return;
            }
            // no party available for one of the ways, create own party for others to join
            addSoloParty(dayPlan, person, false);
        } else {
            ptThere.getPartyThere().addPassenger(person);
            ptBack.getPartyBack().addPassenger(person);
        }
        coveredPersons.add(person);
		
	}

	private boolean alreadyDrivesTooMuch(Person person, int driverConsiderationThreshold,
			DayOfWeekABCombo dayOfWeekABCombo) {
		boolean weekThresholdMet = getNumberOfDrives(person, dayOfWeekABCombo.isWeekA()) > (driverConsiderationThreshold / 2);
		boolean totalThresholdMet = numberOfDrives_Total.get(person) >= driverConsiderationThreshold;
		return weekThresholdMet || totalThresholdMet;
	}

    private Map<Person, Integer> getNumberOfDrivesMap(boolean weekA) {
    	if (weekA) {
			return numberOfDrives_A;
		} else {
			return numberOfDrives_B;
		}
    }
    
	private int getNumberOfDrives(Person person, boolean weekA) {
		return getNumberOfDrivesMap(weekA).get(person);
	}


	/**
     * Finds equivalent parties (i.e., parties that drive at the same time) 
     * and balances the passenger load to prevent "the party-bus and the loner"
     * 
     * @param dayPlan the dayPlan with potentially unbalanced parties  
     * @param referencePlan reference plan, may be null
     * @param frequentDrivers set of frequentDrivers, may be null if not yet known
     */
    private void balanceEquivalentParties(DayPlan dayPlan, DayPlan referencePlan, Set<Person> frequentDrivers) {
        // Collect equivalent parties
        Map<Integer, List<Party>> wayTherePartiesByStartLesson = new HashMap<>();
        Map<Integer, List<Party>> wayBackPartiesByEndLesson = new HashMap<>();
        Set<PartyTouple> removalCandidates = new HashSet<>();
        for (PartyTouple touple : dayPlan.getPartyTouples()) {
        	
        	
            Party pt = touple.getPartyThere();
            if (Util.partyIsAvailable(pt)) {
				List<Party> partiesThereForCurrentLesson = wayTherePartiesByStartLesson.get(pt.getLesson());
				if (partiesThereForCurrentLesson == null) {
					partiesThereForCurrentLesson = new ArrayList<>();
					wayTherePartiesByStartLesson.put(pt.getLesson(), partiesThereForCurrentLesson);
				}
				partiesThereForCurrentLesson.add(pt);
			}
            Party pb = touple.getPartyBack();
            if (Util.partyIsAvailable(pb)) {
            	List<Party> partiesBackForCurrentLesson = wayBackPartiesByEndLesson.get(pb.getLesson());
            	if (partiesBackForCurrentLesson == null) {
            		partiesBackForCurrentLesson = new ArrayList<>();
            		wayBackPartiesByEndLesson.put(pb.getLesson(), partiesBackForCurrentLesson);
            	}
            	partiesBackForCurrentLesson.add(pb);            	
            }
            
            // help the overloaded workers!
            if (frequentDrivers != null && frequentDrivers.contains(touple.getDriver()) && !touple.isDesignatedDriver()) {
            	// schedule potential removal
            	removalCandidates.add(touple);
            }
        }
        // process potential removals
        // FIXME: if a party touple is dissolved, the driver sometimes gets lost :(
        processRemovalCandidates(dayPlan, wayTherePartiesByStartLesson, wayBackPartiesByEndLesson, removalCandidates);
        
        
        // Balance equivalent parties
        balanceEquivalentParties(wayTherePartiesByStartLesson, referencePlan);
        balanceEquivalentParties(wayBackPartiesByEndLesson, referencePlan);
    }

    /**
     * Checks the identified candidates (drivers with max number of drives
     * who are not designated drivers in the given partyTouple) and dissolves
     * the partyTouple if possible (i.e., if others can take the persons)
     * 
     * @param dayPlan
     * @param wayTherePartiesByStartLesson
     * @param wayBackPartiesByEndLesson
     * @param removalCandidates
     */
	private void processRemovalCandidates(DayPlan dayPlan, Map<Integer, List<Party>> wayTherePartiesByStartLesson,
			Map<Integer, List<Party>> wayBackPartiesByEndLesson, Set<PartyTouple> removalCandidates) {
		for (PartyTouple removalCandidate : removalCandidates) {
        	// way there
        	List<Party> otherPartiesThere = wayTherePartiesByStartLesson.get(removalCandidate.getPartyThere().getLesson())
        			.stream().filter(p -> !p.getDriver().equals(removalCandidate.getDriver()))
        			.collect(Collectors.toList()); // makes sure current drivers party is not considered an alternative -> recursion!
        	int totalFreeSeatsWayThere = 0;
        	for (Party otherParty : otherPartiesThere) {
        		int freeSeats = otherParty.getDriver().getNoPassengerSeats() - otherParty.getPassengers().size();
        		totalFreeSeatsWayThere += freeSeats;
        	}
        	
        	// way back
        	List<Party> otherPartiesBack = wayBackPartiesByEndLesson.get(removalCandidate.getPartyBack().getLesson())
        			.stream().filter(
        					p -> 	!p.getDriver().equals(removalCandidate.getDriver()) &&
        							Util.partyIsAvailable(p))
        			.collect(Collectors.toList());  // makes sure current drivers party is not considered an alternative -> recursion!
        	int totalFreeSeatsWayBack = 0;
        	for (Party otherParty : otherPartiesBack) {
        		int freeSeats = otherParty.getDriver().getNoPassengerSeats() - otherParty.getPassengers().size();
        		totalFreeSeatsWayBack += freeSeats;
        	}
        	// check if others can take over (driver + passengers)
        	int personsWayThere = removalCandidate.getPartyThere().getPassengers().size() + 1;
        	int personsWayBack = removalCandidate.getPartyBack().getPassengers().size() + 1;
        	
        	if (personsWayThere < totalFreeSeatsWayThere && personsWayBack < totalFreeSeatsWayBack) {
        		// there's enough room to accommodate everyone! 
        		dayPlan.getPartyTouples().remove(removalCandidate);
        		// move people for wayThere
        		boolean movingComplete_There = false;
        		for (Party otherParty : otherPartiesThere) {
        			if (movingComplete_There) {
        				break;
        			}
            		while (otherParty.getDriver().getNoPassengerSeats() > otherParty.getPassengers().size()) {
            			if (!removalCandidate.getPartyThere().getPassengers().isEmpty()) {
            				otherParty.addPassenger(removalCandidate.getPartyThere().popPassenger());
            			} else {
            				otherParty.addPassenger(removalCandidate.getDriver());
            				movingComplete_There = true;
            				break;
            			}
            		}
            	}
        		// move people for wayBack
        		boolean movingComplete_Back = false;
        		for (Party otherParty : otherPartiesBack) {
        			if (movingComplete_Back) {
        				break;
        			}
        			while (otherParty.getDriver().getNoPassengerSeats() > otherParty.getPassengers().size()) {
            			if (!removalCandidate.getPartyBack().getPassengers().isEmpty()) {
            				otherParty.addPassenger(removalCandidate.getPartyBack().popPassenger());
            			} else {
            				otherParty.addPassenger(removalCandidate.getDriver());
            				movingComplete_Back = true;
            				break;
            			}
            		}
            	}
        	}/* else {
        		// there's not enough room to dissolve this party :(
        		System.err.println("Sadly, " + removalCandidate.getDriver().firstName + "'s party cannot be removed. There's not enough capacity in the alternative parties.");
        	}*/
        	
        }
	}

    /**
     * Finds equivalent parties and tries to balance them by moving passengers
     * from the biggest party (with the highest number of passengers) to the
     * smallest party (with the lowerst number of passengers). This is done
     * repeatedly until the difference is sufficiently small or no further
     * balancing is possible.<br><br>
     * 
     * TODO: Big persons/small cars: This still needs to be implemented (incl. frontend)
     * >> Additionally, this method attempts to swap big persons with small persons
     * >> in case big persons end up in a small car.
     * 
     * TODO: Swap passengers to try to have the same driver for a person's wayThere/wayBack + weekA/weekB
     * 
     * @param partiesByLesson parties mapped by the respective lesson (start lesson for wayThere and end lesson for wayBack)
     * @param referencePlan reference plan, may be null
     */
    private void balanceEquivalentParties(Map<Integer, List<Party>> partiesByLesson, DayPlan referencePlan) {
        for (List<Party> equivalentParties : partiesByLesson.values()) {
            if (equivalentParties.size() > 1) {
                // normal balancing based on number of passengers & free seats 
                balanceListOfPartiesBasedOnNumbers(equivalentParties);
                
                // balance according to referencePlan
                matchAandBWeek(equivalentParties, referencePlan);
            }
        }
    }

    private void matchAandBWeek(List<Party> equivalentParties, DayPlan referencePlan) {
        if (referencePlan != null) {
        	Set<Person> virtualBufferCar = new HashSet<>();
//        	System.out.println("Parsing " + equivalentParties.size() + " parties to bring people together, similar to the mirror day " + referencePlan.getDayOfWeekABCombo());
        	for (Party party : equivalentParties) {
        		PartyTouple pt = Util.getMirrorDayPartyTouple(party.getDriver(), referencePlan);
        		if (pt == null) {
        			continue;
        		}
        		Party mirrorParty = party.isWayBack() ? pt.getPartyBack() : pt.getPartyThere();
        		if (!mirrorParty.getPassengers().isEmpty()) {
					removeUnwantedPassengers(virtualBufferCar, party, mirrorParty);
					findDesiredPassengersInEquivalentParties(equivalentParties, party, mirrorParty, virtualBufferCar);
				}
        	}
//        	System.out.println("Bringing people together in a similar way to the mirror day left " + virtualBufferCar.size() + " people homeless!");
        	
        	while (!virtualBufferCar.isEmpty()) {
        		Collections.sort(equivalentParties, SEATING_ORDER);
        		Party partyWithFreeSeats = equivalentParties.get(0);
        		Person nextRandomPerson = virtualBufferCar.iterator().next();
        		virtualBufferCar.remove(nextRandomPerson);
        		partyWithFreeSeats.addPassenger(nextRandomPerson);
        	}
        }
    }

	private void findDesiredPassengersInEquivalentParties(List<Party> equivalentParties, Party party,
			Party mirrorParty, Set<Person> virtualBufferCar) {
		// find passengers from mirror party
		for (Person mirrorPartyPassenger : mirrorParty.getPassengers()) {
			if (virtualBufferCar.contains(mirrorPartyPassenger)) {
				virtualBufferCar.remove(mirrorPartyPassenger);
				party.addPassenger(mirrorPartyPassenger);
			} else {
				Optional<Party> findFirst = equivalentParties.stream().filter(p -> p.getPassengers().contains(mirrorPartyPassenger)).findFirst();
				if (findFirst.isPresent() && !findFirst.get().equals(party)) {
					// remove the mirror passenger from the mirror party and add him to today's party
					findFirst.get().removePassenger(mirrorPartyPassenger);
					party.addPassenger(mirrorPartyPassenger);
				}				
			}
		}
	}

	private void removeUnwantedPassengers(Set<Person> virtualBufferCar, Party party, Party mirrorParty) {
		Set<Person> scheduledForRemovalFromParty = new HashSet<>();
		for (Person passenger : party.getPassengers()) {
			// remove any passengers that are not part of the mirror party
			if (!mirrorParty.getPassengers().contains(passenger)) {
				// he shouldn't be here
				scheduledForRemovalFromParty.add(passenger);
				// place him into the virtual buffer car for now
				virtualBufferCar.add(passenger);
			}
		}
		scheduledForRemovalFromParty.forEach(unwantedPerson -> party.removePassenger(unwantedPerson));
	}
    
    /**
     * 
     * @param equivalentParties list of equivalent parties, size must be > 1
     * @param referencePlan reference plan, may be null
     */
    private void reorganizePartiesAccordingToReferencePlan(List<Party> equivalentParties, DayPlan referencePlan) {
        if (referencePlan != null) {
            boolean isWayBack = equivalentParties.iterator().next().isWayBack(); // safe because size > 1
            List<SwapJob> swapJobs = new ArrayList<>();
            Set<Person> personsScheduledForSwap = new HashSet<>();
            for (Party party : equivalentParties) {
                for (Person passenger : party.getPassengers()) {
                	if (personsScheduledForSwap.contains(passenger)) {
                		// skip this one, already scheduled for a swap!
                		continue;
                	}
                    Set<Person> preferredPartyPeople = getPreferredPartyPeopleForPerson(referencePlan, isWayBack, party, passenger);
                    if (!partyMeetsPppCriteria(party, preferredPartyPeople)) {
                        // this person is sad because it's not driving with anyone from the referencePlan (other week, same day)
                        Party preferredParty = getBestPartyPeopleParty(equivalentParties, preferredPartyPeople);
                        if (preferredParty != null) {
                            Person swappee = getSwapCandidateFromPreferredParty(preferredParty, referencePlan, personsScheduledForSwap);
                            if (swappee != null) {
                            	System.out.println();
                            	System.out.println("Swap plan:");
                            	System.out.println("Source party: " + party);
                            	System.out.println("Swap party: " + preferredParty);
                            	System.out.println(passenger.firstName + " prefers the other party: " + preferredParty);
                            	System.out.println("Planning to swap " + passenger.firstName + " with " + swappee.firstName);
                            	System.out.println();
                                // we have a swappee, let's go swap!
                                swapJobs.add(new SwapJob(party, preferredParty, passenger, swappee));
                                personsScheduledForSwap.add(passenger);
                                personsScheduledForSwap.add(swappee);
                            }
                        }
                    }
                }
            }
            // now we have collected a number of SwapJobs, let's go swap!
            swapJobs.forEach(swapJob -> swapJob.swappediswap());
        }
        
    }

    private Person getSwapCandidateFromPreferredParty(Party preferredParty, DayPlan referencePlan, Set<Person> personsScheduledForSwap) {
        for (Person potentialSwappee : preferredParty.getPassengers()) {
        	if (personsScheduledForSwap.contains(potentialSwappee)) {
        		// don't consider this person, already taken
        		continue;
        	}
            Set<Person> preferredPartyPeople = getPreferredPartyPeopleForPerson(referencePlan, preferredParty.isWayBack(), preferredParty, potentialSwappee);
            if (preferredPartyPeople.contains(preferredParty.getDriver())) {
                continue;
            }
            boolean hasFriendInCar = false;
            for (Person friend : preferredPartyPeople) {
                if (preferredParty.getPassengers().contains(friend)) {
                    hasFriendInCar = true;
                    break;
                }
            }
            if (!hasFriendInCar) {
                // this person has no friends in the car -> can be the swappee
                return potentialSwappee;
            }
        }
        return null;
    }

    /**
     * Returns the party with the highest number of preferredPartyPeople (PPP)
     * 
     * @param equivalentParties candidates
     * @param preferredPartyPeople the persons who rock the most!
     * @return the best party or null, if none of the candidate-parties contains any of the PPP
     */
    private Party getBestPartyPeopleParty(List<Party> equivalentParties, Set<Person> preferredPartyPeople) {
        int bestPartyValue = 0;
        Party bestParty = null;
        for (Party party : equivalentParties) {
            int partyValue = 0;
            if (preferredPartyPeople.contains(party.getDriver())) {
                partyValue++;
            }
            for (Person passenger : party.getPassengers()) {
                if (preferredPartyPeople.contains(passenger)) {
                    partyValue++;
                }
            }
            // evaluate if bestParty is still valid
            if (partyValue > bestPartyValue) {
                bestParty = party;
            }
        }
        return bestParty;
    }

    private Set<Person> getPreferredPartyPeopleForPerson(DayPlan referencePlan, boolean isWayBack, Party party,
            Person passenger) {
        Set<Person> preferredPartyPeople = new HashSet<>();
        for (PartyTouple referencePartyTouple : referencePlan.getPartyTouples()) {
            Party p;
            boolean matchingDriver;
            boolean matchingPassenger;
            if (isWayBack) {
                p = referencePartyTouple.getPartyBack();
                matchingDriver = p.getDriver().equals(passenger);
                matchingPassenger = p.getPassengers().contains(passenger);
            } else {
                p = referencePartyTouple.getPartyThere();
                matchingDriver = p.getDriver().equals(passenger);
                matchingPassenger = p.getPassengers().contains(passenger);
            }
            // if the plfp is listed in the reference party, add every member to the set.
            if (matchingDriver || matchingPassenger) {
                preferredPartyPeople.add(p.getDriver());
                preferredPartyPeople.addAll(p.getPassengers());
                // the person itself should not be included (even if it would probably not matter)
                preferredPartyPeople.remove(passenger);
                break; // no need to search any further
            }
        }
        return preferredPartyPeople;
    }
    
    /**
     * Returns true if the given party contains someone from the PPP set.
     * @param party the party to check
     * @param preferredPartyPeople the PPP
     * @return true if the given party contains someone from the PPP set.
     */
    private boolean partyMeetsPppCriteria(Party party, Set<Person> preferredPartyPeople) {
        for (Person ppPerson : preferredPartyPeople) {
            if (ppPerson.equals(party.getDriver()) || party.getPassengers().contains(ppPerson)) {
                return true;
            }
        }
        return false;
    }

    private void balanceListOfPartiesBasedOnNumbers(List<Party> equivalentPartiesThere) {
        boolean rebalancingHasHappened = false;
        do {
            Party smallestParty = equivalentPartiesThere.get(0);
            Party biggestParty = equivalentPartiesThere.get(0);;
            for (Party party : equivalentPartiesThere) {
                if (smallestParty.getPassengers().size() > party.getPassengers().size()) {
                    smallestParty = party;
                }
                if (biggestParty.getPassengers().size() < party.getPassengers().size()) {
                    biggestParty = party;
                }
            }
            // check if it makes sense to move anyone:
            // from car with most passengers (if 2 or more)
            boolean sufficientlyDifferent = biggestParty.getPassengers().size() - smallestParty.getPassengers().size() > 1;
            // add person to car with 1 free spot and 2 total seats (e.g., Smart) or with at least 2 free spots 
            int freeSpotsInSmallParty = smallestParty.getDriver().getNoPassengerSeats() - smallestParty.getPassengers().size();
            boolean noFiveSeater = smallestParty.getDriver().getNoPassengerSeats() != 5;
            boolean enoughRoomInSmallParty = freeSpotsInSmallParty > 1 || noFiveSeater; 
            if (sufficientlyDifferent && enoughRoomInSmallParty) {
                // move person from biggest to smallest party
                smallestParty.addPassenger(biggestParty.popPassenger());
                rebalancingHasHappened = true;     // rebalancing took place
            } else {
                rebalancingHasHappened = false;     // no rebalancing needed anymore
            }
        } while (rebalancingHasHappened); // keep repeating until no rebalancing is needed anymore
    }

    /**
     * Evaluates number of drives to prefer drivers with a low number of drives for starting a party.
     * 
     * @return the minimum number of drives a person currently has
     */
    private int getInitialDriverConsiderationThreshold(boolean weekA) {
        int min = 100;
        for (int noDrives : getNumberOfDrivesMap(weekA).values()) {
            min = Math.min(noDrives, min);
        }
        return min;
    }

    /**
     * Returns the best PartyTouple for the given personLookingForParty based on its candidates.<br>
     * The candidates are evaluated based on available seats or a preference score (on equal number of free seats).
     * 
     * @param personLookingForParty the person that is looking for a party
     * @param candidates the possible party touples for this person
     * @param isWayBack true, if we're talking about the way back
     * @param designatedDrivers the set of persons who have to drive anyway
     * @return the best party touple for the given person
     */
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
            boolean moreFreeSeats = bestCandidatesFreeSeats < currentNoFreeSeats;
            boolean equalNoSeats = bestCandidatesFreeSeats == currentNoFreeSeats;
            boolean betterScore = getPreferenceScore(bestParty, designatedDrivers) < getPreferenceScore(party, designatedDrivers);
            if (moreFreeSeats || (equalNoSeats && betterScore)) {
                bestCandidate = candidate;
                bestParty = party;
                bestCandidatesFreeSeats = currentNoFreeSeats;
            }
        }
        return bestCandidate;
    }

    /**
     * Returns a preference score between -10 and 1, starting with a base score of 0. It shows how feasible the party is.
     * 
     * @param party the party the party to evaluate
     * @param designatedDrivers the set of persons that have to drive anyway
     * @return the score (high = good)
     */
    private int getPreferenceScore(Party party, Set<Person> designatedDrivers) {
        if (party == null) {
            return -1;
        }
        int score = 0;
        if (designatedDrivers.contains(party.getDriver())) score++;
        if (!(party.getDriver().getNoPassengerSeats() > party.getPassengers().size())) score = -10;
        return score;
    }

    /**
     * Creates a solo party for each designatedDriver (isDesignatedDriver=true) and adds them to the dayPlan.
     * 
     * @param dayPlan the solo parties are added to this dayPlan
     * @param designatedDrivers set of designatedDrivers (must drive, no alternative)
     */
    private void addPartiesForDesignatedDrivers(DayPlan dayPlan, Set<Person> designatedDrivers) throws Exception {
        for (Person driver : designatedDrivers ) {
            addSoloParty(dayPlan, driver, true);
        }
    }
    
    /**
     * Creates a solo party for the given driver and adds it to the dayPlan
     * @param dayPlan the created solo party is added to this dayPlan
     * @param driver the driver
     * @param isDesignatedDriver true, if designatedDriver (must drive, no alternative)
     * @return 
     */
    private PartyTouple addSoloParty(DayPlan dayPlan, Person driver, boolean isDesignatedDriver) throws Exception {
        PartyTouple partyTouple = new PartyTouple();
        
        Party partyThere = new Party();
        partyThere.setDayOfTheWeekABCombo(dayPlan.getDayOfWeekABCombo());
        partyThere.setDriver(driver);
        partyThere.setWayBack(false);
        int firstLesson = driver.schedule.getTimingInfoPerDay().get(dayPlan.getDayOfWeekABCombo().getUniqueNumber()).getFirstLesson();
        partyThere.setLesson(firstLesson);
        partyThere.setTime(driver.schedule.getTimingInfoPerDay().get(dayPlan.getDayOfWeekABCombo().getUniqueNumber()).getStartTime());
        partyTouple.setPartyThere(partyThere);
        
        Party partyBack = new Party();
        partyBack.setDayOfTheWeekABCombo(dayPlan.getDayOfWeekABCombo());
        partyBack.setDriver(driver);
        partyBack.setWayBack(true);
        int lastLesson = driver.getLesson(dayPlan.getDayOfWeekABCombo(), true);
        partyBack.setLesson(lastLesson);
        partyBack.setTime(driver.schedule.getTimingInfoPerDay().get(dayPlan.getDayOfWeekABCombo().getUniqueNumber()).getEndTime());
        partyTouple.setPartyBack(partyBack);
        partyTouple.setDesignatedDriver(isDesignatedDriver);        
        dayPlan.addPartyTouple(partyTouple);
        
        if (!isDesignatedDriver) {
			// increment number of drives (not needed for designated drivers)
			incrementNumberOfDrives(getNumberOfDrivesMap(dayPlan.getDayOfWeekABCombo().isWeekA()), driver);
		}
		return partyTouple;
    }

    /**
     * Returns a map of persons grouped by their first lesson.
     * 
     * @param dayOfWeek the day of the week needed to query the persons' schedules
     * @return a map of persons grouped by their first lesson
     */
    private Map<Integer, List<Person>> getPersonsByFirstLesson(List<Person> persons, DayOfWeekABCombo dayOfWeekABCombo) {
        Map<Integer, List<Person>> personsByFirstLesson = new HashMap<>(); 
        // place persons into groups based on first-lesson
        for (Person person : persons) {
            TimingInfo timingInfo = person.schedule.getTimingInfoPerDay().get(dayOfWeekABCombo.getUniqueNumber());
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
    private Map<Integer, List<Person>> getPersonsByLastLesson(List<Person> persons, DayOfWeekABCombo dayOfWeekABCombo) {
        Map<Integer, List<Person>> personsByLastLesson = new HashMap<>(); 
        // place persons into groups based on first-lesson
        for (Person person : persons) {
            TimingInfo timingInfo = person.schedule.getTimingInfoPerDay().get(dayOfWeekABCombo.getUniqueNumber());
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
     * or have custom preferences that say so.
     * 
     * @param personsByFirstLesson map with persons by first lesson slot
     * @param personsByLastLesson map with persons by last lesson slot
     * @param allPersonsForThisDay list of all persons for this day to extract custom preferences 
     * @param dayOfTheWeekABCombo to know which day it is
     * @return a set of persons that need to drive anyway because they are the only one in a time slot
     */
    private Set<Person> getDesignatedDrivers(DayPlanInput dpi, List<Person> allPersonsForThisDay, DayOfWeekABCombo dayOfTheWeekABCombo) {
        Set<Person> designatedDrivers = new HashSet<>();

        // 1. add persons who are alone to their first lesson
        for (List<Person> persons : dpi.personsByFirstLesson.values()) {
            if (persons.size() == 1) {
                designatedDrivers.add(persons.iterator().next());
            }
        }
        
        // 2. add persons who are alone from their last lesson
        for (List<Person> persons : dpi.personsByLastLesson.values()) {
            if (persons.size() == 1) {
                designatedDrivers.add(persons.iterator().next());
            }
        }
        
        // 3. Add persons based on custom preferences
        // pay attention: key is 0 based while uniqueNumber is 1 based
        int customDaysIndex = Util.dowComboToCustomDaysIndex(dayOfTheWeekABCombo);
        for (Person person : allPersonsForThisDay) {
            if (person.customDays.get(customDaysIndex).needsCar) {
                designatedDrivers.add(person);
            }
        }
        return designatedDrivers;
    }
    
    private void incrementNumberOfDrives(Map<Person, Integer> numberOfDrivesMap, Person driver) {
		// map for specific week
    	Integer number = numberOfDrivesMap.get(driver);
        numberOfDrivesMap.put(driver, number + 1);
        
        // total map
        number = numberOfDrives_Total.get(driver);
        numberOfDrives_Total.put(driver, number + 1);
	}

}
