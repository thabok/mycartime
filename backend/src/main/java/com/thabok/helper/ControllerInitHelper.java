package com.thabok.helper;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Map.Entry;
import java.util.Set;

import com.thabok.entities.CustomDay;
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
		return getPersonsByStartTime(persons, dayOfWeekABCombo, false);
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
    public static Map<Integer, List<Person>> getPersonsByStartTime(List<Person> persons, DayOfWeekABCombo dayOfWeekABCombo, boolean applyTolerance) {
    	return getPersonsByStartOrEndTime(persons, dayOfWeekABCombo, applyTolerance, false);
    }
    
    /**
     * Returns a map of persons grouped by their end time.
     * 
     * @param dayOfWeek the day of the week needed to query the persons' schedules
     * @return a map of persons grouped by their end time
     */
    public static Map<Integer, List<Person>> getPersonsByEndTime(List<Person> persons, DayOfWeekABCombo dayOfWeekABCombo) {
    	return getPersonsByEndTime(persons, dayOfWeekABCombo, false);
    }
    
    /**
     * Returns a map of persons grouped by their end time.
     * 
     * @param dayOfWeek the day of the week needed to query the persons' schedules
     * @return a map of persons grouped by their end time
     */
    public static Map<Integer, List<Person>> getPersonsByEndTime(List<Person> persons, DayOfWeekABCombo dayOfWeekABCombo, boolean applyTolerance) {
        return getPersonsByStartOrEndTime(persons, dayOfWeekABCombo, applyTolerance, true);
    }
    
    private static Map<Integer, List<Person>> getPersonsByStartOrEndTime(List<Person> persons,
    		DayOfWeekABCombo dayOfWeekABCombo, boolean applyTolerances, boolean isWayBack) {
    	Map<Integer, List<Person>> personsByStartOrEndTime = new HashMap<>(); 
        // place persons into groups based on start/end time
        for (Person person : persons) {
        	CustomDay preferences = Util.getCustomDayObject(person, dayOfWeekABCombo);
        	// skip persons based on their preferences
        	if ((isWayBack && preferences.skipAfternoon) || (!isWayBack && preferences.skipMorning)) {
        		continue;
        	}
            TimingInfo timingInfo = person.schedule.get(dayOfWeekABCombo.getUniqueNumber());
            if (timingInfo != null && TimetableHelper.isPersonActiveOnThisDay(person, dayOfWeekABCombo)) {
                int time = isWayBack ? timingInfo.getEndTime() : timingInfo.getStartTime();
                if (!personsByStartOrEndTime.containsKey(time)) {
                    List<Person> list = new ArrayList<>();
                    personsByStartOrEndTime.put(time, list);
                }
                personsByStartOrEndTime.get(time).add(person);
            }
        }
        if (!applyTolerances) {
        	return personsByStartOrEndTime;
        }
        // merge stuff if tolerance shall be considered
        Map<Integer, List<Person>> personsByTimeMerged = new HashMap<>();
        int lastReferenceTime = 0;
        List<Entry<Integer, List<Person>>> sortedEntries = new ArrayList<>(personsByStartOrEndTime.entrySet());
        sortedEntries.sort((e1, e2) -> e1.getKey().compareTo(e2.getKey()));
        for (Entry<Integer, List<Person>> entry : sortedEntries) {
        	if (!Util.isTimeDifferenceAcceptable(entry.getKey(), lastReferenceTime)) {
                lastReferenceTime = entry.getKey();
                personsByTimeMerged.put(lastReferenceTime, new ArrayList<>());
            }
        	personsByTimeMerged.get(lastReferenceTime).addAll(entry.getValue());
        }
        return personsByTimeMerged;
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
        for (Person person : allPersonsForThisDay) {
        	CustomDay customDayObject = Util.getCustomDayObject(person, dayOfTheWeekABCombo);
            if (!customDayObject.ignoreCompletely && customDayObject.needsCar) {
                designatedDrivers.add(person);
            }
        }
        return designatedDrivers;
    }
	
}
