package com.thabok.helper;

import java.util.List;

import com.thabok.entities.DayPlan;

public class PlanOptimizationHelper {

    public static DayPlan getDayPlanForLazyDriver(List<DayPlan> dayPlans) {
    	// FIXME: This needs to consider capacity requirements
        return dayPlans.get(0);
    }


}
