package com.thabok.helper;

import java.util.List;
import java.util.Map;

import com.thabok.entities.DayPlan;
import com.thabok.entities.MasterPlan;
import com.thabok.entities.Party;
import com.thabok.entities.Person;
import com.thabok.entities.TimingInfo;
import com.thabok.util.Util;

public class PlanOptimizationHelper {

	/**
	 * Measures if this person would resolve a tight spot in the plan.
	 * Returns a value between 0 (not helping) and 2 (resolves a big
	 * tight spot on morning AND afternoon)
	 * 
	 * @param dayPlan the day to check
	 * @param lazyDriver the lazy driver that can create a party
	 * @return a value between 0 (not helping) and 2 (resolves a big
	 * 			tight spot on morning AND afternoon)
	 */
	private static float measureTightnessSolvedByThisPerson(DayPlan dayPlan, Person lazyDriver) {
		// parties of the given day
		List<Party> schoolboundParties = PartyHelper.getParties(dayPlan, true);
		List<Party> homeboundParties = PartyHelper.getParties(dayPlan, false);
		
		TimingInfo timingInfo = lazyDriver.schedule.get(dayPlan.getDayOfWeekABCombo().getUniqueNumber());

		// schoolbound parties matching this persons timeslot
		List<Party> schoolboundPartiesMatchingTime = null;
		Map<Integer, List<Party>> schoolboundPartiesByTimeslot = PartyHelper.getPartiesByStartOrEndTime(schoolboundParties, true);
		for (Integer timeslot : schoolboundPartiesByTimeslot.keySet()) {
			if (Util.isTimeDifferenceAcceptable(timingInfo.getStartTime(), timeslot)) {
				schoolboundPartiesMatchingTime = schoolboundPartiesByTimeslot.get(timeslot);
				break;
			}
		}
		if (schoolboundPartiesMatchingTime == null) {
			System.err.println("WARNING: schoolboundPartiesMatchingTime == null (PlanOptimizationHelper:38)");
		}
		int freeSeatsTotal_schoolbound = 0;
		for (Party p : schoolboundPartiesMatchingTime) {
			freeSeatsTotal_schoolbound += p.getNumberOfFreeSeats();
		}
		// float value between 0 (>= 5 free seats) and 1 (not a single free seat)
		float schoolboundTightness = Math.max(0, (5 - freeSeatsTotal_schoolbound)) / 5f;
		
		// homebound parties matching this persons timeslot
		List<Party> homeboundPartiesMatchingTime = null;
		Map<Integer, List<Party>> homeboundPartiesByTimeslot = PartyHelper.getPartiesByStartOrEndTime(homeboundParties, true);
		for (Integer timeslot : homeboundPartiesByTimeslot.keySet()) {
			if (Util.isTimeDifferenceAcceptable(timingInfo.getEndTime(), timeslot)) {
				homeboundPartiesMatchingTime = homeboundPartiesByTimeslot.get(timeslot);
				break;
			}
		}
		if (homeboundPartiesMatchingTime == null) {
			System.err.println("WARNING: homeboundPartiesMatchingTime == null (PlanOptimizationHelper:37)");
		}
		int freeSeatsTotal_homebound = 0;
		for (Party p : schoolboundPartiesMatchingTime) {
			freeSeatsTotal_homebound += p.getNumberOfFreeSeats();
		}
		// float value between 0 (>= 5 free seats) and 1 (not a single free seat)
		float homeboundTightness = Math.max(0, (5 - freeSeatsTotal_homebound)) / 5f;
		
		return schoolboundTightness + homeboundTightness;
	}
	
	/**
	 * Evaluates which of the available days could use another driver.
	 * This is done based on two aspects:
	 * 
	 * - find a day where its tight, e.g. a friday afternoon where 10 people
	 *   are placed in 2 cars
	 *   
	 * Definition of tight for 1 timeslot:
	 * x >= 5 free seats->0%, 4->20%, 3->40%, 2->60%, 1->80%, 0->100%
	 * Per Day: highest value counts
	 * 
	 * @param dayPlans the days on which the given lazyDriver is still available
	 * @param lazyDriver
	 * @return
	 */
    public static DayPlan getDayPlanForLazyDriver(List<DayPlan> dayPlans, Person lazyDriver) {
    	float highestTightnessResolveValue = -1f;
    	DayPlan tightestDayThatThisPersonCanSolve = null;
    	
    	// TODO: Note -> this may not be the optimal solution, as we search for local optima
    	// Ideal solution would be to preserve the whole list of days per person with tightness values and then
    	// figure out the best distribution... but that's too much for a Tuesday evening. 
    	
    	for (DayPlan dp : dayPlans) {
    		float tightnessSolvedByThisPerson = measureTightnessSolvedByThisPerson(dp, lazyDriver);
    		if (tightnessSolvedByThisPerson > highestTightnessResolveValue) {
    			highestTightnessResolveValue = tightnessSolvedByThisPerson;
    			tightestDayThatThisPersonCanSolve = dp;
    		}
    	}
    	
		return tightestDayThatThisPersonCanSolve;
//		return dayPlans.get(0); // <-- TODO compare old and new solution to see impact :)
    }

	public static void printTightnessOverview(MasterPlan mp) {
		System.out.println("Tightness levels:");
		for (DayPlan dp : mp.getDayPlans().values()) {
			// find worst tight spot for this day
			List<Party> schoolboundParties = PartyHelper.getParties(dp, true);
			List<Party> homeboundParties = PartyHelper.getParties(dp, false);
			
			float schoolboundTightness = -1;
			Map<Integer, List<Party>> schoolboundPartiesByTimeslot = PartyHelper.getPartiesByStartOrEndTime(schoolboundParties, true);
			for (List<Party> parties : schoolboundPartiesByTimeslot.values()) {
				int freeSeatsTotal_schoolbound = 0;
				for (Party p : parties) {
					freeSeatsTotal_schoolbound += p.getNumberOfFreeSeats();
				}
				// float value between 0 (>= 5 free seats) and 1 (not a single free seat)
				float currentSchoolboundTightness = Math.max(0, (5 - freeSeatsTotal_schoolbound)) / 5f;
				if (currentSchoolboundTightness > schoolboundTightness) {
					schoolboundTightness = currentSchoolboundTightness;
				}
			}
			
			float homeboundTightness = -1;
			Map<Integer, List<Party>> homeboundPartiesByTimeslot = PartyHelper.getPartiesByStartOrEndTime(homeboundParties, true);
			for (List<Party> parties : homeboundPartiesByTimeslot.values()) {
				int freeSeatsTotal_homebound = 0;
				for (Party p : parties) {
					freeSeatsTotal_homebound += p.getNumberOfFreeSeats();
				}
				// float value between 0 (>= 5 free seats) and 1 (not a single free seat)
				float currentHomeboundTightness = Math.max(0, (5 - freeSeatsTotal_homebound)) / 5f;
				if (currentHomeboundTightness > homeboundTightness) {
					homeboundTightness = currentHomeboundTightness;
				}
			}
			
			// print total per day
			System.out.println("- " + dp.getDayOfWeekABCombo() + ": " + ((schoolboundTightness + homeboundTightness) * 100) + "%");
		}
		
	}


}
