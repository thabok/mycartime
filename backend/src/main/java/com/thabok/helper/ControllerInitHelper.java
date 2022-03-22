package com.thabok.helper;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

import com.thabok.entities.DayOfWeekABCombo;
import com.thabok.entities.DayPlanInput;
import com.thabok.entities.Person;
import com.thabok.entities.TimingInfo;
import com.thabok.util.Util;


/**
 * Static helper class for the Controller initialization.
 * @author thabok
 */
public class ControllerInitHelper {

	/**
     * Returns a map of persons grouped by their start time
     * 
     * @param dayOfWeek the day of the week needed to query the persons' schedules
     * @return a map of persons grouped by their start time
     */
	public static Map<Integer, List<Person>> getPersonsByStartTime(List<Person> persons, DayOfWeekABCombo dayOfWeekABCombo) {
		return getPersonsByStartTime(persons, dayOfWeekABCombo, 0);
	}
	
	/**
     * Returns a map of persons grouped by their start time.
     * If a tolerance is set (toleranceInMinutes > 0), people with different start times are grouped together based on that tolerance.
     * <br><br>
     * Example:
     * <ul>
     * <li>toleranceInMinutes: 10</li>
     * <li>personA start time: 745</li>
     * <li>personB start time: 755</li>
     * <li>personC start time: 800</li>
     * </ul>
     * 
     * <i>Group 1: Person A and B, Group 2: Person C</i>
     * 
     * @param dayOfWeek the day of the week needed to query the persons' schedules
     * @return a map of persons grouped by their start time
     */
    public static Map<Integer, List<Person>> getPersonsByStartTime(List<Person> persons, DayOfWeekABCombo dayOfWeekABCombo, int toleranceInMinutes) {
        Map<Integer, List<Person>> personsByFirstLesson = new HashMap<>(); 
        // place persons into groups based on start time
        for (Person person : persons) {
            TimingInfo timingInfo = person.schedule.get(dayOfWeekABCombo.getUniqueNumber());
            if (timingInfo != null) {
                int startTime = timingInfo.getStartTime();
                if (!personsByFirstLesson.containsKey(startTime)) {
                    List<Person> list = new ArrayList<>();
                    personsByFirstLesson.put(startTime, list);
                }
                personsByFirstLesson.get(startTime).add(person);
            }
        }
        return personsByFirstLesson;
    }
    
    /**
     * Returns a map of persons grouped by their end time.
     * 
     * @param dayOfWeek the day of the week needed to query the persons' schedules
     * @return a map of persons grouped by their end time
     */
    public static Map<Integer, List<Person>> getPersonsByEndTime(List<Person> persons, DayOfWeekABCombo dayOfWeekABCombo) {
        Map<Integer, List<Person>> personsByLastLesson = new HashMap<>(); 
        // place persons into groups based on first-lesson
        for (Person person : persons) {
            TimingInfo timingInfo = person.schedule.get(dayOfWeekABCombo.getUniqueNumber());
            if (timingInfo != null) {
                int lastLesson = timingInfo.getEndTime();
                if (!personsByLastLesson.containsKey(lastLesson)) {
                    List<Person> list = new ArrayList<>();
                    personsByLastLesson.put(lastLesson, list);
                }
                personsByLastLesson.get(lastLesson).add(person);
            }
        }
        return personsByLastLesson;
    }
    
    /**
     * Returns a set of persons that need to drive anyway because they are the only one in a time slot
     * or have custom preferences that say so.
     * 
     * @param personsByFirstLesson map with persons by start time slot
     * @param personsByLastLesson map with persons by end time slot
     * @param allPersonsForThisDay list of all persons for this day to extract custom preferences 
     * @param dayOfTheWeekABCombo to know which day it is
     * @return a set of persons that need to drive anyway because they are the only one in a time slot
     */
    public static Set<Person> getDesignatedDrivers(DayPlanInput dpi, List<Person> allPersonsForThisDay, DayOfWeekABCombo dayOfTheWeekABCombo) {
        Set<Person> designatedDrivers = new HashSet<>();

        // 1. add persons who are alone to their first lesson
        for (List<Person> persons : dpi.personsByFirstLesson.values()) {
            if (persons.size() == 1) {
                designatedDrivers.add(persons.iterator().next());
            }
        }
        
        // 2. add persons who are alone from their last lesson
        for (List<Person> persons : dpi.personsByLastLesson.values()) {
            if (persons.size() == 1) {
                designatedDrivers.add(persons.iterator().next());
            }
        }
        
        // 3. Add persons based on custom preferences
        // pay attention: key is 0 based while uniqueNumber is 1 based
        int customDaysIndex = Util.dowComboToCustomDaysIndex(dayOfTheWeekABCombo);
        for (Person person : allPersonsForThisDay) {
            if (person.customDays.get(customDaysIndex).needsCar) {
                designatedDrivers.add(person);
            }
        }
        return designatedDrivers;
    }
	
}
