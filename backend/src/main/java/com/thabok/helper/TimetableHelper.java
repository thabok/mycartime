package com.thabok.helper;

import java.time.DayOfWeek;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.HashMap;
import java.util.Map;
import java.util.Map.Entry;

import com.thabok.entities.CustomDay;
import com.thabok.entities.DayOfWeekABCombo;
import com.thabok.entities.Person;
import com.thabok.entities.Schedule;
import com.thabok.entities.TimingInfo;
import com.thabok.main.Controller;
import com.thabok.untis.Period;
import com.thabok.untis.Teacher;
import com.thabok.util.Util;

/**
 * Static helper class for anything related to the Timetable.
 * @author thabok
 */
public class TimetableHelper {

	/**
	 * Converts a timetable with start & end time information into a {@link Schedule} object
	 * which is based on 1st lesson, 2nd lesson, etc. for easy of use in the planning algorithm.
	 * <br><br>
	 * The conversion considers the lessons start & end times and uses them as thresholds to
	 * convert the continuous time values into discrete lesson numbers.   
	 * @param person the person can override some parts of the schedule based on preferences
	 * @param timetable the timetable object (continuous)
	 * @return the schedule object (discrete)
	 */
	public static Map<Integer, TimingInfo> timetableToSchedule(Person person, Map<Integer, Period> timetable) {
		Map<Integer, TimingInfo> schedule = new HashMap<>();
		for (Entry<Integer, Period> entry : timetable.entrySet()) {
			DayOfWeekABCombo dayOfWeekABCombo = getDayOfWeekABCombo(entry.getKey() /* date */);
			TimingInfo dayInfo = new TimingInfo();
			// apply first & last lesson based on the retrieved timetable
			dayInfo.setStartTime(entry.getValue().startTime);
			dayInfo.setEndTime(entry.getValue().endTime);
			
			// the person may have custom preferences that override the timetable
			applyCustomPreferencesToDayInfo(dayInfo, entry.getKey(), person);
			
			
			schedule.put(dayOfWeekABCombo.getUniqueNumber(), dayInfo);
		}
		return schedule;
	}
	
	/**
	 * Returns true if the period is relevant for the carpool planning. False if not.
	 * 
	 * @param period the period to be checked
	 * @param initials initials of the teacher who's schedule is queried
	 * @return true if the period is relevant for the carpool planning. False if not.
	 */
	public static boolean isPeriodRelevant(Period period, String initials) {
		// class trips, excursions, etc. are marked with the code "irregular"
		if ("irregular".equals(period.code)) {
			return false;
		}
		boolean foundDifferentOrgname = false;
		boolean foundMatchingName = false;
		for (Teacher teacher : period.te) {
			if (teacher.orgname != null) {
				if (teacher.orgname.equals(initials)) {
					// the period is handled by the specified teacher
					foundMatchingName = true;
				} else {
					// the period is only handled temporarily by the specified teacher 
					foundDifferentOrgname = true;
				}
			} else if (teacher.name != null && teacher.name.equals(initials)) {
				// the period is handled by the specified teacher
				foundMatchingName = true;
			}
		}
		boolean isIrrelevant = (foundDifferentOrgname && !foundMatchingName) || period.isOnCallSubstitution();
		return !isIrrelevant;
	}
	
	public static boolean isPersonActiveOnThisDay(Person p, DayOfWeekABCombo dayOfWeekABCombo) {
		CustomDay customDayObject = p.getCustomPrefsForCombo(dayOfWeekABCombo);
		boolean active = getTimingInfoForDay(p, dayOfWeekABCombo) != null;
		
		return active && !customDayObject.ignoreCompletely;
	}
	
	public static TimingInfo getTimingInfoForDay(Person p, DayOfWeekABCombo dayOfWeekABCombo) {
		return p.schedule.get(dayOfWeekABCombo.getUniqueNumber());
	}
	
	
	/*
	 *  Private methods
	 */
	
	private static void applyCustomPreferencesToDayInfo(TimingInfo dayInfo, int date, Person person) {
		int daysBetween = getDaysBetweenDateAndReferenceWeekStartDate(date);
		int customDayIndex = daysBetween > 4 ? daysBetween - 2 : daysBetween;
		CustomDay customDayInfo = person.accessCustomDaysWithCalculatedIndex(customDayIndex);
		if (!customDayInfo.customStart.isBlank()) {
			dayInfo.setStartTime(customDayInfo.getCustomStartTimeInteger());
		}
		if (!customDayInfo.customEnd.isBlank()) {
			dayInfo.setEndTime(customDayInfo.getCustomEndTimeInteger());
		}
	}
	
	private static int getDaysBetweenDateAndReferenceWeekStartDate(int dateNumber) {
		DateTimeFormatter dtf = DateTimeFormatter.ofPattern("yyyyMMdd");
		LocalDate dateObj = LocalDate.parse(String.valueOf(dateNumber), dtf);
		LocalDate startDate = LocalDate.parse(String.valueOf(Controller.referenceWeekStartDate), dtf);
		int daysBetween = (int) java.time.Period.between(startDate, dateObj).getDays();
		return daysBetween;
	}
	/**
	 * Given a date integer of the kind yyyymmdd (e.g., 20210831 for August 31st 2021) 
	 * this method returns the day of the week.
	 * 
	 * @param date the date integer
	 * @return the day of the week enum
	 */
	private static DayOfWeekABCombo getDayOfWeekABCombo(int dateNumber) {
		int number = getDaysBetweenDateAndReferenceWeekStartDate(dateNumber);
		DayOfWeek dow = Util.weekdays.get(number % 7);
		boolean isA = number < 7;
		return new DayOfWeekABCombo(dow, isA);
	}
}
