package com.thabok.main;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

import com.thabok.entities.DayOfWeekABCombo;
import com.thabok.entities.DayPlanInput;
import com.thabok.entities.MasterPlan;
import com.thabok.entities.Person;
import com.thabok.util.Util;

public class Controller {

	public static int referenceWeekStartDate;
	private Map<Integer, DayPlanInput> inputsPerDay = new HashMap<>();;
	private List<Person> persons;

	public Controller(List<Person> persons) {
		this.persons = persons;
		for (DayOfWeekABCombo dayOfWeekABCombo : Util.weekdayListAB) {
			DayPlanInput dpi = new DayPlanInput();
			dpi.personsByFirstLesson = Util.getPersonsByFirstLesson(persons, dayOfWeekABCombo);
			dpi.personsByLastLesson = Util.getPersonsByLastLesson(persons, dayOfWeekABCombo);
			dpi.designatedDrivers = Util.getDesignatedDrivers(dpi, persons, dayOfWeekABCombo);
			inputsPerDay.put(dayOfWeekABCombo.getUniqueNumber(), dpi);
		}
	}


	/**
	 * Main method to come up with a driving plan for the a & b week
	 * 
	 * @return the two-week-plan
	 */
	public MasterPlan calculateWeekPlan() {
		
		// this plan will be filled, optimized and finally proudly presented
		MasterPlan theMasterPlan = new MasterPlan(inputsPerDay);
		
		System.out.println();
		System.out.println(theMasterPlan);
		Util.summarizeNumberOfDrives(theMasterPlan, persons);
		System.out.println();
		
		/*
		 * 
		 */
		
		return theMasterPlan;
	}


	/**
	 * Adapts the given plan to work with the updated
	 * <br>- persons' schedule
	 * <br>- persons' personal preferences 
	 * 
	 * @param preset the old plan - the new one should stay as close as possible to this
	 * @return the adapted plan
	 */
	public MasterPlan adaptPreset(MasterPlan preset) {
		// TODO Auto-generated method stub
		return null;
	}

}
