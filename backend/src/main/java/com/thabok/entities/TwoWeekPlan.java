package com.thabok.entities;

import java.util.List;
import java.util.Map;
import java.util.TreeMap;

public class TwoWeekPlan {

	public String summary;
	private Map<DayOfWeekABCombo, DayPlan> dayPlans = new TreeMap<>();
	private List<DayOfWeekABCombo> weekDayPermutation;

	public Map<DayOfWeekABCombo, DayPlan> getDayPlans() {
		return dayPlans;
	}

	public void setDayPlans(Map<DayOfWeekABCombo, DayPlan> dayPlans) {
		this.dayPlans = dayPlans;
	}

	public void put(DayOfWeekABCombo day, DayPlan plan) {
		this.dayPlans.put(day, plan);
	}
	
	public DayPlan get(DayOfWeekABCombo day) {
		return this.dayPlans.get(day);
	}
	
	public String toString() {
		return dayPlans.values().toString();
	}

	public List<DayOfWeekABCombo> getWeekDayPermutation() {
		return weekDayPermutation;
	}

	public void setWeekDayPermutation(List<DayOfWeekABCombo> weekDayPermutation) {
		this.weekDayPermutation = weekDayPermutation;
	}


}
