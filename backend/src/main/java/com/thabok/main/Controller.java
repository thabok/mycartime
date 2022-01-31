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

	private static final float MIN_MAX_DIFF_PENALTY_FACTOR = 		 0.5f; // 0.3f;
	private static final float AVERAGE_DRIVING_DAYS_PENALTY_FACTOR = 0.1f; // 0.3f;
	private static final float MISSED_GUIDELINE_FACTOR = 			 0.5f; // 0.5f;
	
	private List<Person> persons;
    private Map<Person, Integer> numberOfDrives;
    private List<Rule> rules = new ArrayList<>();
    private Map<DayOfWeekABCombo, DayPlanInput> inputsPerDay;
    public static List<DayOfWeek> weekdays = Arrays.asList(DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY, DayOfWeek.THURSDAY, DayOfWeek.FRIDAY);
    public static int referenceWeekStartDate;
    
    public Controller(List<Person> persons) {
        this.persons = persons;
        numberOfDrives = new HashMap<>();
        persons.forEach(p -> numberOfDrives.put(p, 0));
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
            float progressValue = 0.95f + (((float) (i+1) / iterations) * 0.05f);
            WebService.updateProgress(progressValue, msg);
        }
        System.out.println("Best Score: " + bestScore);
        return bestPlan;
    }
    
    public String summarizeNumberOfDrives(TwoWeekPlan wp) {
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
        inputsPerDay = new HashMap<>();
        persons.forEach(p -> numberOfDrives.put(p, 0));
        for (DayOfWeekABCombo dayOfWeekABCombo : Util.weekdayListAB) {
            DayPlanInput dpi = new DayPlanInput();
            dpi.personsByFirstLesson = getPersonsByFirstLesson(persons, dayOfWeekABCombo);
            dpi.personsByLastLesson = getPersonsByLastLesson(persons, dayOfWeekABCombo);
            dpi.designatedDrivers = getDesignatedDrivers(dpi, persons, dayOfWeekABCombo);
            inputsPerDay.put(dayOfWeekABCombo, dpi);
            dpi.designatedDrivers.forEach(driver -> {
                Integer number = numberOfDrives.get(driver);
                numberOfDrives.put(driver, number + 1);
            });
        }
    }
    
    public TwoWeekPlan calculateWeekPlan() throws Exception {
        initialize();
        TwoWeekPlan wp = new TwoWeekPlan();
        // shuffle lists to get new combinations
        Collections.shuffle(this.persons);
        Collections.shuffle(Util.weekdayListAB);
        wp.setWeekDayPermutation(new ArrayList<>(Util.weekdayListAB));
        for (DayOfWeekABCombo dayOfWeekABCombo : wp.getWeekDayPermutation()) {
            DayOfWeekABCombo referenceCombo = getReferenceCombo(wp.getWeekDayPermutation(), dayOfWeekABCombo);
            DayPlan referencePlan = wp.get(referenceCombo);
            wp.put(dayOfWeekABCombo, calculateDayPlan(dayOfWeekABCombo, referencePlan));
        }
        return wp;
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
        float minMaxDiffPenalty = maxDrivingDays == minDrivingDays ? 0f : 1 - (1f / (1 + maxDrivingDays - minDrivingDays));
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
        
        List<Person> personsForThisDay = persons.stream().filter(p -> p.schedule.getTimingInfoPerDay().get(dayOfWeekABCombo.getUniqueNumber()) != null).collect(Collectors.toList());
        
        
        /*
         * PART 1: Solo drivers
         */
        
        // add parties for solo drivers
        addPartiesForDesignatedDrivers(dayPlan, dpi.designatedDrivers);

        /*
         * PART 2: There & back matches
         * - for each first & last lesson combo: find the set of people that match and are not designated drivers
         * - if set is not empty: create parties 
         */
        Set<Person> coveredPersons = new HashSet<>(dpi.designatedDrivers);
        
        // This threshold defines how many drives a driver may already have to be considered. This will be increased in the while-loop if needed
        int driverConsiderationThreshold = getInitialDriverConsiderationThreshold();
        // Do this until all persons have been covered
        while (coveredPersons.size() < personsForThisDay.size()) {
            for (Person remainingPerson : personsForThisDay) {
                if (coveredPersons.contains(remainingPerson)) {
                    continue;
                }
                List<PartyTouple> candidatesThere = new ArrayList<>();
                List<PartyTouple> candidatesBack = new ArrayList<>();
                for (PartyTouple pt : dayPlan.getPartyTouples()) {
                    boolean timeThereMatches = remainingPerson.getLesson(dayOfWeekABCombo, false) == pt.getPartyThere().getLesson();
                    boolean partyThereIsAvailable = Util.partyIsAvailable(pt.getPartyThere());
                    if (timeThereMatches && partyThereIsAvailable) {
                        // remaining person could join this party (->)
                        candidatesThere.add(pt);
                    }
                    boolean timeBackMatches = remainingPerson.getLesson(dayOfWeekABCombo, true) == pt.getPartyBack().getLesson();
                    boolean partyBackIsAvailable = Util.partyIsAvailable(pt.getPartyThere());
                    if (timeBackMatches && partyBackIsAvailable) {
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
        // Performs balancing to prevent one car
        // from filling up and the first person that doesn't
        // fit anymore drives alone while the other car is full
        balanceEquivalentParties(dayPlan, referencePlan);
        return dayPlan;
    }

    /**
     * Finds equivalent parties (i.e., parties that drive at the same time) 
     * and balances the passenger load to prevent "the party-bus and the loner"
     * 
     * @param dayPlan the dayPlan with potentially unbalanced parties  
     * @param referencePlan reference plan, may be null
     */
    private void balanceEquivalentParties(DayPlan dayPlan, DayPlan referencePlan) {
        // Collect equivalent parties
        Map<Integer, List<Party>> wayTherePartiesByStartLesson = new HashMap<>();
        Map<Integer, List<Party>> wayBackPartiesByEndLesson = new HashMap<>();
        for (PartyTouple touple : dayPlan.getPartyTouples()) {
            Party pt = touple.getPartyThere();
            List<Party> partiesThereForCurrentLesson = wayTherePartiesByStartLesson.get(pt.getLesson());
            if (partiesThereForCurrentLesson == null) {
                partiesThereForCurrentLesson = new ArrayList<>();
                wayTherePartiesByStartLesson.put(pt.getLesson(), partiesThereForCurrentLesson);
            }
            partiesThereForCurrentLesson.add(pt);
            
            Party pb = touple.getPartyBack();
            List<Party> partiesBackForCurrentLesson = wayBackPartiesByEndLesson.get(pb.getLesson());
            if (partiesBackForCurrentLesson == null) {
                partiesBackForCurrentLesson = new ArrayList<>();
                wayBackPartiesByEndLesson.put(pb.getLesson(), partiesBackForCurrentLesson);
            }
            partiesBackForCurrentLesson.add(pb);
        }
        
        // Balance equivalent parties
        balanceEquivalentParties(wayTherePartiesByStartLesson, referencePlan);
        balanceEquivalentParties(wayBackPartiesByEndLesson, referencePlan);
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
        for (List<Party> equivalentPartiesThere : partiesByLesson.values()) {
            if (equivalentPartiesThere.size() > 1) {
                // normal balancing based on number of passengers & free seats 
                balanceListOfPartiesBasedOnNumbers(equivalentPartiesThere);
                
                // balance according to referencePlan
                reorganizePartiesAccordingToReferencePlan(equivalentPartiesThere, referencePlan);
            }
        }
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
            for (Party party : equivalentParties) {
                for (Person passenger : party.getPassengers()) {
                    Set<Person> preferredPartyPeople = getPreferredPartyPeopleForPerson(referencePlan, isWayBack, party, passenger);
                    if (!partyMeetsPppCriteria(party, preferredPartyPeople)) {
                        // this person is sad because it's not driving with anyone from the referencePlan (other week, same day)
                        Party preferredParty = getBestPartyPeopleParty(equivalentParties, preferredPartyPeople);
                        if (preferredParty != null) {
                            Person swappee = getSwapCandidateFromPreferredParty(preferredParty, referencePlan);
                            if (swappee != null) {
                                // we have a swappee, let's go swap!
                                swapJobs.add(new SwapJob(party, preferredParty, passenger, swappee));
                            }
                        }
                    }
                }
            }
            // now we have collected a number of SwapJobs, let's go swap!
            swapJobs.forEach(swapJob -> swapJob.swappediswap());
        }
        
    }

    private Person getSwapCandidateFromPreferredParty(Party preferredParty, DayPlan referencePlan) {
        for (Person passenger : preferredParty.getPassengers()) {
            Set<Person> preferredPartyPeople = getPreferredPartyPeopleForPerson(referencePlan, preferredParty.isWayBack(), preferredParty, passenger);
            if (preferredPartyPeople.contains(preferredParty.getDriver())) {
                continue;
            }
            boolean hasFriendInCar = false;
            for (Person friend : preferredPartyPeople) {
                if (preferredPartyPeople.contains(friend)) {
                    hasFriendInCar = true;
                    break;
                }
            }
            if (!hasFriendInCar) {
                // this person has no friends in the car -> can be the swappee
                return passenger;
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
                matchingDriver = party.getDriver().equals(passenger);
                matchingPassenger = party.getPassengers().contains(passenger);
            } else {
                p = referencePartyTouple.getPartyThere();
                matchingDriver = party.getDriver().equals(passenger);
                matchingPassenger = party.getPassengers().contains(passenger);
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
    private int getInitialDriverConsiderationThreshold() {
        int min = 100;
        for (int noDrives : numberOfDrives.values()) {
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
     */
    private void addSoloParty(DayPlan dayPlan, Person driver, boolean isDesignatedDriver) throws Exception {
        PartyTouple partyTouple = new PartyTouple();
        
        Party partyThere = new Party();
        partyThere.setDayOfTheWeekABCombo(dayPlan.getDayOfWeekABCombo());
        partyThere.setDriver(driver);
        partyThere.setWayBack(false);
        int firstLesson = driver.schedule.getTimingInfoPerDay().get(dayPlan.getDayOfWeekABCombo().getUniqueNumber()).getFirstLesson();
        partyThere.setLesson(firstLesson);
        partyThere.setTime(Util.lessonStartTimes[firstLesson - 1]);
        partyTouple.setPartyThere(partyThere);
        
        Party partyBack = new Party();
        partyBack.setDayOfTheWeekABCombo(dayPlan.getDayOfWeekABCombo());
        partyBack.setDriver(driver);
        partyBack.setWayBack(true);
        int lastLesson = driver.getLesson(dayPlan.getDayOfWeekABCombo(), true);
        partyBack.setLesson(lastLesson);
        partyBack.setTime(Util.lessonEndTimes[lastLesson - 1]);
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

}
