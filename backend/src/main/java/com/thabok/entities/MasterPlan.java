package com.thabok.entities;

import java.io.OutputStream;
import java.io.PrintStream;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.stream.Collectors;

import com.thabok.helper.ControllerInitHelper;
import com.thabok.helper.PartyHelper;
import com.thabok.util.Util;

public class MasterPlan {

	public String summary;
	private Map<Integer, DayPlan> dayPlans = new TreeMap<>();
	
	public List<Person> persons;
	public Map<Integer, DayPlanInput> inputsPerDay;
	public List<DayOfWeekABCombo> key;

	/**
	 * Creates a new master plan and initializes all day plans with the respective designated drivers.
	 * 
	 * @param inputsPerDay the inputs per day (for designated drivers)
	 */
	public MasterPlan(List<Person> persons, MasterPlan preset) {
		this.persons = new ArrayList<>(persons);
		if (preset == null) {
			// "preset == null" indicates a run inside the optimization loop
			// Store order of weekdays in week plan
			key = new ArrayList<>(Util.weekdayListAB);
			// disable prints to console
			Util.out = new PrintStream(OutputStream.nullOutputStream());
		} else {
			key = preset.key;
			Util.weekdayListAB = new ArrayList<>(preset.key);
			// enable prints to console for preset run
			Util.out = System.out;
		}

		initialize();
		
	}

	/**
	 * Initializes inputsPerDay field with persons by 1st / last lesson and designated drivers
	 * and the week plan's day plans 
	 */
	private void initialize() {
		inputsPerDay = new HashMap<>();
        for (DayOfWeekABCombo dayOfWeekABCombo : Util.weekdayListAB) {
        	// inputs per day
            DayPlanInput dpi = new DayPlanInput();
            dpi.personsByFirstLesson = ControllerInitHelper.getPersonsByStartTime(persons, dayOfWeekABCombo, true);
            dpi.personsByLastLesson = ControllerInitHelper.getPersonsByEndTime(persons, dayOfWeekABCombo, true);
            dpi.designatedDrivers = ControllerInitHelper.getDesignatedDrivers(dpi, persons, dayOfWeekABCombo);
            inputsPerDay.put(dayOfWeekABCombo.getUniqueNumber(), dpi);

            // the week plan's day plans
            DayPlan dayPlan = new DayPlan(dayOfWeekABCombo);
            // add a party for each of the day's designated drivers
            try { PartyHelper.addPartiesForDesignatedDrivers(dayPlan, inputsPerDay, dayPlans); } catch (Exception e) { e.printStackTrace(); }
            dayPlans.put(dayOfWeekABCombo.getUniqueNumber(), dayPlan);
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
		return dayPlans.values().stream().sorted((dp1, dp2) -> Integer.compare(dp1.getDayOfWeekABCombo().getUniqueNumber(), dp2.getDayOfWeekABCombo().getUniqueNumber())).collect(Collectors.toList()).toString();
	}


}
