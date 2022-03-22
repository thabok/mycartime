package com.thabok.entities;

import java.util.Map;
import java.util.TreeMap;

import com.thabok.helper.PartyHelper;
import com.thabok.util.Util;

public class MasterPlan {

	public String summary;
	private Map<Integer, DayPlan> dayPlans = new TreeMap<>();

	/**
	 * Creates a new master plan and initializes all day plans with the respective designated drivers.
	 * 
	 * @param inputsPerDay the inputs per day (for designated drivers)
	 */
	public MasterPlan(Map<Integer, DayPlanInput> inputsPerDay) {
		for (DayOfWeekABCombo combo : Util.weekdayListAB) {
			DayPlan dayPlan = new DayPlan(combo);
			dayPlans.put(combo.getUniqueNumber(), dayPlan);
		}
		for (DayPlan dayPlan : dayPlans.values()) {
			try { PartyHelper.addPartiesForDesignatedDrivers(dayPlan, inputsPerDay, dayPlans); } catch (Exception e) { e.printStackTrace(); }
		}
	}

	public Map<Integer, DayPlan> getDayPlans() {
		return dayPlans;
	}

	public void setDayPlans(Map<Integer, DayPlan> dayPlans) {
		this.dayPlans = dayPlans;
	}

	public void put(Integer dowABComboNumber, DayPlan plan) {
		this.dayPlans.put(dowABComboNumber, plan);
	}
	
	public DayPlan get(Integer dowABComboNumber) {
		return this.dayPlans.get(dowABComboNumber);
	}
	
	public String toString() {
		return dayPlans.values().toString();
	}


}
