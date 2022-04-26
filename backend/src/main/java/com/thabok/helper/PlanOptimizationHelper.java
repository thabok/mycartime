package com.thabok.helper;

import java.util.List;

import com.thabok.entities.DayPlan;
import com.thabok.entities.Person;

public class PlanOptimizationHelper {

    public static DayPlan getDayPlanForLazyDriver(List<DayPlan> dayPlans, Person lazyDriver) {

//    	for (DayPlan dp : dayPlans) {
//    		List<Party> partiesThere = dp.getPartyTouples().stream()
//    				.map(pt -> pt.getPartyThere())
//    				.filter(p -> PartyHelper.partyIsAvailable(p))
//    				.collect(Collectors.toList());
//    		List<Party> partiesBack = dp.getPartyTouples().stream()
//    				.map(pt -> pt.getPartyBack())
//    				.filter(p -> PartyHelper.partyIsAvailable(p))
//    				.collect(Collectors.toList());
//    		Map<Integer, List<Party>> wayTherePartiesByStartTime = PartyHelper.getPartiesByStartOrEndTime(partiesThere, true);
//            Map<Integer, List<Party>> wayBackPartiesByEndTime = PartyHelper.getPartiesByStartOrEndTime(partiesBack, true);
//    		
//            int startTime = lazyDriver.getTimeForDowCombo(dp.getDayOfWeekABCombo(), false);
//            int endTime = lazyDriver.getTimeForDowCombo(dp.getDayOfWeekABCombo(), true);
//            
//            List<Party> list = wayTherePartiesByStartTime.get(startTime);
//            
//    	}
        
        
		// FIXME: This needs to consider capacity requirements
		return dayPlans.get(0);
    	
    }


}
