package com.thabok.entities;

import java.time.DayOfWeek;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

public class WeekPlan {

	public String summary;
	private Map<DayOfWeek, DayPlan> dayPlans = new TreeMap<>();
	private List<DayOfWeek> weekDayPermutation;

	public Map<DayOfWeek, DayPlan> getDayPlans() {
		return dayPlans;
	}

	public void setDayPlans(Map<DayOfWeek, DayPlan> dayPlans) {
		this.dayPlans = dayPlans;
	}

	public void put(DayOfWeek day, DayPlan plan) {
		this.dayPlans.put(day, plan);
	}
	
	public DayPlan get(DayOfWeek day) {
		return this.dayPlans.get(day);
	}
	
	public String toString() {
		return dayPlans.values().toString();
	}

	public List<DayOfWeek> getWeekDayPermutation() {
		return weekDayPermutation;
	}

	public void setWeekDayPermutation(List<DayOfWeek> weekDayPermutation) {
		this.weekDayPermutation = weekDayPermutation;
	}


}
