package com.thabok.entities;

import java.io.OutputStream;
import java.io.PrintStream;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.stream.Collectors;

import com.thabok.helper.ControllerInitHelper;
import com.thabok.helper.PartyHelper;
import com.thabok.util.Util;

public class MasterPlan {

	public List<Person> persons;
	public Map<Integer, DayPlanInput> inputsPerDay;
	public String summary;
	public List<DayOfWeekABCombo> key;
	private Map<Integer, DayPlan> dayPlans = new TreeMap<>();

	/**
	 * Creates a new master plan and initializes all day plans with the respective designated drivers.
	 * 
	 * @param inputsPerDay the inputs per day (for designated drivers)
	 */
	public MasterPlan(List<Person> persons, MasterPlan preset) {
		this.persons = new ArrayList<>(persons);
		initialize();
		if (preset == null) {
			Collections.shuffle(Util.weekdayListAB);
			Util.out = new PrintStream(OutputStream.nullOutputStream());
			key = new ArrayList<>(Util.weekdayListAB);
		} else {
			key = preset.key;
			Util.weekdayListAB = new ArrayList<>(preset.key);
			Util.out = System.out;
		}
		for (DayOfWeekABCombo combo : Util.weekdayListAB) {
			DayPlan dayPlan = new DayPlan(combo);
			dayPlans.put(combo.getUniqueNumber(), dayPlan);
		}
		for (DayPlan dayPlan : dayPlans.values()) {
			try { PartyHelper.addPartiesForDesignatedDrivers(dayPlan, inputsPerDay, dayPlans); } catch (Exception e) { e.printStackTrace(); }
		}
	}

	private void initialize() {
		inputsPerDay = new HashMap<>();
        for (DayOfWeekABCombo dayOfWeekABCombo : Util.weekdayListAB) {
            DayPlanInput dpi = new DayPlanInput();
            dpi.personsByFirstLesson = ControllerInitHelper.getPersonsByStartTime(persons, dayOfWeekABCombo, true);
            dpi.personsByLastLesson = ControllerInitHelper.getPersonsByEndTime(persons, dayOfWeekABCombo, true);
            dpi.designatedDrivers = ControllerInitHelper.getDesignatedDrivers(dpi, persons, dayOfWeekABCombo);
            inputsPerDay.put(dayOfWeekABCombo.getUniqueNumber(), dpi);
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
