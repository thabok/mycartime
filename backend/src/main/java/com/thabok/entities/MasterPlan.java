package com.thabok.entities;

import java.util.Map;
import java.util.TreeMap;

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
			DayPlanInput dpi = inputsPerDay.get(combo.getUniqueNumber());
			DayPlan dayPlan = new DayPlan(combo);
			try { Util.addPartiesForDesignatedDrivers(dayPlan, dpi.designatedDrivers); } catch (Exception e) {}
			dayPlans.put(combo.getUniqueNumber(), dayPlan);
			Util.registerMirrorDrivers(inputsPerDay, combo, dpi);
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
